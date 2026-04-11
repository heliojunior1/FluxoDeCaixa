"""Motor de avaliação de fórmulas parametrizáveis.

Este módulo é o coração do sistema de fórmulas. Ele é responsável por:
- Extrair variáveis de expressões matemáticas
- Validar expressões sintaticamente
- Avaliar expressões com variáveis substituídas
- Calcular a 'base' histórica de uma rubrica por diferentes métodos
- Projetar valores usando fórmulas parametrizadas

Usa a biblioteca py_expression_eval para avaliação segura (sem eval()).
"""

import json
from datetime import date
from typing import Dict, List, Optional, Tuple

import pandas as pd
from py_expression_eval import Parser
from sqlalchemy import Integer as db_Integer

from ..repositories import formula_repository as formula_repo


# Parser compartilhado (thread-safe para leitura)
_parser = Parser()


def extrair_variaveis(expressao: str) -> List[str]:
    """Extrai os nomes das variáveis de uma expressão matemática.

    Args:
        expressao: Expressão como 'base * (1 + ipca) * (1 + pib * elasticidade)'

    Returns:
        Lista de nomes de variáveis, ex: ['base', 'ipca', 'pib', 'elasticidade']
    """
    try:
        expr = _parser.parse(expressao)
        return sorted(expr.variables())
    except Exception:
        return []


def validar_formula(expressao: str) -> Tuple[bool, Optional[str]]:
    """Valida se uma expressão é sintaticamente correta.

    Args:
        expressao: Expressão a validar

    Returns:
        Tupla (valida, mensagem_erro). Se válida, mensagem_erro é None.
    """
    if not expressao or not expressao.strip():
        return False, 'Expressão vazia'

    try:
        expr = _parser.parse(expressao)
        # Tentar avaliar com variáveis zeradas para verificar se funciona
        variaveis = {v: 1.0 for v in expr.variables()}
        expr.evaluate(variaveis)
        return True, None
    except Exception as e:
        return False, f'Erro na expressão: {str(e)}'


def avaliar_formula(expressao: str, variaveis: Dict[str, float]) -> float:
    """Avalia uma expressão matemática com os valores das variáveis informados.

    Args:
        expressao: Expressão como 'base * (1 + ipca)'
        variaveis: Dicionário {nome_variavel: valor}, ex: {'base': 1000, 'ipca': 0.045}

    Returns:
        Resultado numérico da avaliação

    Raises:
        ValueError: Se a expressão for inválida ou faltar variáveis
    """
    try:
        expr = _parser.parse(expressao)
        vars_necessarias = set(expr.variables())
        vars_disponiveis = set(variaveis.keys())
        faltantes = vars_necessarias - vars_disponiveis

        if faltantes:
            raise ValueError(
                f'Variáveis não informadas: {", ".join(sorted(faltantes))}'
            )

        resultado = expr.evaluate(variaveis)
        return float(resultado)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f'Erro ao avaliar expressão: {str(e)}')


def listar_anos_disponiveis(seq_qualificador: int) -> List[int]:
    """Retorna lista de anos que possuem dados históricos para um qualificador.

    Consulta a tabela de lançamentos para encontrar todos os anos distintos
    com dados para o qualificador informado.

    Args:
        seq_qualificador: ID do qualificador

    Returns:
        Lista de anos ordenados em ordem decrescente, ex: [2024, 2023, 2022]
    """
    from ..models import Lancamento, db
    from sqlalchemy import func, extract

    try:
        anos = (
            db.session.query(
                extract('year', Lancamento.dat_lancamento).label('ano')
            )
            .filter(Lancamento.seq_qualificador == seq_qualificador)
            .distinct()
            .order_by(extract('year', Lancamento.dat_lancamento).desc())
            .all()
        )
        return [int(a.ano) for a in anos]
    except Exception:
        return []


def listar_todos_anos_disponiveis() -> List[int]:
    """Retorna lista de todos os anos distintos com dados históricos (qualquer qualificador).

    Usado para popular a seção de configuração de base no cenário, onde o usuário
    seleciona quais anos usar para o cálculo da base.

    Returns:
        Lista de anos ordenados em ordem decrescente, ex: [2025, 2024, 2023, 2022]
    """
    from ..models import Lancamento
    from ..models.base import SessionLocal
    from sqlalchemy import func

    try:
        session = SessionLocal()
        year_col = func.strftime('%Y', Lancamento.dat_lancamento)
        anos = (
            session.query(year_col.label('ano'))
            .distinct()
            .order_by(year_col.desc())
            .all()
        )
        result = [int(a.ano) for a in anos if a.ano]
        return result
    except Exception as e:
        print(f"[formula_engine] Erro ao listar anos: {e}")
        import traceback
        traceback.print_exc()
        return []


