"""Indicadores (Indicators) service - financial metrics and charts."""
from datetime import date
import calendar

from ...repositories.lancamento_repository import LancamentoRepository
from ...repositories.pagamento_repository import PagamentoRepository
from ...models import OrigemLancamento, Orgao
from .base import get_tipo_lancamento_ids


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
    meses_nomes = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
    tipo_ids = get_tipo_lancamento_ids()
    id_entrada = tipo_ids['entrada']
    id_saida = tipo_ids['saida']
    
    # Initialize repositories
    lancamento_repo = LancamentoRepository()
    pagamento_repo = PagamentoRepository()
    
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

    # Pie chart: Distribution by origem (revenue) or orgao (expense)
    pie_chart_data = {"labels": [], "values": []}
    
    if tipo_selecionado in ("receita", "ambos"):
        origens = OrigemLancamento.query.all()
        for origem in origens:
            total_origem = 0
            for mes in meses_selecionados:
                month_start = date(ano_selecionado, mes, 1)
                month_end = (
                    date(ano_selecionado + 1, 1, 1)
                    if mes == 12
                    else date(ano_selecionado, mes + 1, 1)
                )
                valor = lancamento_repo.get_sum_by_origem_and_period(
                    cod_origem=origem.cod_origem_lancamento,
                    cod_tipo=id_entrada,
                    start_date=month_start,
                    end_date=month_end
                )
                total_origem += float(valor)
            if total_origem > 0:
                pie_chart_data["labels"].append(origem.dsc_origem_lancamento)
                pie_chart_data["values"].append(total_origem)
    elif tipo_selecionado == "despesa":
        orgaos = Orgao.query.all()
        for orgao in orgaos:
            total_orgao = 0
            for mes in meses_selecionados:
                month_start = date(ano_selecionado, mes, 1)
                month_end = (
                    date(ano_selecionado + 1, 1, 1)
                    if mes == 12
                    else date(ano_selecionado, mes + 1, 1)
                )
                valor = pagamento_repo.get_sum_by_orgao_and_period(
                    cod_orgao=orgao.cod_orgao,
                    start_date=month_start,
                    end_date=month_end
                )
                total_orgao += float(valor)
            if total_orgao > 0:
                pie_chart_data["labels"].append(orgao.nom_orgao)
                pie_chart_data["values"].append(total_orgao)

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
