"""Serviço de Backtest para comparação de modelos de projeção.

Este módulo executa backtestes walk-forward: treina modelos com dados históricos
selecionados pelo usuário e compara as projeções com os valores reais.
Calcula métricas de acurácia (MAPE, WMAPE, Viés) e gera rankings.
"""

import json
import traceback
from datetime import date
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from ..models import db, Lancamento, Qualificador
from sqlalchemy import func, extract, and_


# Modelos suportados no backtest
MODELOS_DISPONIVEIS = {
    'HOLT_WINTERS': {'nome': 'Holt-Winters', 'min_meses': 12},
    'ARIMA': {'nome': 'ARIMA', 'min_meses': 12},
    'SARIMA': {'nome': 'SARIMA', 'min_meses': 12},
    'XGBOOST': {'nome': 'XGBoost', 'min_meses': 13},
    'LIGHTGBM': {'nome': 'LightGBM', 'min_meses': 13},
    'MEDIA_HISTORICA': {'nome': 'Média Histórica', 'min_meses': 1},
    'CRESCIMENTO_ANO': {'nome': 'Crescimento Último Ano', 'min_meses': 12},
}


def _obter_dados_treino(
    seq_qualificador: int,
    anos_treino: List[int],
) -> pd.DataFrame:
    """Obtém dados históricos de treino para os anos selecionados.

    Args:
        seq_qualificador: ID do qualificador
        anos_treino: Lista de anos para usar como treino

    Returns:
        DataFrame com colunas: data, valor (mensal)
    """
    lancamentos = (
        Lancamento.query
        .filter(
            Lancamento.seq_qualificador == seq_qualificador,
            Lancamento.ind_status == 'A',
            extract('year', Lancamento.dat_lancamento).in_(anos_treino),
        )
        .all()
    )

    if not lancamentos:
        return pd.DataFrame(columns=['data', 'valor'])

    data = []
    for lanc in lancamentos:
        data.append({
            'data': lanc.dat_lancamento,
            'valor': float(lanc.val_lancamento)
        })

    df = pd.DataFrame(data)
    df['ano_mes'] = df['data'].apply(lambda x: x.strftime('%Y-%m'))
    df_agregado = df.groupby('ano_mes')['valor'].sum().reset_index()
    df_agregado.columns = ['data', 'valor']
    df_agregado['data'] = pd.to_datetime(df_agregado['data'] + '-01')
    return df_agregado.sort_values('data').reset_index(drop=True)


def _obter_real(
    seq_qualificador: int,
    ano: int,
) -> Dict[int, float]:
    """Obtém valores reais (mensais) de um qualificador para um ano.

    Returns:
        Dict {mes: valor_total}, ex: {1: 50000, 2: 55000, ...}
    """
    lancamentos = (
        Lancamento.query
        .filter(
            Lancamento.seq_qualificador == seq_qualificador,
            Lancamento.ind_status == 'A',
            extract('year', Lancamento.dat_lancamento) == ano,
        )
        .all()
    )

    resultado = {}
    for lanc in lancamentos:
        mes = lanc.dat_lancamento.month
        resultado[mes] = resultado.get(mes, 0) + float(lanc.val_lancamento)

    return resultado