def calcular_base(
    seq_qualificador: int,
    mes: int,
    metodo: str,
    config: dict,
) -> float:
    """Calcula o valor da 'base' para um mês específico usando dados históricos.

    Args:
        seq_qualificador: ID do qualificador
        mes: Mês para o qual calcular a base (1-12)
        metodo: 'MEDIA_SIMPLES', 'MEDIA_PONDERADA', ou 'VALOR_FIXO'
        config: Configuração do método, ex:
            MEDIA_SIMPLES:   {"anos": [2023, 2024]}
            MEDIA_PONDERADA: {"anos": [2022,2023,2024], "pesos": {"2022":1,"2023":2,"2024":3}}
            VALOR_FIXO:      {"valor": 150000.00}

    Returns:
        Valor calculado da base
    """
    if metodo == 'VALOR_FIXO':
        return float(config.get('valor', 0))

    anos = config.get('anos', [])
    if not anos:
        return 0.0

    # Buscar valores históricos para o mês nos anos selecionados
    valores_por_ano = _buscar_valores_historicos_mes(seq_qualificador, mes, anos)

    if not valores_por_ano:
        return 0.0

    if metodo == 'MEDIA_SIMPLES':
        return sum(valores_por_ano.values()) / len(valores_por_ano)

    elif metodo == 'MEDIA_PONDERADA':
        pesos = config.get('pesos', {})
        soma_ponderada = 0.0
        soma_pesos = 0.0

        for ano, valor in valores_por_ano.items():
            peso = float(pesos.get(str(ano), 1))
            soma_ponderada += valor * peso
            soma_pesos += peso

        if soma_pesos == 0:
            return 0.0
        return soma_ponderada / soma_pesos

    return 0.0


def _buscar_valores_historicos_mes(
    seq_qualificador: int,
    mes: int,
    anos: List[int],
) -> Dict[int, float]:
    """Busca valores históricos de um qualificador para um mês em vários anos.

    Args:
        seq_qualificador: ID do qualificador
        mes: Mês (1-12)
        anos: Lista de anos para buscar

    Returns:
        Dicionário {ano: valor_total_do_mes}
    """
    from ..models import Lancamento, db
    from sqlalchemy import func, extract, and_

    try:
        resultados = (
            db.session.query(
                extract('year', Lancamento.dat_lancamento).label('ano'),
                func.sum(Lancamento.val_lancamento).label('total'),
            )
            .filter(
                and_(
                    Lancamento.seq_qualificador == seq_qualificador,
                    extract('month', Lancamento.dat_lancamento) == mes,
                    extract('year', Lancamento.dat_lancamento).in_(anos),
                )
            )
            .group_by(extract('year', Lancamento.dat_lancamento))
            .all()
        )

        return {int(r.ano): float(r.total) for r in resultados}
    except Exception:
        return {}


def projetar_com_formula(
    seq_qualificador: int,
    ano_base: int,
    meses: int,
    expressao: str,
    metodo_base: str,
    config_base: dict,
    parametros: Dict[str, float],
) -> pd.DataFrame:
    """Projeta valores usando uma fórmula parametrizada (modo mensal)."""
    from dateutil.relativedelta import relativedelta

    records = []
    data_inicio = date(ano_base, 1, 1)

    for i in range(meses):
        data_mes = data_inicio + relativedelta(months=i)
        mes = data_mes.month
        base = calcular_base(seq_qualificador, mes, metodo_base, config_base)
        variaveis = dict(parametros)
        variaveis['base'] = base
        try:
            valor_projetado = avaliar_formula(expressao, variaveis)
        except ValueError:
            valor_projetado = base

        records.append({
            'data': data_mes,
            'seq_qualificador': seq_qualificador,
            'valor_projetado': valor_projetado,
        })

    if not records:
        return pd.DataFrame(columns=['data', 'seq_qualificador', 'valor_projetado'])
    return pd.DataFrame(records)


