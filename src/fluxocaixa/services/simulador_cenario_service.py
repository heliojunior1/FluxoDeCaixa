"""Service layer for Simulador de Cenários."""

from datetime import date
from typing import Dict, List, Optional
import json

from ..repositories import simulador_cenario_repository as repo
from ..models import (
    SimuladorCenario,
    CenarioReceita,
    CenarioReceitaAjuste,
    CenarioDespesa,
    CenarioDespesaAjuste,
    ModeloEconomicoParametro,
)


# ==================== CRUD Operations ====================

def list_simuladores() -> List[SimuladorCenario]:
    """Lista todos os cenários simuladores."""
    return repo.get_all_simuladores()


def list_active_simuladores() -> List[SimuladorCenario]:
    """Lista apenas cenários ativos."""
    return repo.get_active_simuladores()


def get_simulador(seq_simulador_cenario: int) -> Optional[SimuladorCenario]:
    """Busca um cenário simulador por ID."""
    return repo.get_simulador_by_id(seq_simulador_cenario)


def delete_simulador(seq_simulador_cenario: int, user_id: int = 1) -> Optional[SimuladorCenario]:
    """Inativa logicamente um cenário simulador."""
    return repo.delete_simulador_logical(seq_simulador_cenario, user_id)


# ==================== Criar Cenário Completo ====================

def criar_simulador_cenario(
    nom_cenario: str,
    dsc_cenario: str,
    ano_base: int,
    meses_projecao: int,
    tipo_cenario_receita: str,  # 'MANUAL', 'HOLT_WINTERS', 'ARIMA', 'SARIMA', 'REGRESSAO'
    config_receita: Dict,  # Configuração específica do modelo de receita
    tipo_cenario_despesa: str,  # 'MANUAL', 'LOA', 'MEDIA_HISTORICA'
    config_despesa: Dict,  # Configuração específica do modelo de despesa
    ajustes_receita: Optional[Dict] = None,  # Ajustes mensais para cenário manual de receita
    ajustes_despesa: Optional[Dict] = None,  # Ajustes mensais para cenário manual de despesa
    user_id: int = 1,  # ID do usuário criando o cenário
) -> SimuladorCenario:
    """
    Cria um cenário simulador completo com receita e despesa.
    
    Args:
        nom_cenario: Nome do cenário
        dsc_cenario: Descrição
        ano_base: Ano base para projeção
        meses_projecao: Número de meses a projetar
        tipo_cenario_receita: 'MANUAL', 'HOLT_WINTERS', 'ARIMA', 'SARIMA', 'REGRESSAO'
        config_receita: Dicionário com configuração específica do modelo
        ajustes_receita: Ajustes mensais para cenário manual (dict)
        tipo_cenario_despesa: 'MANUAL', 'LOA', 'MEDIA_HISTORICA'
        config_despesa: Dicionário com configuração específica
        ajustes_despesa: Ajustes mensais para cenário manual (dict)
        user_id: ID do usuário criando o cenário
    
    Returns:
        SimuladorCenario criado
    """
    # Criar cenário principal
    simulador = SimuladorCenario(
        nom_cenario=nom_cenario,
        dsc_cenario=dsc_cenario,
        ano_base=ano_base,
        meses_projecao=meses_projecao,
        ind_status='A',
        cod_pessoa_inclusao=user_id,
    )
    repo.create_simulador(simulador)
    
    # Criar configuração de receita
    cenario_receita = CenarioReceita(
        seq_simulador_cenario=simulador.seq_simulador_cenario,
        cod_tipo_cenario=tipo_cenario_receita,
        json_configuracao=json.dumps(config_receita) if config_receita else None,
    )
    repo.create_cenario_receita(cenario_receita)
    
    # Criar ajustes de receita se for manual
    if tipo_cenario_receita == 'MANUAL' and ajustes_receita:
        _criar_ajustes_receita(
            cenario_receita.seq_cenario_receita,
            ajustes_receita,
            ano_base,
        )
    
    # Criar parâmetros econômicos se for regressão
    if tipo_cenario_receita == 'REGRESSAO' and config_receita.get('parametros'):
        _criar_parametros_economicos(
            cenario_receita.seq_cenario_receita,
            config_receita['parametros'],
        )
    
    # Criar configuração de despesa
    cenario_despesa = CenarioDespesa(
        seq_simulador_cenario=simulador.seq_simulador_cenario,
        cod_tipo_cenario=tipo_cenario_despesa,
        json_configuracao=json.dumps(config_despesa) if config_despesa else None,
    )
    repo.create_cenario_despesa(cenario_despesa)
    
    # Criar ajustes de despesa se for manual
    if tipo_cenario_despesa == 'MANUAL' and ajustes_despesa:
        _criar_ajustes_despesa(
            cenario_despesa.seq_cenario_despesa,
            ajustes_despesa,
            ano_base,
        )
    
    repo.commit()
    return simulador