def _executar_modelo(
    modelo: str,
    dados_treino: pd.DataFrame,
    ano_teste: int,
    seq_qualificador: int,
    anos_treino: List[int],
) -> Optional[Dict[int, float]]:
    """Executa um modelo de projeção e retorna projeção mensal.

    Returns:
        Dict {mes: valor_projetado} ou None se falhar
    """
    from . import modelos_economicos_service as modelos

    config = {}
    meses_projecao = 12

    try:
        if modelo == 'HOLT_WINTERS':
            if len(dados_treino) < 12:
                return None
            resultado = modelos.projetar_holt_winters(
                dados_treino, meses_projecao, config, ano_teste
            )

        elif modelo == 'ARIMA':
            if len(dados_treino) < 12:
                return None
            resultado = modelos.projetar_arima(
                dados_treino, meses_projecao, config, ano_teste
            )

        elif modelo == 'SARIMA':
            if len(dados_treino) < 12:
                return None
            resultado = modelos.projetar_sarima(
                dados_treino, meses_projecao, config, ano_teste
            )

        elif modelo == 'XGBOOST':
            if len(dados_treino) < 13:
                return None
            resultado = modelos.projetar_xgboost(
                dados_treino, meses_projecao, config, ano_teste
            )

        elif modelo == 'LIGHTGBM':
            if len(dados_treino) < 13:
                return None
            resultado = modelos.projetar_lightgbm(
                dados_treino, meses_projecao, config, ano_teste
            )

        elif modelo == 'MEDIA_HISTORICA':
            if len(dados_treino) == 0:
                return None
            resultado = modelos.projetar_media_historica(
                dados_treino, meses_projecao, config, ano_teste
            )

        elif modelo == 'CRESCIMENTO_ANO':
            # Crescimento usa dados dos anos de treino
            # Precisa de pelo menos 2 anos para calcular crescimento
            if len(anos_treino) < 2:
                return None
            from .formula_engine import projetar_crescimento_ultimo_ano
            ano_ref = max(anos_treino)
            resultado = projetar_crescimento_ultimo_ano(
                seq_qualificadores=[seq_qualificador],
                ano_projecao=ano_teste,
                ano_referencia=ano_ref,
                mes_referencia=12,  # usar ano completo para backtest
                meses_projecao=12,
            )

        else:
            return None

        # Converter DataFrame para dict {mes: valor}
        proj = {}
        for _, row in resultado.iterrows():
            d = row['data'] if isinstance(row['data'], date) else row['data'].date()
            mes = d.month
            col = 'valor_projetado' if 'valor_projetado' in resultado.columns else 'valor'
            proj[mes] = float(row[col])

        return proj

    except Exception as e:
        print(f"  [BACKTEST] Erro {modelo} q={seq_qualificador}: {e}")
        return None


def _calcular_metricas(
    projecao: Dict[int, float],
    real: Dict[int, float],
) -> Dict[str, float]:
    """Calcula métricas de acurácia entre projeção e valores reais.

    Returns:
        Dict com 'mape', 'wmape', 'bias', 'mae'
    """
    meses_comuns = sorted(set(projecao.keys()) & set(real.keys()))

    if not meses_comuns:
        return {'mape': None, 'wmape': None, 'bias': None, 'mae': None}

    proj_vals = np.array([projecao[m] for m in meses_comuns])
    real_vals = np.array([real[m] for m in meses_comuns])

    # Filtrar zeros nos reais (evitar divisão por zero no MAPE)
    mask = real_vals != 0
    if not mask.any():
        return {'mape': None, 'wmape': None, 'bias': None, 'mae': None}

    proj_nz = proj_vals[mask]
    real_nz = real_vals[mask]

    # MAPE: Mean Absolute Percentage Error
    ape = np.abs(proj_nz - real_nz) / np.abs(real_nz) * 100
    mape = float(np.mean(ape))

    # WMAPE: Weighted MAPE (pondera por volume)
    wmape = float(np.sum(np.abs(proj_vals - real_vals)) / np.sum(np.abs(real_vals)) * 100)

    # Viés: positivo = superestima
    bias = float(np.mean(proj_vals - real_vals) / np.mean(np.abs(real_vals)) * 100)

    # MAE: Mean Absolute Error (em R$)
    mae = float(np.mean(np.abs(proj_vals - real_vals)))

    return {
        'mape': round(mape, 2),
        'wmape': round(wmape, 2),
        'bias': round(bias, 2),
        'mae': round(mae, 2),
    }


def _determinar_semaforo(mape: Optional[float]) -> str:
    """Determina o semáforo de acurácia.

    Returns:
        'verde' (≤5%), 'amarelo' (5-15%), 'vermelho' (>15%), 'cinza' (sem dados)
    """
    if mape is None:
        return 'cinza'
    if mape <= 5:
        return 'verde'
    if mape <= 15:
        return 'amarelo'
    return 'vermelho'