def calcular_base_anual(
    seq_qualificador: int,
    metodo: str,
    config: dict,
) -> float:
    """Calcula o valor base anual (soma dos 12 meses) dos anos selecionados.

    Args:
        seq_qualificador: ID do qualificador
        metodo: 'MEDIA_SIMPLES', 'MEDIA_PONDERADA', ou 'VALOR_FIXO'
        config: Configuração do método

    Returns:
        Valor calculado da base anual
    """
    if metodo == 'VALOR_FIXO':
        return float(config.get('valor', 0))

    anos = config.get('anos', [])
    if not anos:
        return 0.0

    valores_por_ano = _buscar_valores_historicos_anual(seq_qualificador, anos)
    if not valores_por_ano:
        return 0.0

    if metodo == 'MEDIA_SIMPLES':
        return sum(valores_por_ano.values()) / len(valores_por_ano)

    elif metodo == 'MEDIA_PONDERADA':
        pesos = config.get('pesos', {})
        soma_ponderada = 0.0
        soma_pesos = 0.0
        for ano, valor in valores_por_ano.items():
            peso = float(pesos.get(str(ano), 1))
            soma_ponderada += valor * peso
            soma_pesos += peso
        if soma_pesos == 0:
            return 0.0
        return soma_ponderada / soma_pesos

    return 0.0


def _buscar_valores_historicos_anual(
    seq_qualificador: int,
    anos: List[int],
) -> Dict[int, float]:
    """Busca totais anuais (soma de todos os meses) para um qualificador."""
    from ..models import Lancamento, db
    from sqlalchemy import func, extract, and_

    try:
        resultados = (
            db.session.query(
                extract('year', Lancamento.dat_lancamento).label('ano'),
                func.sum(Lancamento.val_lancamento).label('total'),
            )
            .filter(
                and_(
                    Lancamento.seq_qualificador == seq_qualificador,
                    extract('year', Lancamento.dat_lancamento).in_(anos),
                )
            )
            .group_by(extract('year', Lancamento.dat_lancamento))
            .all()
        )
        return {int(r.ano): float(r.total) for r in resultados}
    except Exception:
        return {}


def projetar_com_formula_anual(
    seq_qualificador: int,
    ano_base: int,
    periodos: int,
    expressao: str,
    metodo_base: str,
    config_base: dict,
    parametros: Dict[str, float],
) -> pd.DataFrame:
    """Projeta valores usando uma fórmula parametrizada (modo anual)."""
    records = []
    base = calcular_base_anual(seq_qualificador, metodo_base, config_base)

    for i in range(periodos):
        ano_projetado = ano_base + i
        data_ref = date(ano_projetado, 1, 1)
        variaveis = dict(parametros)
        variaveis['base'] = base
        try:
            valor_projetado = avaliar_formula(expressao, variaveis)
        except ValueError:
            valor_projetado = base
        records.append({
            'data': data_ref,
            'seq_qualificador': seq_qualificador,
            'valor_projetado': valor_projetado,
        })

    if not records:
        return pd.DataFrame(columns=['data', 'seq_qualificador', 'valor_projetado'])
    return pd.DataFrame(records)


def projetar_cenario_formula(
    seq_simulador_cenario: int,
    ano_base: int,
    periodos: int,
    tipo_fluxo: str,
    periodicidade: str = 'ANUAL',
    metodo_base: str = 'MEDIA_SIMPLES',
    config_base: Optional[dict] = None,
) -> pd.DataFrame:
    """Projeta receitas ou despesas usando fórmulas para todas as rubricas configuradas.

    A configuração de base (método, anos, pesos) vem do cenário, não da fórmula individual.

    Args:
        seq_simulador_cenario: ID do cenário simulador
        ano_base: Ano base para projeção
        periodos: Número de períodos a projetar (anos para ANUAL)
        tipo_fluxo: 'receita' ou 'despesa'
        periodicidade: 'ANUAL', 'MENSAL', etc.
        metodo_base: Método de cálculo da base (do cenário)
        config_base: Configuração da base (do cenário)

    Returns:
        DataFrame com colunas ['data', 'seq_qualificador', 'valor_projetado']
    """
    from ..models import Qualificador
    from ..repositories import formula_repository as f_repo

    if config_base is None:
        config_base = {}

    # Buscar valores dos parâmetros definidos para este cenário
    valores_cenario = f_repo.get_valores_cenario(seq_simulador_cenario)
    parametros = {v.nom_parametro: float(v.val_parametro) for v in valores_cenario}

    # Buscar qualificadores-folha do tipo informado
    qualificadores = Qualificador.query.filter_by(ind_status='A').all()
    folhas = [
        q for q in qualificadores
        if q.tipo_fluxo == tipo_fluxo and q.is_folha()
    ]

    all_records = []
    for folha in folhas:
        formula = f_repo.get_formula_by_qualificador(folha.seq_qualificador)
        if not formula:
            continue

        if periodicidade == 'ANUAL':
            df = projetar_com_formula_anual(
                seq_qualificador=folha.seq_qualificador,
                ano_base=ano_base,
                periodos=periodos,
                expressao=formula.dsc_formula_expressao,
                metodo_base=metodo_base,
                config_base=config_base,
                parametros=parametros,
            )
        else:
            df = projetar_com_formula(
                seq_qualificador=folha.seq_qualificador,
                ano_base=ano_base,
                meses=periodos,
                expressao=formula.dsc_formula_expressao,
                metodo_base=metodo_base,
                config_base=config_base,
                parametros=parametros,
            )

        if len(df) > 0:
            all_records.append(df)

    if not all_records:
        return pd.DataFrame(columns=['data', 'seq_qualificador', 'valor_projetado'])

    return pd.concat(all_records, ignore_index=True)