def _criar_ajustes_receita(seq_cenario_receita: int, ajustes_data: Dict, ano_base: int):
    """Helper para criar ajustes de receita."""
    for key, value in ajustes_data.items():
        # Ignorar chaves de despesa (que também começam com val_ajuste_)
        if key.startswith('val_ajuste_') and not key.startswith('val_ajuste_desp_') and value:
            try:
                parts = key.split('_')
                # val_ajuste_1_10 -> ['val', 'ajuste', '1', '10']
                mes = int(parts[2])
                seq_qualificador = int(parts[3])
                val_ajuste = float(value)
                cod_tipo_ajuste = ajustes_data.get(f'cod_tipo_ajuste_{mes}_{seq_qualificador}', 'P')
                
                ajuste = CenarioReceitaAjuste(
                    seq_cenario_receita=seq_cenario_receita,
                    seq_qualificador=seq_qualificador,
                    ano=ano_base,
                    mes=mes,
                    cod_tipo_ajuste=cod_tipo_ajuste,
                    val_ajuste=val_ajuste,
                )
                repo.create_ajuste_receita(ajuste)
            except (ValueError, IndexError):
                continue


def _criar_ajustes_despesa(seq_cenario_despesa: int, ajustes_data: Dict, ano_base: int):
    """Helper para criar ajustes de despesa."""
    for key, value in ajustes_data.items():
        if key.startswith('val_ajuste_desp_') and value:
            try:
                parts = key.split('_')
                # val_ajuste_desp_1_10 -> ['val', 'ajuste', 'desp', '1', '10']
                mes = int(parts[3])
                seq_qualificador = int(parts[4])
                val_ajuste = float(value)
                cod_tipo_ajuste = ajustes_data.get(f'cod_tipo_ajuste_desp_{mes}_{seq_qualificador}', 'P')
                
                ajuste = CenarioDespesaAjuste(
                    seq_cenario_despesa=seq_cenario_despesa,
                    seq_qualificador=seq_qualificador,
                    ano=ano_base,
                    mes=mes,
                    cod_tipo_ajuste=cod_tipo_ajuste,
                    val_ajuste=val_ajuste,
                )
                repo.create_ajuste_despesa(ajuste)
            except (ValueError, IndexError):
                continue


def _criar_parametros_economicos(seq_cenario_receita: int, parametros: List[Dict]):
    """Helper para criar parâmetros de modelos econômicos."""
    for param in parametros:
        modelo_param = ModeloEconomicoParametro(
            seq_cenario_receita=seq_cenario_receita,
            nom_variavel=param['nome'],
            val_coeficiente=param['coeficiente'],
            json_valores_historicos=json.dumps(param.get('valores_historicos', [])),
        )
        repo.create_parametro_economico(modelo_param)


# ==================== Atualizar Cenário ====================

