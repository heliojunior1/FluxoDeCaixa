"""Controle de Despesa service - Seguindo Repository Pattern."""
from datetime import date
import calendar

from ...models import CenarioAjusteMensal, Qualificador
from ...repositories.lancamento_repository import LancamentoRepository
from .base import get_tipo_lancamento_ids


def get_controle_despesa_data(
    ano: int,
    cenario_id: int | None,
    qualificadores_ids: list[int],
    meses: list[int] | None = None
) -> dict:
    """
    Retorna dados para o relatório de Controle de Despesa.
    
    Args:
        ano: Ano para análise
        cenario_id: ID do cenário selecionado (None = sem projeção)
        qualificadores_ids: Lista de IDs de qualificadores de despesa
        meses: Lista de meses (1-12), None = todos os meses
    
    Returns:
        {
            'kpis': {
                'previsao_total': float,
                'executado_total': float,
                'saldo_projetado': float
            },
            'evolucao_mensal': [
                {
                    'mes': str,
                    'mes_num': int,
                    'realizado': float | None,
                    'previsao': float | None,
                    'is_futuro': bool
                }
            ],
            'execucao_por_grupo': [
                {
                    'qualificador_nome': str,
                    'qualificador_id': int,
                    'executado_total': float,
                    'previsao_total': float,
                    'percentual_execucao': float
                }
            ],
            'mes_atual': int
        }
    """
    # Determinar meses a analisar
    meses_selecionados = meses if meses else list(range(1, 13))
    meses_nomes = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
    
    # ID do tipo Saída
    tipo_ids = get_tipo_lancamento_ids()
    id_saida = tipo_ids['saida']
    
    # Mês atual para determinar se é histórico ou futuro
    hoje = date.today()
    mes_atual = hoje.month if hoje.year == ano else (13 if ano < hoje.year else 0)
    
    # Inicializar repository
    lancamento_repo = LancamentoRepository()
    
    # Carregar ajustes do cenário se fornecido
    ajustes_cenario = {}
    if cenario_id:
        ajustes = CenarioAjusteMensal.query.filter_by(
            seq_cenario=cenario_id, ano=ano
        ).filter(
            CenarioAjusteMensal.seq_qualificador.in_(qualificadores_ids)
        ).all()
        ajustes_cenario = {(a.mes, a.seq_qualificador): a for a in ajustes}
    
    # --- 1. EVOLUÇÃO MENSAL ---
    evolucao_mensal = []
    total_executado = 0
    total_previsao = 0
    
    for mes in sorted(meses_selecionados):
        is_futuro = (ano > hoje.year) or (ano == hoje.year and mes > hoje.month)
        
        # Calcular valores realizados para meses históricos
        realizado_mes = None
        if not is_futuro:
            realizado_mes = lancamento_repo.get_sum_by_qualificadores_and_month(
                qualificadores_ids=qualificadores_ids,
                cod_tipo=id_saida,
                ano=ano,
                mes=mes
            )
            # Despesas são valores negativos, converter para positivo
            realizado_mes = abs(realizado_mes)
            total_executado += realizado_mes
        
        # Calcular previsão para meses futuros (ou todos se cenário selecionado)
        previsao_mes = None
        if cenario_id and (is_futuro or mes >= mes_atual):
            previsao_mes = 0
            
            # Buscar valores base do ano anterior
            ano_base = ano - 1
            for qual_id in qualificadores_ids:
                valor_base = lancamento_repo.get_sum_by_qualificadores_and_month(
                    qualificadores_ids=[qual_id],
                    cod_tipo=id_saida,
                    ano=ano_base,
                    mes=mes
                )
                valor_base = abs(valor_base)  # Converter para positivo
                
                # Aplicar ajuste do cenário se existir
                key = (mes, qual_id)
                if key in ajustes_cenario:
                    ajuste = ajustes_cenario[key]
                    if ajuste.cod_tipo_ajuste == 'P':
                        valor_base = valor_base * (1 + float(ajuste.val_ajuste) / 100)
                    elif ajuste.cod_tipo_ajuste == 'V':
                        valor_base = valor_base + float(ajuste.val_ajuste)
                
                previsao_mes += valor_base
            
            total_previsao += previsao_mes
        
        evolucao_mensal.append({
            'mes': meses_nomes[mes][:3],
            'mes_num': mes,
            'realizado': round(realizado_mes, 2) if realizado_mes is not None else None,
            'previsao': round(previsao_mes, 2) if previsao_mes is not None else None,
            'is_futuro': is_futuro
        })
    
    # --- 2. EXECUÇÃO POR GRUPO ---
    execucao_por_grupo = []
    
    for qual_id in qualificadores_ids:
        # Buscar nome do qualificador
        qualificador = Qualificador.query.get(qual_id)
        if not qualificador:
            continue
        
        # Total executado (liquidado) no ano
        executado_total = lancamento_repo.get_sum_by_qualificadores_and_year(
            qualificadores_ids=[qual_id],
            cod_tipo=id_saida,
            ano=ano
        )
        executado_total = abs(executado_total)  # Converter para positivo
        
        # Total previsto no cenário (todos os 12 meses)
        previsao_total = 0
        if cenario_id:
            ano_base = ano - 1
            for mes in range(1, 13):
                valor_base = lancamento_repo.get_sum_by_qualificadores_and_month(
                    qualificadores_ids=[qual_id],
                    cod_tipo=id_saida,
                    ano=ano_base,
                    mes=mes
                )
                valor_base = abs(valor_base)
                
                # Aplicar ajuste do cenário
                key = (mes, qual_id)
                if key in ajustes_cenario:
                    ajuste = ajustes_cenario[key]
                    if ajuste.cod_tipo_ajuste == 'P':
                        valor_base = valor_base * (1 + float(ajuste.val_ajuste) / 100)
                    elif ajuste.cod_tipo_ajuste == 'V':
                        valor_base = valor_base + float(ajuste.val_ajuste)
                
                previsao_total += valor_base
        
        # Percentual de execução
        percentual_execucao = 0
        if previsao_total > 0:
            percentual_execucao = (executado_total / previsao_total) * 100
        
        execucao_por_grupo.append({
            'qualificador_nome': qualificador.dsc_qualificador,
            'qualificador_id': qual_id,
            'executado_total': round(executado_total, 2),
            'previsao_total': round(previsao_total, 2),
            'percentual_execucao': round(percentual_execucao, 2)
        })
    
    # --- 3. KPIs ---
    # Calcular totais completos se cenário estiver selecionado
    previsao_total_anual = 0
    if cenario_id:
        ano_base = ano - 1
        for mes in range(1, 13):
            for qual_id in qualificadores_ids:
                valor_base = lancamento_repo.get_sum_by_qualificadores_and_month(
                    qualificadores_ids=[qual_id],
                    cod_tipo=id_saida,
                    ano=ano_base,
                    mes=mes
                )
                valor_base = abs(valor_base)
                
                key = (mes, qual_id)
                if key in ajustes_cenario:
                    ajuste = ajustes_cenario[key]
                    if ajuste.cod_tipo_ajuste == 'P':
                        valor_base = valor_base * (1 + float(ajuste.val_ajuste) / 100)
                    elif ajuste.cod_tipo_ajuste == 'V':
                        valor_base = valor_base + float(ajuste.val_ajuste)
                
                previsao_total_anual += valor_base
    
    # Total executado até agora
    executado_total_anual = lancamento_repo.get_sum_by_qualificadores_and_year(
        qualificadores_ids=qualificadores_ids,
        cod_tipo=id_saida,
        ano=ano
    )
    executado_total_anual = abs(executado_total_anual)
    
    saldo_projetado = previsao_total_anual - executado_total_anual
    
    kpis = {
        'previsao_total': round(previsao_total_anual, 2),
        'executado_total': round(executado_total_anual, 2),
        'saldo_projetado': round(saldo_projetado, 2)
    }
    
    return {
        'kpis': kpis,
        'evolucao_mensal': evolucao_mensal,
        'execucao_por_grupo': execucao_por_grupo,
        'mes_atual': mes_atual
    }