# ==================== Projeções por Crescimento ====================


def _soma_acumulada(seq_qualificadores: List[int], ano: int, mes_ini: int, mes_fim: int) -> float:
    """Soma dos lançamentos no período [mes_ini, mes_fim] do ano.

    Args:
        seq_qualificadores: Lista de IDs dos qualificadores a somar
        ano: Ano dos lançamentos
        mes_ini: Mês inicial (1-12)
        mes_fim: Mês final (1-12)

    Returns:
        Soma absoluta dos lançamentos no período
    """
    from ..models import Lancamento
    from ..models.base import SessionLocal
    from sqlalchemy import func

    session = SessionLocal()
    try:
        total = (
            session.query(func.sum(func.abs(Lancamento.val_lancamento)))
            .filter(
                Lancamento.seq_qualificador.in_(seq_qualificadores),
                func.strftime('%Y', Lancamento.dat_lancamento) == str(ano),
                func.cast(func.strftime('%m', Lancamento.dat_lancamento), db_Integer).between(mes_ini, mes_fim),
                Lancamento.ind_status == 'A',
            )
            .scalar()
        )
        return float(total) if total else 0.0
    except Exception as e:
        print(f"[formula_engine] Erro ao calcular soma acumulada: {e}")
        return 0.0


def _perfil_sazonal(seq_qualificadores: List[int], ano: int) -> Dict[int, float]:
    """Retorna o perfil sazonal de um ano: {mes: proporção}.

    Ex: {1: 0.08, 2: 0.07, ..., 12: 0.11} onde a soma = 1.0.
    Se o total do ano for 0, retorna distribuição uniforme (1/12).

    Args:
        seq_qualificadores: Lista de IDs dos qualificadores
        ano: Ano para calcular o perfil

    Returns:
        Dicionário {mês: proporção}
    """
    from ..models import Lancamento
    from ..models.base import SessionLocal
    from sqlalchemy import func

    session = SessionLocal()
    try:
        mes_col = func.cast(func.strftime('%m', Lancamento.dat_lancamento), db_Integer)
        resultados = (
            session.query(
                mes_col.label('mes'),
                func.sum(func.abs(Lancamento.val_lancamento)).label('total')
            )
            .filter(
                Lancamento.seq_qualificador.in_(seq_qualificadores),
                func.strftime('%Y', Lancamento.dat_lancamento) == str(ano),
                Lancamento.ind_status == 'A',
            )
            .group_by(mes_col)
            .all()
        )

        valores = {int(r.mes): float(r.total) for r in resultados}
        total_ano = sum(valores.values())

        if total_ano > 0:
            return {m: valores.get(m, 0) / total_ano for m in range(1, 13)}
        else:
            return {m: 1.0 / 12 for m in range(1, 13)}
    except Exception as e:
        print(f"[formula_engine] Erro ao calcular perfil sazonal: {e}")
        return {m: 1.0 / 12 for m in range(1, 13)}


def _perfil_sazonal_medio(seq_qualificadores: List[int], anos: List[int]) -> Dict[int, float]:
    """Média dos perfis sazonais de vários anos.

    Args:
        seq_qualificadores: Lista de IDs dos qualificadores
        anos: Lista de anos para calcular a média

    Returns:
        Dicionário {mês: proporção média}
    """
    if not anos:
        return {m: 1.0 / 12 for m in range(1, 13)}

    perfis = [_perfil_sazonal(seq_qualificadores, ano) for ano in anos]

    resultado = {}
    for mes in range(1, 13):
        valores_mes = [p.get(mes, 0) for p in perfis]
        resultado[mes] = sum(valores_mes) / len(valores_mes)

    return resultado