def atualizar_simulador_cenario(
    seq_simulador_cenario: int,
    nom_cenario: str,
    dsc_cenario: str,
    ano_base: int,
    meses_projecao: int,
    tipo_cenario_receita: str,  # 'MANUAL', 'HOLT_WINTERS', 'ARIMA', 'SARIMA', 'REGRESSAO'
    config_receita: Dict,  # Configuração específica do modelo de receita
    tipo_cenario_despesa: str,  # 'MANUAL', 'LOA', 'MEDIA_HISTORICA'
    config_despesa: Dict,  # Configuração específica do modelo de despesa
    ajustes_receita: Optional[Dict] = None,  # Ajustes mensais para cenário manual de receita
    ajustes_despesa: Optional[Dict] = None,  # Ajustes mensais para cenário manual de despesa
    user_id: int = 1,  # ID do usuário criando o cenário
) -> Optional[SimuladorCenario]:
    """Atualiza um cenário simulador existente."""
    simulador = repo.get_simulador_by_id(seq_simulador_cenario)
    if not simulador:
        return None
    
    # Atualizar dados principais
    simulador.nom_cenario = nom_cenario
    simulador.dsc_cenario = dsc_cenario
    simulador.ano_base = ano_base
    simulador.meses_projecao = meses_projecao
    simulador.dat_alteracao = date.today()
    simulador.cod_pessoa_alteracao = user_id
    
    # Atualizar receita
    cenario_receita = repo.get_cenario_receita_by_simulador(seq_simulador_cenario)
    if cenario_receita:
        cenario_receita.cod_tipo_cenario = tipo_cenario_receita
        cenario_receita.json_configuracao = json.dumps(config_receita) if config_receita else None
        
        # Remover ajustes antigos e criar novos
        repo.delete_ajustes_receita_by_cenario_ano(cenario_receita.seq_cenario_receita, ano_base)
        if tipo_cenario_receita == 'MANUAL' and ajustes_receita:
            _criar_ajustes_receita(cenario_receita.seq_cenario_receita, ajustes_receita, ano_base)
        
        # Atualizar parâmetros econômicos
        if tipo_cenario_receita == 'REGRESSAO' and config_receita.get('parametros'):
            repo.delete_parametros_by_cenario_receita(cenario_receita.seq_cenario_receita)
            _criar_parametros_economicos(cenario_receita.seq_cenario_receita, config_receita['parametros'])
    
    # Atualizar despesa
    cenario_despesa = repo.get_cenario_despesa_by_simulador(seq_simulador_cenario)
    if cenario_despesa:
        cenario_despesa.cod_tipo_cenario = tipo_cenario_despesa
        cenario_despesa.json_configuracao = json.dumps(config_despesa) if config_despesa else None
        
        # Remover ajustes antigos e criar novos
        repo.delete_ajustes_despesa_by_cenario_ano(cenario_despesa.seq_cenario_despesa, ano_base)
        if tipo_cenario_despesa == 'MANUAL' and ajustes_despesa:
            _criar_ajustes_despesa(cenario_despesa.seq_cenario_despesa, ajustes_despesa, ano_base)
    
    repo.commit()
    return simulador


# ==================== Obter Dados Completos ====================

def obter_simulador_completo(seq_simulador_cenario: int) -> Optional[Dict]:
    """
    Retorna um cenário simulador com todos os dados relacionados.
    
    Returns:
        Dict com estrutura:
        {
            'simulador': SimuladorCenario,
            'receita': {
                'config': CenarioReceita,
                'ajustes': List[CenarioReceitaAjuste],
                'parametros': List[ModeloEconomicoParametro]
            },
            'despesa': {
                'config': CenarioDespesa,
                'ajustes': List[CenarioDespesaAjuste]
            }
        }
    """
    simulador = repo.get_simulador_by_id(seq_simulador_cenario)
    if not simulador:
        return None
    
    resultado = {
        'simulador': simulador,
        'receita': {},
        'despesa': {},
    }
    
    # Carregar dados de receita
    cenario_receita = repo.get_cenario_receita_by_simulador(seq_simulador_cenario)
    if cenario_receita:
        resultado['receita']['config'] = cenario_receita
        resultado['receita']['ajustes'] = repo.get_ajustes_receita_by_cenario(cenario_receita.seq_cenario_receita)
        resultado['receita']['parametros'] = repo.get_parametros_by_cenario_receita(cenario_receita.seq_cenario_receita)
    
    # Carregar dados de despesa
    cenario_despesa = repo.get_cenario_despesa_by_simulador(seq_simulador_cenario)
    if cenario_despesa:
        resultado['despesa']['config'] = cenario_despesa
        resultado['despesa']['ajustes'] = repo.get_ajustes_despesa_by_cenario(cenario_despesa.seq_cenario_despesa)
    
    return resultado


# ==================== Executar Simulação ====================

