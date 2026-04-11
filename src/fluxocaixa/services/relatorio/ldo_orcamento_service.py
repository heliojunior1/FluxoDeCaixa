"""LDO & Orçamento service - Monitoramento de Metas Fiscais.

Refatorado para usar dados reais da LOA (flc_loa) e suportar
receitas + despesas + comparativo LOA × Realizado.
"""
from datetime import date

from ...models import Qualificador
from ...repositories.lancamento_repository import LancamentoRepository
from ...repositories.loa_repository import LoaRepository
from .base import get_tipo_lancamento_ids


def get_ldo_orcamento_data(ano: int, tipo_fluxo: str = 'ambos') -> dict:
    """
    Retorna dados para o relatório de LDO & Orçamento.

    Mostra:
    - KPIs totalizadores (Total LOA, Realizado, % Execução, Saldo)
    - Comparativo LOA × Realizado por categoria (gráfico de barras)
    - Distribuição do Orçamento (LOA) por categoria (gráfico pizza)
    - Metas Fiscais (LDO) com status de cumprimento

    Args:
        ano: Ano para análise
        tipo_fluxo: 'receita', 'despesa' ou 'ambos'

    Returns:
        dict com kpis, comparativo, distribuicao_orcamento, metas_fiscais
    """
    # IDs dos tipos
    tipo_ids = get_tipo_lancamento_ids()
    id_entrada = tipo_ids['entrada']
    id_saida = tipo_ids['saida']

    # Inicializar repositories
    lancamento_repo = LancamentoRepository()
    loa_repo = LoaRepository()

    # --- Buscar qualificadores folha ativos ---
    qualificadores_ativos = [
        q for q in Qualificador.query.filter_by(ind_status='A').all()
        if q.is_folha()
    ]

    # Filtrar por tipo_fluxo
    if tipo_fluxo == 'receita':
        qualificadores_filtrados = [q for q in qualificadores_ativos if q.tipo_fluxo == 'receita']
    elif tipo_fluxo == 'despesa':
        qualificadores_filtrados = [q for q in qualificadores_ativos if q.tipo_fluxo == 'despesa']
    else:
        qualificadores_filtrados = qualificadores_ativos

    # --- Buscar dados LOA reais ---
    loa_dict = loa_repo.get_dict_by_year(ano)

    # --- 1. COMPARATIVO LOA × REALIZADO ---
    comparativo = []
    total_loa = 0.0
    total_realizado = 0.0

    for qual in qualificadores_filtrados:
        # Valor LOA cadastrado
        valor_loa = loa_dict.get(qual.seq_qualificador, 0.0)

        # Valor Realizado (soma dos lançamentos)
        cod_tipo = id_entrada if qual.tipo_fluxo == 'receita' else id_saida
        valor_realizado = lancamento_repo.get_sum_by_qualificadores_and_year(
            qualificadores_ids=[qual.seq_qualificador],
            cod_tipo=cod_tipo,
            ano=ano
        )
        valor_realizado = abs(valor_realizado)

        # Percentual de execução
        perc_execucao = (valor_realizado / valor_loa * 100) if valor_loa > 0 else 0.0

        if valor_loa > 0 or valor_realizado > 0:
            comparativo.append({
                'categoria': qual.dsc_qualificador,
                'qualificador_id': qual.seq_qualificador,
                'valor_loa': round(valor_loa, 2),
                'valor_realizado': round(valor_realizado, 2),
                'percentual_execucao': round(perc_execucao, 2),
                'tipo': qual.tipo_fluxo
            })
            total_loa += valor_loa
            total_realizado += valor_realizado

    # Ordenar por valor LOA decrescente
    comparativo.sort(key=lambda x: x['valor_loa'], reverse=True)

    # --- 2. KPIs ---
    perc_execucao_total = (total_realizado / total_loa * 100) if total_loa > 0 else 0.0
    saldo_loa = total_loa - total_realizado

    kpis = {
        'total_loa': round(total_loa, 2),
        'total_realizado': round(total_realizado, 2),
        'percentual_execucao': round(perc_execucao_total, 2),
        'saldo_loa': round(saldo_loa, 2),
    }

    # --- 3. DISTRIBUIÇÃO DO ORÇAMENTO (LOA) - gráfico pizza ---
    distribuicao = []
    total_loa_dist = 0.0

    for qual in qualificadores_filtrados:
        valor_loa = loa_dict.get(qual.seq_qualificador, 0.0)
        if valor_loa > 0:
            distribuicao.append({
                'categoria': qual.dsc_qualificador,
                'valor': valor_loa,
                'tipo': qual.tipo_fluxo
            })
            total_loa_dist += valor_loa

    # Calcular percentuais
    for item in distribuicao:
        item['percentual'] = round((item['valor'] / total_loa_dist * 100) if total_loa_dist > 0 else 0, 2)
        item['valor'] = round(item['valor'], 2)

    # Ordenar por valor decrescente
    distribuicao.sort(key=lambda x: x['valor'], reverse=True)

    # --- 4. METAS FISCAIS (LDO) ---
    metas_fiscais = _calcular_metas_fiscais(
        ano, lancamento_repo, loa_repo, loa_dict,
        qualificadores_ativos, id_entrada, id_saida
    )

    return {
        'kpis': kpis,
        'comparativo': comparativo,
        'distribuicao_orcamento': distribuicao,
        'metas_fiscais': metas_fiscais,
    }