def projetar_crescimento_ultimo_ano(
    seq_qualificadores: List[int],
    ano_projecao: int,
    ano_referencia: int,
    mes_referencia: int,
    meses_projecao: int = 12,
) -> pd.DataFrame:
    """Projeção por Crescimento do Último Ano.

    Calcula a taxa de crescimento do acumulado parcial do ano de projeção
    vs. o mesmo período do ano de referência, e extrapola para o ano completo.

    Fórmula:
        taxa = Acum(ano_projecao, 1..M) / Acum(ano_referencia, 1..M)
        projecao_total = taxa × Total(ano_referencia)

    Os meses já realizados (1..M) usam o valor real.
    Os meses restantes (M+1..12) são distribuídos pelo perfil sazonal do ano de referência.

    Args:
        seq_qualificadores: Lista de IDs dos qualificadores a projetar
        ano_projecao: Ano que está sendo projetado (ex: 2026)
        ano_referencia: Ano de referência para a taxa de crescimento (ex: 2025)
        mes_referencia: Até que mês existem dados reais no ano de projeção
        meses_projecao: Número de meses a projetar (padrão 12)

    Returns:
        DataFrame com colunas: data, valor_projetado
    """
    # 1. Calcular acumulados parciais
    acum_atual = _soma_acumulada(seq_qualificadores, ano_projecao, 1, mes_referencia)
    acum_referencia = _soma_acumulada(seq_qualificadores, ano_referencia, 1, mes_referencia)
    total_referencia = _soma_acumulada(seq_qualificadores, ano_referencia, 1, 12)

    # 2. Calcular taxa de crescimento
    if acum_referencia > 0:
        taxa_crescimento = acum_atual / acum_referencia
    else:
        taxa_crescimento = 1.0

    # 3. Projeção total do ano
    projecao_total = taxa_crescimento * total_referencia

    # 4. Distribuir: meses reais + meses projetados
    perfil = _perfil_sazonal(seq_qualificadores, ano_referencia)

    registros = []
    for mes in range(1, 13):
        if mes <= mes_referencia:
            # Mês com dados reais: usar valor real
            valor = _soma_acumulada(seq_qualificadores, ano_projecao, mes, mes)
        else:
            # Mês projetado: distribuir pelo perfil sazonal
            valor = projecao_total * perfil.get(mes, 1.0 / 12)

        registros.append({
            'data': date(ano_projecao, mes, 1),
            'valor_projetado': round(valor, 2),
        })

    return pd.DataFrame(registros)


def projetar_media_crescimento_anos(
    seq_qualificadores: List[int],
    ano_projecao: int,
    anos_referencia: List[int],
    mes_referencia: int,
    meses_projecao: int = 12,
) -> pd.DataFrame:
    """Projeção por Média de Crescimento de Anos Selecionados.

    Calcula a taxa de projeção (Total/Acumulado parcial) para cada ano
    de referência, faz a média das taxas, e aplica ao acumulado parcial
    do ano de projeção. Suaviza distorções de anos atípicos.

    Fórmula:
        taxa_i = Total(ano_i) / Acum(ano_i, 1..M)
        taxa_media = mean(taxa_i)
        projecao_total = Acum(ano_projecao, 1..M) × taxa_media

    Args:
        seq_qualificadores: Lista de IDs dos qualificadores a projetar
        ano_projecao: Ano que está sendo projetado (ex: 2026)
        anos_referencia: Lista de anos para média (ex: [2023, 2024, 2025])
        mes_referencia: Até que mês existem dados reais no ano de projeção
        meses_projecao: Número de meses a projetar (padrão 12)

    Returns:
        DataFrame com colunas: data, valor_projetado
    """
    if not anos_referencia:
        return pd.DataFrame(columns=['data', 'valor_projetado'])

    # 1. Calcular taxa para cada ano de referência
    taxas = []
    for ano in anos_referencia:
        acum_parcial = _soma_acumulada(seq_qualificadores, ano, 1, mes_referencia)
        total_ano = _soma_acumulada(seq_qualificadores, ano, 1, 12)

        if acum_parcial > 0:
            taxas.append(total_ano / acum_parcial)

    # 2. Média das taxas
    if taxas:
        taxa_media = sum(taxas) / len(taxas)
    else:
        taxa_media = 1.0

    # 3. Aplicar ao acumulado atual
    acum_atual = _soma_acumulada(seq_qualificadores, ano_projecao, 1, mes_referencia)
    projecao_total = acum_atual * taxa_media

    # 4. Distribuir: meses reais + meses projetados (perfil sazonal médio)
    perfil = _perfil_sazonal_medio(seq_qualificadores, anos_referencia)

    registros = []
    for mes in range(1, 13):
        if mes <= mes_referencia:
            valor = _soma_acumulada(seq_qualificadores, ano_projecao, mes, mes)
        else:
            valor = projecao_total * perfil.get(mes, 1.0 / 12)

        registros.append({
            'data': date(ano_projecao, mes, 1),
            'valor_projetado': round(valor, 2),
        })

    return pd.DataFrame(registros)