def executar_simulacao(seq_simulador_cenario: int) -> Optional[Dict]:
    """
    Executa a simulação completa de um cenário, gerando projeções de receita e despesa.
    
    Args:
        seq_simulador_cenario: ID do cenário simulador
    
    Returns:
        Dict com estrutura:
        {
            'simulador': SimuladorCenario,
            'projecao_receita': pd.DataFrame com colunas (data, valor_projetado),
            'projecao_despesa': pd.DataFrame com colunas (data, valor_projetado),
            'cenario_total': pd.DataFrame com colunas (data, receita, despesa, saldo),
            'resumo': {
                'total_receita': float,
                'total_despesa': float,
                'saldo_final': float,
            }
        }
    """
    from . import modelos_economicos_service as modelos
    from datetime import date
    from dateutil.relativedelta import relativedelta
    import pandas as pd
    
    # Carregar cenário completo
    cenario_completo = obter_simulador_completo(seq_simulador_cenario)
    if not cenario_completo:
        return None
    
    simulador = cenario_completo['simulador']
    ano_base = simulador.ano_base
    meses_projecao = simulador.meses_projecao
    
    # ==================== Projeção de Receita ====================
    
    config_receita = cenario_completo['receita'].get('config')
    tipo_receita = config_receita.cod_tipo_cenario if config_receita else 'MANUAL'
    
    if tipo_receita == 'MANUAL':
        # Usar ajustes manuais
        projecao_receita = _executar_cenario_manual_receita(
            cenario_completo['receita'].get('ajustes', []),
            ano_base,
            meses_projecao
        )
    elif tipo_receita == 'HOLT_WINTERS':
        config = json.loads(config_receita.json_configuracao or '{}')
        seq_qualificador = config.get('seq_qualificador')
        
        # Obter dados históricos
        data_fim = date(ano_base, 12, 31)
        data_inicio = data_fim - relativedelta(years=2)  # 2 anos de histórico
        dados_hist = modelos.obter_dados_historicos(seq_qualificador, data_inicio, data_fim)
        
        projecao_receita = modelos.projetar_holt_winters(dados_hist, meses_projecao, config)
        
    elif tipo_receita == 'ARIMA':
        config = json.loads(config_receita.json_configuracao or '{}')
        seq_qualificador = config.get('seq_qualificador')
        
        data_fim = date(ano_base, 12, 31)
        data_inicio = data_fim - relativedelta(years=2)
        dados_hist = modelos.obter_dados_historicos(seq_qualificador, data_inicio, data_fim)
        
        projecao_receita = modelos.projetar_arima(dados_hist, meses_projecao, config)
        
    elif tipo_receita == 'SARIMA':
        config = json.loads(config_receita.json_configuracao or '{}')
        seq_qualificador = config.get('seq_qualificador')
        
        data_fim = date(ano_base, 12, 31)
        data_inicio = data_fim - relativedelta(years=3)  # 3 anos para SARIMA
        dados_hist = modelos.obter_dados_historicos(seq_qualificador, data_inicio, data_fim)
        
        projecao_receita = modelos.projetar_sarima(dados_hist, meses_projecao, config)
        
    elif tipo_receita == 'REGRESSAO':
        config = json.loads(config_receita.json_configuracao or '{}')
        projecao_receita = modelos.projetar_regressao_multipla(meses_projecao, config)
    else:
        # Fallback: cenário vazio
        projecao_receita = pd.DataFrame({
            'data': [],
            'valor_projetado': []
        })
    
    # ==================== Projeção de Despesa ====================
    
    config_despesa = cenario_completo['despesa'].get('config')
    tipo_despesa = config_despesa.cod_tipo_cenario if config_despesa else 'MANUAL'
    
    if tipo_despesa == 'MANUAL':
        # Usar ajustes manuais
        projecao_despesa = _executar_cenario_manual_despesa(
            cenario_completo['despesa'].get('ajustes', []),
            ano_base,
            meses_projecao
        )
    elif tipo_despesa == 'LOA':
        config = json.loads(config_despesa.json_configuracao or '{}')
        projecao_despesa = modelos.projetar_loa(meses_projecao, config)
        
    elif tipo_despesa == 'MEDIA_HISTORICA':
        config = json.loads(config_despesa.json_configuracao or '{}')
        seq_qualificador = config.get('seq_qualificador')
        
        data_fim = date(ano_base, 12, 31)
        data_inicio = data_fim - relativedelta(years=2)
        dados_hist = modelos.obter_dados_historicos(seq_qualificador, data_inicio, data_fim)
        
        projecao_despesa = modelos.projetar_media_historica(dados_hist, meses_projecao, config)
    else:
        # Fallback
        projecao_despesa = pd.DataFrame({
            'data': [],
            'valor_projetado': []
        })
    
    # ==================== Cenário Total ====================
    
    cenario_total = _calcular_cenario_total(projecao_receita, projecao_despesa)
    
    # ==================== Resumo ====================
    
    resumo = {
        'total_receita': projecao_receita['valor_projetado'].sum() if len(projecao_receita) > 0 else 0,
        'total_despesa': projecao_despesa['valor_projetado'].sum() if len(projecao_despesa) > 0 else 0,
        'saldo_final': 0,
    }
    resumo['saldo_final'] = resumo['total_receita'] - abs(resumo['total_despesa'])
    
    return {
        'simulador': simulador,
        'projecao_receita': projecao_receita,  # Agregado por data
        'projecao_despesa': projecao_despesa,  # Agregado por data
        'projecao_receita_detalhada': projecao_receita_detalhada if 'projecao_receita_detalhada' in locals() else None,
        'projecao_despesa_detalhada': projecao_despesa_detalhada if 'projecao_despesa_detalhada' in locals() else None,
        'cenario_total': cenario_total,
        'resumo': resumo,
    }