def _calcular_metas_fiscais(
    ano: int,
    lancamento_repo: LancamentoRepository,
    loa_repo: LoaRepository,
    loa_dict: dict[int, float],
    qualificadores_ativos: list,
    id_entrada: int,
    id_saida: int
) -> list[dict]:
    """Calcula metas fiscais usando dados reais de LOA e lançamentos."""

    quals_receita = [q for q in qualificadores_ativos if q.tipo_fluxo == 'receita']
    quals_despesa = [q for q in qualificadores_ativos if q.tipo_fluxo == 'despesa']

    # Receita Corrente Líquida (RCL) = Total receitas realizadas
    rcl = lancamento_repo.get_sum_by_qualificadores_and_year(
        qualificadores_ids=[q.seq_qualificador for q in quals_receita],
        cod_tipo=id_entrada,
        ano=ano
    )

    # Total Despesas Realizadas
    total_despesas_ano = lancamento_repo.get_sum_by_qualificadores_and_year(
        qualificadores_ids=[q.seq_qualificador for q in quals_despesa],
        cod_tipo=id_saida,
        ano=ano
    )
    total_despesas_ano = abs(total_despesas_ano)

    # Superávit Primário
    superavit_primario = rcl - total_despesas_ano

    # Despesa com Pessoal
    despesa_pessoal = 0
    for qual in quals_despesa:
        if 'pessoal' in qual.dsc_qualificador.lower() or 'folha' in qual.dsc_qualificador.lower():
            valor = lancamento_repo.get_sum_by_qualificadores_and_year(
                qualificadores_ids=[qual.seq_qualificador],
                cod_tipo=id_saida,
                ano=ano
            )
            despesa_pessoal += abs(valor)

    # Aplicação em Saúde
    aplicacao_saude = 0
    for qual in quals_despesa:
        if 'saúde' in qual.dsc_qualificador.lower() or 'saude' in qual.dsc_qualificador.lower():
            valor = lancamento_repo.get_sum_by_qualificadores_and_year(
                qualificadores_ids=[qual.seq_qualificador],
                cod_tipo=id_saida,
                ano=ano
            )
            aplicacao_saude += abs(valor)

    # Aplicação em Educação
    aplicacao_educacao = 0
    for qual in quals_despesa:
        if 'educação' in qual.dsc_qualificador.lower() or 'educacao' in qual.dsc_qualificador.lower():
            valor = lancamento_repo.get_sum_by_qualificadores_and_year(
                qualificadores_ids=[qual.seq_qualificador],
                cod_tipo=id_saida,
                ano=ano
            )
            aplicacao_educacao += abs(valor)

    # Calcular percentuais
    perc_despesa_pessoal = (despesa_pessoal / rcl * 100) if rcl > 0 else 0
    perc_saude = (aplicacao_saude / total_despesas_ano * 100) if total_despesas_ano > 0 else 0
    perc_educacao = (aplicacao_educacao / total_despesas_ano * 100) if total_despesas_ano > 0 else 0

    # Usar LOA total de receita como referência para meta de superávit
    loa_receita_total = loa_repo.get_total_by_year(ano, 'receita')
    meta_superavit = loa_receita_total * 0.02 if loa_receita_total > 0 else rcl * 0.02

    # Dívida Consolidada (simplificado)
    divida_consolidada_rcl = 45.0

    metas_fiscais = []

    # Meta 1: Superávit Primário
    status_superavit = 'ATINGIDO' if superavit_primario >= meta_superavit else 'CRÍTICO'
    metas_fiscais.append({
        'nome': 'Superávit Primário',
        'meta': f'≥ {format_currency_short(meta_superavit)}',
        'realizado': format_currency_short(superavit_primario),
        'percentual': round((superavit_primario / meta_superavit * 100) if meta_superavit > 0 else 0, 1),
        'status': status_superavit
    })

    # Meta 2: Dívida Consolidada / RCL
    status_divida = 'DENTRO DA META' if divida_consolidada_rcl <= 200 else 'ATENÇÃO'
    metas_fiscais.append({
        'nome': 'Dívida Consolidada / RCL',
        'meta': '≤ 200%',
        'realizado': f'{divida_consolidada_rcl}%',
        'percentual': divida_consolidada_rcl,
        'status': status_divida
    })

    # Meta 3: Despesa com Pessoal / RCL
    status_pessoal = 'DENTRO DA META' if perc_despesa_pessoal <= 60 else 'ATENÇÃO' if perc_despesa_pessoal <= 70 else 'CRÍTICO'
    metas_fiscais.append({
        'nome': 'Despesa com Pessoal / RCL',
        'meta': '≤ 60%',
        'realizado': f'{round(perc_despesa_pessoal, 1)}%',
        'percentual': round(perc_despesa_pessoal, 1),
        'status': status_pessoal
    })

    # Meta 4: Aplicação em Saúde
    status_saude = 'DENTRO DA META' if perc_saude >= 15 else 'ATENÇÃO'
    metas_fiscais.append({
        'nome': 'Aplicação em Saúde',
        'meta': '≥ 15%',
        'realizado': f'{round(perc_saude, 1)}%',
        'percentual': round(perc_saude, 1),
        'status': status_saude
    })

    # Meta 5: Aplicação em Educação
    status_educacao = 'DENTRO DA META' if perc_educacao >= 25 else 'ATENÇÃO'
    metas_fiscais.append({
        'nome': 'Aplicação em Educação',
        'meta': '≥ 25%',
        'realizado': f'{round(perc_educacao, 1)}%',
        'percentual': round(perc_educacao, 1),
        'status': status_educacao
    })

    return metas_fiscais


def format_currency_short(value: float) -> str:
    """Formata valor em formato abreviado (M para milhões)."""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f'R$ {abs_value / 1_000_000_000:.2f} B'
    elif abs_value >= 1_000_000:
        return f'R$ {abs_value / 1_000_000:.1f} M'
    elif abs_value >= 1_000:
        return f'R$ {abs_value / 1_000:.1f} K'
    else:
        return f'R$ {abs_value:.2f}'
