"""Indicadores (Indicators) service - financial metrics and charts."""
from datetime import date
import calendar

from ...repositories.lancamento_repository import LancamentoRepository
from .base import get_tipo_lancamento_ids
from ...utils.constants import MONTH_NAME_PT


def get_indicadores_data(
    ano_selecionado: int,
    meses_selecionados: list[int],
    tipo_selecionado: str
) -> dict:
    """Get financial indicators data (area chart, pie chart, projection chart).
    
    Args:
        ano_selecionado: Year to analyze
        meses_selecionados: List of months (1-12)
        tipo_selecionado: 'receita', 'despesa', or 'ambos'
    
    Returns:
        Dictionary with area_chart_data, pie_chart_data, and projection_chart_data
    """
    meses_nomes = MONTH_NAME_PT
    tipo_ids = get_tipo_lancamento_ids()
    id_entrada = tipo_ids['entrada']
    id_saida = tipo_ids['saida']
    
    # Initialize repository
    lancamento_repo = LancamentoRepository()
    
    # Area chart: Monthly revenues vs expenses
    area_chart_data = {"labels": [], "receitas": [], "despesas": []}

    for mes in sorted(meses_selecionados):
        receitas_mes = lancamento_repo.get_monthly_summary(
            ano=ano_selecionado,
            mes=mes,
            cod_tipo=id_entrada
        )
        
        despesas_lanc_mes = lancamento_repo.get_monthly_summary(
            ano=ano_selecionado,
            mes=mes,
            cod_tipo=id_saida
        )
        despesas_mes = abs(despesas_lanc_mes or 0)
        
        area_chart_data["labels"].append(meses_nomes[mes][:3])
        area_chart_data["receitas"].append(float(receitas_mes))
        area_chart_data["despesas"].append(float(despesas_mes))

    # Pie chart: Distribution by qualificador folha (leaf qualifiers)
    pie_chart_data = {"labels": [], "values": []}
    
    # Import Qualificador model
    from ...models import Qualificador
    qualificadores = Qualificador.query.filter_by(ind_status='A').all()
    qualificadores_folha = [q for q in qualificadores if q.is_folha()]
    
    if tipo_selecionado in ("receita", "ambos"):
        # Filter only revenue qualifiers (those under root 1.x)
        qualificadores_receita = [q for q in qualificadores_folha if q.tipo_fluxo == 'receita']
        
        for qualificador in qualificadores_receita:
            total_qualificador = 0
            for mes in meses_selecionados:
                # Use more efficient repository method
                month_total = lancamento_repo.get_sum_by_qualificadores_and_month(
                    qualificadores_ids=[qualificador.seq_qualificador],
                    cod_tipo=id_entrada,
                    ano=ano_selecionado,
                    mes=mes
                )
                total_qualificador += float(month_total)
            
            if total_qualificador > 0:
                pie_chart_data["labels"].append(qualificador.dsc_qualificador)
                pie_chart_data["values"].append(total_qualificador)
                
    elif tipo_selecionado == "despesa":
        # Filter only expense qualifiers (those under root 2.x)
        qualificadores_despesa = [q for q in qualificadores_folha if q.tipo_fluxo == 'despesa']
        
        for qualificador in qualificadores_despesa:
            total_qualificador = 0
            for mes in meses_selecionados:
                # Use more efficient repository method
                month_total = lancamento_repo.get_sum_by_qualificadores_and_month(
                    qualificadores_ids=[qualificador.seq_qualificador],
                    cod_tipo=id_saida,
                    ano=ano_selecionado,
                    mes=mes
                )
                total_qualificador += abs(float(month_total))
            
            if total_qualificador > 0:
                pie_chart_data["labels"].append(qualificador.dsc_qualificador)
                pie_chart_data["values"].append(total_qualificador)

    # Projection chart: Cumulative balance over time
    projection_chart_data = {"labels": [], "saldo": []}
    saldo_acumulado = 0
    
    for mes in sorted(meses_selecionados):
        receitas_mes = lancamento_repo.get_monthly_summary(
            ano=ano_selecionado,
            mes=mes,
            cod_tipo=id_entrada
        )
        
        despesas_lanc_mes = lancamento_repo.get_monthly_summary(
            ano=ano_selecionado,
            mes=mes,
            cod_tipo=id_saida
        )
        despesas_mes = abs(despesas_lanc_mes or 0)
        saldo_mes = float(receitas_mes) - float(despesas_mes)
        saldo_acumulado += saldo_mes
        projection_chart_data["labels"].append(meses_nomes[mes][:3])
        projection_chart_data["saldo"].append(saldo_acumulado)
        
    return {
        "area_chart_data": area_chart_data,
        "pie_chart_data": pie_chart_data,
        "projection_chart_data": projection_chart_data,
        "meses_nomes": meses_nomes,
    }