def _executar_cenario_manual_receita(ajustes: List, ano_base: int, meses_projecao: int) -> 'pd.DataFrame':
    """Helper para executar cenário manual de receita baseado em ajustes."""
    import pandas as pd
    from dateutil.relativedelta import relativedelta
    
    # Criar lista de todos os meses e qualificadores
    data_base = date(ano_base, 1, 1)
    records = []
    
    # Agrupar ajustes por (mes, qualificador)
    ajustes_map = {}
    for ajuste in ajustes:
        ajustes_map[(ajuste.mes, ajuste.seq_qualificador)] = float(ajuste.val_ajuste)
        
    # Identificar todos os qualificadores envolvidos
    qualificadores = set(a.seq_qualificador for a in ajustes)
    
    for i in range(meses_projecao):
        data_mes = data_base + relativedelta(months=i)
        mes = data_mes.month
        
        for seq_qualificador in qualificadores:
            valor = ajustes_map.get((mes, seq_qualificador), 0)
            records.append({
                'data': data_mes,
                'seq_qualificador': seq_qualificador,
                'valor_projetado': valor
            })
            
    if not records:
        return pd.DataFrame(columns=['data', 'seq_qualificador', 'valor_projetado'])
        
    return pd.DataFrame(records)


def _executar_cenario_manual_despesa(ajustes: List, ano_base: int, meses_projecao: int) -> 'pd.DataFrame':
    """Helper para executar cenário manual de despesa baseado em ajustes."""
    import pandas as pd
    from dateutil.relativedelta import relativedelta
    
    # Criar lista de todos os meses e qualificadores
    data_base = date(ano_base, 1, 1)
    records = []
    
    # Agrupar ajustes por (mes, qualificador)
    ajustes_map = {}
    for ajuste in ajustes:
        ajustes_map[(ajuste.mes, ajuste.seq_qualificador)] = float(ajuste.val_ajuste)
        
    # Identificar todos os qualificadores envolvidos
    qualificadores = set(a.seq_qualificador for a in ajustes)
    
    for i in range(meses_projecao):
        data_mes = data_base + relativedelta(months=i)
        mes = data_mes.month
        
        for seq_qualificador in qualificadores:
            valor = ajustes_map.get((mes, seq_qualificador), 0)
            records.append({
                'data': data_mes,
                'seq_qualificador': seq_qualificador,
                'valor_projetado': abs(valor)  # Despesa positiva
            })
            
    if not records:
        return pd.DataFrame(columns=['data', 'seq_qualificador', 'valor_projetado'])
        
    return pd.DataFrame(records)


def _calcular_cenario_total(projecao_receita: 'pd.DataFrame', projecao_despesa: 'pd.DataFrame') -> 'pd.DataFrame':
    """Combina projeções de receita e despesa em um cenário total."""
    import pandas as pd
    
    # Agregar por data se houver detalhamento por qualificador
    if 'seq_qualificador' in projecao_receita.columns:
        df_receita = projecao_receita.groupby('data')['valor_projetado'].sum().reset_index()
    else:
        df_receita = projecao_receita.copy() if len(projecao_receita) > 0 else pd.DataFrame({'data': [], 'valor_projetado': []})
        
    if 'seq_qualificador' in projecao_despesa.columns:
        df_despesa = projecao_despesa.groupby('data')['valor_projetado'].sum().reset_index()
    else:
        df_despesa = projecao_despesa.copy() if len(projecao_despesa) > 0 else pd.DataFrame({'data': [], 'valor_projetado': []})
    
    # Renomear colunas
    df_receita = df_receita.rename(columns={'valor_projetado': 'receita'})
    df_despesa = df_despesa.rename(columns={'valor_projetado': 'despesa'})
    
    # Merge
    if len(df_receita) == 0 and len(df_despesa) == 0:
        return pd.DataFrame(columns=['data', 'receita', 'despesa', 'saldo'])
        
    cenario_total = pd.merge(df_receita, df_despesa, on='data', how='outer').fillna(0)
    
    # Calcular saldo
    cenario_total['saldo'] = cenario_total['receita'] - cenario_total['despesa']
    
    return cenario_total.sort_values('data')
