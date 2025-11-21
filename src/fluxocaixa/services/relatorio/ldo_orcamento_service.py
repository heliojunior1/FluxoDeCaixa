"""LDO & Orçamento service - Monitoramento de Metas Fiscais."""
from datetime import date

from ...models import Qualificador
from ...repositories.lancamento_repository import LancamentoRepository
from .base import get_tipo_lancamento_ids


def get_ldo_orcamento_data(ano: int) -> dict:
    """
    Retorna dados para o relatório de LDO & Orçamento.
    
    Mostra:
    - Distribuição do Orçamento (LOA) por categoria (gráfico pizza)
    - Metas Fiscais (LDO) com status de cumprimento
    
    Args:
        ano: Ano para análise
    
    Returns:
        {
            'distribuicao_orcamento': [
                {
                    'categoria': str,
                    'valor': float,
                    'percentual': float
                }
            ],
            'metas_fiscais': [
                {
                    'nome': str,
                    'meta': str,
                    'realizado': str,
                    'percentual': float,
                    'status': 'ATINGIDO' | 'DENTRO DA META' | 'ATENÇÃO' | 'CRÍTICO'
                }
            ]
        }
    """
    # IDs dos tipos
    tipo_ids = get_tipo_lancamento_ids()
    id_entrada = tipo_ids['entrada']
    id_saida = tipo_ids['saida']
    
    # Inicializar repository
    lancamento_repo = LancamentoRepository()
    
    # --- 1. DISTRIBUIÇÃO DO ORÇAMENTO (LOA) ---
    # Buscar todos os qualificadores de despesa (folha)
    qualificadores_despesa = [
        q for q in Qualificador.query.filter_by(ind_status='A').all()
        if q.is_folha() and q.tipo_fluxo == 'despesa'
    ]
    
    distribuicao = []
    total_despesas = 0
    
    for qual in qualificadores_despesa:
        valor = lancamento_repo.get_sum_by_qualificadores_and_year(
            qualificadores_ids=[qual.seq_qualificador],
            cod_tipo=id_saida,
            ano=ano
        )
        valor = abs(valor)
        
        if valor > 0:
            distribuicao.append({
                'categoria': qual.dsc_qualificador,
                'valor': valor
            })
            total_despesas += valor
    
    # Calcular percentuais
    for item in distribuicao:
        item['percentual'] = (item['valor'] / total_despesas * 100) if total_despesas > 0 else 0
        item['valor'] = round(item['valor'], 2)
        item['percentual'] = round(item['percentual'], 2)
    
    # Ordenar por valor decrescente
    distribuicao.sort(key=lambda x: x['valor'], reverse=True)
    
    # --- 2. METAS FISCAIS (LDO) ---
    
    # Calcular Receita Corrente Líquida (RCL) simplificada
    # RCL = Total de Receitas do ano
    rcl = lancamento_repo.get_sum_by_qualificadores_and_year(
        qualificadores_ids=[q.seq_qualificador for q in Qualificador.query.filter_by(ind_status='A').all() if q.tipo_fluxo == 'receita'],
        cod_tipo=id_entrada,
        ano=ano
    )
    
    # Total de Despesas
    total_despesas_ano = lancamento_repo.get_sum_by_qualificadores_and_year(
        qualificadores_ids=[q.seq_qualificador for q in qualificadores_despesa],
        cod_tipo=id_saida,
        ano=ano
    )
    total_despesas_ano = abs(total_despesas_ano)
    
    # Calcular Superávit Primário
    superavit_primario = rcl - total_despesas_ano
    
    # Despesa com Pessoal (assumindo que existe um qualificador "Pessoal" ou similar)
    despesa_pessoal = 0
    for qual in qualificadores_despesa:
        if 'pessoal' in qual.dsc_qualificador.lower():
            valor = lancamento_repo.get_sum_by_qualificadores_and_year(
                qualificadores_ids=[qual.seq_qualificador],
                cod_tipo=id_saida,
                ano=ano
            )
            despesa_pessoal += abs(valor)
    
    # Aplicação em Saúde
    aplicacao_saude = 0
    for qual in qualificadores_despesa:
        if 'saúde' in qual.dsc_qualificador.lower() or 'saude' in qual.dsc_qualificador.lower():
            valor = lancamento_repo.get_sum_by_qualificadores_and_year(
                qualificadores_ids=[qual.seq_qualificador],
                cod_tipo=id_saida,
                ano=ano
            )
            aplicacao_saude += abs(valor)
    
    # Aplicação em Educação
    aplicacao_educacao = 0
    for qual in qualificadores_despesa:
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
    
    # Dívida Consolidada (simplificado - assumindo 45% como exemplo)
    divida_consolidada_rcl = 45.0  # Em produção, viria de outra fonte
    
    # Definir metas e status
    metas_fiscais = []
    
    # Meta 1: Superávit Primário
    meta_superavit = rcl * 0.02  # 2% da RCL
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
    
    return {
        'distribuicao_orcamento': distribuicao,
        'metas_fiscais': metas_fiscais
    }


def format_currency_short(value: float) -> str:
    """Formata valor em formato abreviado (M para milhões)."""
    abs_value = abs(value)
    if abs_value >= 1000000:
        return f'R$ {abs_value / 1000000:.1f} M'
    elif abs_value >= 1000:
        return f'R$ {abs_value / 1000:.1f} K'
    else:
        return f'R$ {abs_value:.2f}'
