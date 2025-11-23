"""Controle de Despesa service - Seguindo Repository Pattern."""
from datetime import date
import calendar
import pandas as pd

from ...models import Qualificador
from ...repositories.lancamento_repository import LancamentoRepository
from .base import get_tipo_lancamento_ids
from ...utils.constants import MONTH_NAME_PT
from ..simulador_cenario_service import executar_simulacao


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
    meses_nomes = MONTH_NAME_PT
    
    # ID do tipo Saída
    tipo_ids = get_tipo_lancamento_ids()
    id_saida = tipo_ids['saida']
    
    # Mês atual para determinar se é histórico ou futuro
    hoje = date.today()
    mes_atual = hoje.month if hoje.year == ano else (13 if ano < hoje.year else 0)
    
    # Inicializar repository
    lancamento_repo = LancamentoRepository()
    
    # Carregar simulação se cenário fornecido
    simulacao_resultado = None
    df_detalhado = None
    
    if cenario_id:
        simulacao_resultado = executar_simulacao(cenario_id)
        if simulacao_resultado and 'projecao_despesa_detalhada' in simulacao_resultado:
            df_detalhado = simulacao_resultado['projecao_despesa_detalhada']
            if df_detalhado is not None and not df_detalhado.empty:
                df_detalhado['data'] = pd.to_datetime(df_detalhado['data'])
    
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
            
            if df_detalhado is not None and not df_detalhado.empty:
                # Filtrar por ano, mês e qualificadores selecionados
                mask = (
                    (df_detalhado['data'].dt.year == ano) & 
                    (df_detalhado['data'].dt.month == mes) &
                    (df_detalhado['seq_qualificador'].isin(qualificadores_ids))
                )
                previsao_mes = float(df_detalhado.loc[mask, 'valor_projetado'].sum())
            
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
        if cenario_id and df_detalhado is not None and not df_detalhado.empty:
            # Filtrar por ano e qualificador específico
            mask = (
                (df_detalhado['data'].dt.year == ano) & 
                (df_detalhado['seq_qualificador'] == qual_id)
            )
            previsao_total = float(df_detalhado.loc[mask, 'valor_projetado'].sum())
        
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
    if cenario_id and df_detalhado is not None and not df_detalhado.empty:
        # Filtrar por ano e qualificadores selecionados
        mask = (
            (df_detalhado['data'].dt.year == ano) & 
            (df_detalhado['seq_qualificador'].isin(qualificadores_ids))
        )
        previsao_total_anual = float(df_detalhado.loc[mask, 'valor_projetado'].sum())
    
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
