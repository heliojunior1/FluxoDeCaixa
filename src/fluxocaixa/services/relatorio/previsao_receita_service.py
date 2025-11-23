"""Previsão de Receita service - Refatorado para usar Repository Pattern."""
from datetime import date
import calendar
import pandas as pd

from ...models import Qualificador
from ...repositories.lancamento_repository import LancamentoRepository
from .base import get_tipo_lancamento_ids
from ...utils.constants import MONTH_NAME_PT
from ..simulador_cenario_service import executar_simulacao


def get_previsao_receita_data(
    ano: int,
    cenario_id: int | None,
    qualificadores_ids: list[int],
    meses: list[int] | None = None
) -> dict:
    """
    Retorna dados para o relatório de Previsão de Receita.
    
    Args:
        ano: Ano para análise
        cenario_id: ID do cenário selecionado (None = sem projeção)
        qualificadores_ids: Lista de IDs de qualificadores de receita
        meses: Lista de meses (1-12), None = todos os meses
    
    Returns:
        {
            'evolucao_mensal': [
                {
                    'mes': str,
                    'mes_num': int,
                    'realizado': float | None,
                    'previsao': float | None,
                    'is_futuro': bool
                }
            ],
            'composicao_anual': [
                {
                    'qualificador_nome': str,
                    'qualificador_id': int,
                    'realizado_total': float,
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
    
    # ID do tipo Entrada
    tipo_ids = get_tipo_lancamento_ids()
    id_entrada = tipo_ids['entrada']
    
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
        if simulacao_resultado and 'projecao_receita_detalhada' in simulacao_resultado:
            df_detalhado = simulacao_resultado['projecao_receita_detalhada']
            if df_detalhado is not None and not df_detalhado.empty:
                df_detalhado['data'] = pd.to_datetime(df_detalhado['data'])
    
    # --- 1. EVOLUÇÃO MENSAL ---
    evolucao_mensal = []
    
    for mes in sorted(meses_selecionados):
        is_futuro = (ano > hoje.year) or (ano == hoje.year and mes > hoje.month)
        
        # Calcular valores realizados para meses históricos usando repository
        realizado_mes = None
        if not is_futuro:
            realizado_mes = lancamento_repo.get_sum_by_qualificadores_and_month(
                qualificadores_ids=qualificadores_ids,
                cod_tipo=id_entrada,
                ano=ano,
                mes=mes
            )
        
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
        
        evolucao_mensal.append({
            'mes': meses_nomes[mes][:3],  # Jan, Fev, Mar...
            'mes_num': mes,
            'realizado': round(realizado_mes, 2) if realizado_mes is not None else None,
            'previsao': round(previsao_mes, 2) if previsao_mes is not None else None,
            'is_futuro': is_futuro
        })
    
    # --- 2. COMPOSIÇÃO ANUAL ---
    composicao_anual = []
    
    for qual_id in qualificadores_ids:
        # Buscar nome do qualificador
        qualificador = Qualificador.query.get(qual_id)
        if not qualificador:
            continue
        
        # Total realizado no ano usando repository
        realizado_total = lancamento_repo.get_sum_by_qualificadores_and_year(
            qualificadores_ids=[qual_id],
            cod_tipo=id_entrada,
            ano=ano
        )
        
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
            percentual_execucao = (realizado_total / previsao_total) * 100
        
        composicao_anual.append({
            'qualificador_nome': qualificador.dsc_qualificador,
            'qualificador_id': qual_id,
            'realizado_total': round(realizado_total, 2),
            'previsao_total': round(previsao_total, 2),
            'percentual_execucao': round(percentual_execucao, 2)
        })
    
    return {
        'evolucao_mensal': evolucao_mensal,
        'composicao_anual': composicao_anual,
        'mes_atual': mes_atual
    }