def _obter_hierarquia_qualificadores() -> Dict:
    """Retorna a hierarquia de qualificadores: pais com seus filhos.

    Returns:
        {
          seq_pai: {
            'qualificador': Qualificador,
            'filhos': [Qualificador, ...]
          }
        }
    """
    todos = Qualificador.query.filter_by(ind_status='A').all()

    # Mapear por seq
    por_seq = {q.seq_qualificador: q for q in todos}

    # Agrupar filhos por pai
    hierarquia = {}
    for q in todos:
        if q.cod_qualificador_pai is not None:
            pai = por_seq.get(q.cod_qualificador_pai)
            if pai:
                if pai.seq_qualificador not in hierarquia:
                    hierarquia[pai.seq_qualificador] = {
                        'qualificador': pai,
                        'filhos': [],
                    }
                hierarquia[pai.seq_qualificador]['filhos'].append(q)

    return hierarquia


def executar_backtest(
    anos_treino: List[int],
    anos_teste: List[int],
    modelos: List[str],
    qualificadores_ids: Optional[List[int]] = None,
) -> Dict:
    """Executa backtest completo de todos os modelos para todos os qualificadores.

    Args:
        anos_treino: Anos para treinamento (ex: [2022, 2023, 2024])
        anos_teste: Anos para teste/validação (ex: [2025])
        modelos: Lista de modelos a testar (ex: ['HOLT_WINTERS', 'ARIMA'])
        qualificadores_ids: IDs dos qualificadores-filho (None = todos)

    Returns:
        Dict com resultados completos do backtest
    """
    # Validar que treino < teste
    max_treino = max(anos_treino)
    min_teste = min(anos_teste)
    if max_treino >= min_teste:
        raise ValueError(
            f'Ano de treino ({max_treino}) deve ser anterior ao ano de teste ({min_teste})'
        )

    # Obter qualificadores-filho
    hierarquia = _obter_hierarquia_qualificadores()

    filhos_validos = []
    for pai_data in hierarquia.values():
        for filho in pai_data['filhos']:
            if qualificadores_ids is None or filho.seq_qualificador in qualificadores_ids:
                filhos_validos.append(filho)

    if not filhos_validos:
        raise ValueError('Nenhum qualificador-filho selecionado')

    # Validar modelos
    modelos_validos = [m for m in modelos if m in MODELOS_DISPONIVEIS]
    if not modelos_validos:
        raise ValueError('Nenhum modelo válido selecionado')

    print(f"[BACKTEST] Iniciando: {len(filhos_validos)} qualificadores × "
          f"{len(modelos_validos)} modelos × {len(anos_teste)} anos de teste")

    # ==================== BACKTEST POR QUALIFICADOR-FILHO ====================
    resultados_filho = []

    for filho in filhos_validos:
        seq_q = filho.seq_qualificador
        print(f"  [BACKTEST] Qualificador: {filho.dsc_qualificador}")

        # Obter dados de treino
        dados_treino = _obter_dados_treino(seq_q, anos_treino)

        resultado_qualificador = {
            'seq_qualificador': seq_q,
            'num_qualificador': filho.num_qualificador,
            'dsc_qualificador': filho.dsc_qualificador,
            'pai_seq': filho.cod_qualificador_pai,
            'modelos': {},
        }

        for modelo in modelos_validos:
            metricas_por_ano = []

            for ano_teste in anos_teste:
                # Obter valores reais do ano de teste
                real = _obter_real(seq_q, ano_teste)
                if not real:
                    continue

                # Executar modelo
                projecao = _executar_modelo(
                    modelo, dados_treino, ano_teste, seq_q, anos_treino
                )
                if projecao is None:
                    continue

                # Calcular métricas
                metricas = _calcular_metricas(projecao, real)
                metricas['ano_teste'] = ano_teste
                metricas['projecao'] = {str(k): v for k, v in projecao.items()}
                metricas['real'] = {str(k): v for k, v in real.items()}
                metricas_por_ano.append(metricas)

            # Média das métricas entre os anos de teste
            if metricas_por_ano:
                mapes = [m['mape'] for m in metricas_por_ano if m['mape'] is not None]
                wmapes = [m['wmape'] for m in metricas_por_ano if m['wmape'] is not None]
                biases = [m['bias'] for m in metricas_por_ano if m['bias'] is not None]
                maes = [m['mae'] for m in metricas_por_ano if m['mae'] is not None]

                resultado_qualificador['modelos'][modelo] = {
                    'nome': MODELOS_DISPONIVEIS[modelo]['nome'],
                    'mape': round(np.mean(mapes), 2) if mapes else None,
                    'wmape': round(np.mean(wmapes), 2) if wmapes else None,
                    'bias': round(np.mean(biases), 2) if biases else None,
                    'mae': round(np.mean(maes), 2) if maes else None,
                    'detalhes_por_ano': metricas_por_ano,
                }

        # Determinar melhor modelo para este qualificador (menor MAPE)
        melhor = None
        melhor_mape = float('inf')
        for cod_modelo, dados_modelo in resultado_qualificador['modelos'].items():
            if dados_modelo['mape'] is not None and dados_modelo['mape'] < melhor_mape:
                melhor_mape = dados_modelo['mape']
                melhor = cod_modelo

        resultado_qualificador['melhor_modelo'] = melhor
        resultado_qualificador['melhor_mape'] = melhor_mape if melhor else None
        resultado_qualificador['semaforo'] = _determinar_semaforo(
            melhor_mape if melhor else None
        )

        resultados_filho.append(resultado_qualificador)

    # ==================== AGREGAR POR PAI ====================
    resultados_pai = _agregar_pais(resultados_filho, hierarquia, modelos_validos)

    # ==================== RANKING GERAL ====================
    ranking_geral = _rankear_modelos(resultados_filho, modelos_validos)

    return {
        'resultados_filho': resultados_filho,
        'resultados_pai': resultados_pai,
        'ranking_geral': ranking_geral,
        'anos_treino': anos_treino,
        'anos_teste': anos_teste,
        'modelos_testados': [
            {'codigo': m, 'nome': MODELOS_DISPONIVEIS[m]['nome']}
            for m in modelos_validos
        ],
    }


def _agregar_pais(
    resultados_filho: List[Dict],
    hierarquia: Dict,
    modelos_validos: List[str],
) -> List[Dict]:
    """Agrega resultados dos filhos para calcular métricas dos pais."""
    resultados_pai = []

    for pai_seq, pai_data in hierarquia.items():
        pai_q = pai_data['qualificador']

        # Filhos que têm resultados
        filhos_com_resultado = [
            r for r in resultados_filho
            if r['pai_seq'] == pai_seq and r['modelos']
        ]

        if not filhos_com_resultado:
            continue

        resultado_pai = {
            'seq_qualificador': pai_seq,
            'num_qualificador': pai_q.num_qualificador,
            'dsc_qualificador': pai_q.dsc_qualificador,
            'modelos': {},
            'filhos': [r['seq_qualificador'] for r in filhos_com_resultado],
        }

        for modelo in modelos_validos:
            mapes = []
            wmapes = []
            maes = []
            biases = []

            for filho_r in filhos_com_resultado:
                if modelo in filho_r['modelos']:
                    m_data = filho_r['modelos'][modelo]
                    if m_data['mape'] is not None:
                        mapes.append(m_data['mape'])
                    if m_data['wmape'] is not None:
                        wmapes.append(m_data['wmape'])
                    if m_data['mae'] is not None:
                        maes.append(m_data['mae'])
                    if m_data['bias'] is not None:
                        biases.append(m_data['bias'])

            if mapes:
                resultado_pai['modelos'][modelo] = {
                    'nome': MODELOS_DISPONIVEIS[modelo]['nome'],
                    'mape': round(np.mean(mapes), 2),
                    'wmape': round(np.mean(wmapes), 2) if wmapes else None,
                    'bias': round(np.mean(biases), 2) if biases else None,
                    'mae': round(np.mean(maes), 2) if maes else None,
                }

        # Melhor modelo do pai
        melhor = None
        melhor_mape = float('inf')
        for cod_modelo, dados_modelo in resultado_pai['modelos'].items():
            if dados_modelo['mape'] is not None and dados_modelo['mape'] < melhor_mape:
                melhor_mape = dados_modelo['mape']
                melhor = cod_modelo

        resultado_pai['melhor_modelo'] = melhor
        resultado_pai['melhor_mape'] = melhor_mape if melhor else None
        resultado_pai['semaforo'] = _determinar_semaforo(
            melhor_mape if melhor else None
        )

        resultados_pai.append(resultado_pai)

    return resultados_pai


def _rankear_modelos(
    resultados_filho: List[Dict],
    modelos_validos: List[str],
) -> Dict:
    """Gera ranking geral: melhor modelo globalmente."""
    ranking = []

    for modelo in modelos_validos:
        wmapes = []
        vitorias = 0

        for filho_r in resultados_filho:
            if modelo in filho_r['modelos']:
                m_data = filho_r['modelos'][modelo]
                if m_data['wmape'] is not None:
                    wmapes.append(m_data['wmape'])

            # Contar vitórias
            if filho_r.get('melhor_modelo') == modelo:
                vitorias += 1

        ranking.append({
            'modelo': modelo,
            'nome': MODELOS_DISPONIVEIS[modelo]['nome'],
            'wmape_medio': round(np.mean(wmapes), 2) if wmapes else None,
            'qualificadores_vencidos': vitorias,
            'total_testados': len([
                r for r in resultados_filho
                if modelo in r['modelos'] and r['modelos'][modelo]['mape'] is not None
            ]),
        })

    # Ordenar por WMAPE (menor = melhor)
    ranking.sort(key=lambda x: x['wmape_medio'] if x['wmape_medio'] is not None else float('inf'))

    return {
        'melhor_modelo': ranking[0]['modelo'] if ranking and ranking[0]['wmape_medio'] is not None else None,
        'melhor_nome': ranking[0]['nome'] if ranking and ranking[0]['wmape_medio'] is not None else None,
        'wmape_medio': ranking[0]['wmape_medio'] if ranking else None,
        'ranking': ranking,
    }


# ==================== RECOMENDAÇÕES ====================

def salvar_recomendacoes(resultados_backtest: Dict) -> int:
    """Salva o melhor modelo por qualificador na tabela de recomendações.

    Args:
        resultados_backtest: Resultado de executar_backtest()

    Returns:
        Número de recomendações salvas
    """
    from ..models.formula import db as formula_db

    # Limpar recomendações anteriores
    db.session.execute(
        db.text('DELETE FROM flc_backtest_recomendacao')
    )

    count = 0
    anos_json = json.dumps(resultados_backtest.get('anos_teste', []))

    for filho_r in resultados_backtest.get('resultados_filho', []):
        melhor = filho_r.get('melhor_modelo')
        if melhor and melhor in filho_r.get('modelos', {}):
            m_data = filho_r['modelos'][melhor]
            db.session.execute(
                db.text(
                    '''INSERT INTO flc_backtest_recomendacao
                    (seq_qualificador, cod_modelo, val_mape, val_wmape, val_bias,
                     anos_teste, dat_execucao)
                    VALUES (:seq_q, :modelo, :mape, :wmape, :bias, :anos, :data)'''
                ),
                {
                    'seq_q': filho_r['seq_qualificador'],
                    'modelo': melhor,
                    'mape': m_data.get('mape'),
                    'wmape': m_data.get('wmape'),
                    'bias': m_data.get('bias'),
                    'anos': anos_json,
                    'data': date.today().isoformat(),
                },
            )
            count += 1

    db.session.commit()
    return count


def obter_recomendacoes() -> Dict[int, Dict]:
    """Obtém recomendações salvas do último backtest.

    Returns:
        Dict {seq_qualificador: {modelo, nome, mape, wmape, bias}}
    """
    rows = db.session.execute(
        db.text(
            '''SELECT seq_qualificador, cod_modelo, val_mape, val_wmape, val_bias,
                      anos_teste, dat_execucao
               FROM flc_backtest_recomendacao
               ORDER BY seq_qualificador'''
        )
    ).fetchall()

    resultado = {}
    for row in rows:
        cod_modelo = row[1]
        resultado[row[0]] = {
            'modelo': cod_modelo,
            'nome': MODELOS_DISPONIVEIS.get(cod_modelo, {}).get('nome', cod_modelo),
            'mape': float(row[2]) if row[2] else None,
            'wmape': float(row[3]) if row[3] else None,
            'bias': float(row[4]) if row[4] else None,
            'anos_teste': json.loads(row[5]) if row[5] else [],
            'dat_execucao': row[6],
        }

    return resultado
