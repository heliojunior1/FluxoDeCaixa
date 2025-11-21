"""Resumo (Cash Flow Summary) service."""
from datetime import date
import calendar
from sqlalchemy import extract

from ...models import db, CenarioAjusteMensal
from ...repositories.lancamento_repository import LancamentoRepository
from .base import get_tipo_lancamento_ids


def get_resumo_data(
    ano_selecionado: int,
    meses_selecionados: list[int],
    estrategia: str,
    cenario_selecionado_id: int | None
) -> dict:
    """Get cash flow summary data for selected year and months.
    
    Args:
        ano_selecionado: Year to analyze
        meses_selecionados: List of months (1-12)
        estrategia: 'realizado' or 'projetado'
        cenario_selecionado_id: ID of scenario if strategy is 'projetado'
    
    Returns:
        Dictionary with summary data including totals and cash flow chart data
    """
    meses_nomes = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
    tipo_ids = get_tipo_lancamento_ids()
    id_entrada = tipo_ids['entrada']
    id_saida = tipo_ids['saida']
    
    # Initialize repository
    lancamento_repo = LancamentoRepository()

    # Calculate period totals using repository
    total_entradas_periodo = lancamento_repo.get_total_by_tipo_and_period(
        cod_tipo=id_entrada,
        ano=ano_selecionado,
        meses=meses_selecionados
    )
    
    total_saidas_lanc = lancamento_repo.get_total_by_tipo_and_period(
        cod_tipo=id_saida,
        ano=ano_selecionado,
        meses=meses_selecionados
    )
    total_saidas_periodo = abs(total_saidas_lanc)
    disponibilidade_periodo = total_entradas_periodo - total_saidas_periodo

    # Load scenario adjustments if in projection mode
    ajustes_cenario = {}
    if estrategia == "projetado" and cenario_selecionado_id:
        ajustes = CenarioAjusteMensal.query.filter_by(
            seq_cenario=cenario_selecionado_id, ano=ano_selecionado
        ).all()
        ajustes_cenario = {(a.ano, a.mes, a.seq_qualificador): a for a in ajustes}

    # Build cash flow data month by month
    cash_flow_data = {
        "labels": [],
        "receitas": [],
        "despesas": [],
        "saldos": [],
        "saldo_final": [],
        "meses_projetados": [],
    }
    saldo_acumulado = 0
    hoje = date.today()
    total_entradas_recalc = 0
    total_saidas_recalc = 0

    for mes in sorted(meses_selecionados):
        projetar_mes = (
            estrategia == "projetado"
            and ajustes_cenario
            and (
                ano_selecionado > hoje.year
                or (ano_selecionado == hoje.year and mes >= hoje.month)
            )
        )
        receitas_mes = 0
        despesas_mes = 0
        
        if projetar_mes:
            # Use base data from previous year and apply adjustments
            lancamentos_base = lancamento_repo.get_grouped_by_qualificador_and_period(
                ano=ano_selecionado - 1,
                mes=mes,
                groupby_column=extract("month", db.session.query(db.Model).subquery().c.dat_lancamento)
            )
            
            # Create a mapping for easier lookup
            from ...models import Lancamento
            base_query = db.session.query(
                Lancamento.seq_qualificador,
                Lancamento.cod_tipo_lancamento,
                db.func.sum(Lancamento.val_lancamento).label("total"),
            ).filter(
                extract("year", Lancamento.dat_lancamento) == ano_selecionado - 1,
                extract("month", Lancamento.dat_lancamento) == mes,
                Lancamento.ind_status == "A",
            ).group_by(Lancamento.seq_qualificador, Lancamento.cod_tipo_lancamento).all()
            
            for seq_qualificador, cod_tipo_lancamento, total_base in base_query:
                total_base = float(total_base or 0)
                valor_ajustado = total_base
                key = (ano_selecionado, mes, seq_qualificador)
                if key in ajustes_cenario:
                    ajuste = ajustes_cenario[key]
                    if ajuste.cod_tipo_ajuste == "P":
                        valor_ajustado = total_base * (
                            1 + float(ajuste.val_ajuste) / 100
                        )
                    elif ajuste.cod_tipo_ajuste == "V":
                        valor_ajustado = total_base + float(ajuste.val_ajuste)
                if cod_tipo_lancamento == id_entrada:
                    receitas_mes += valor_ajustado
                elif cod_tipo_lancamento == id_saida:
                    despesas_mes += abs(valor_ajustado)
        else:
            # Use actual data from repository
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
        
        cash_flow_data["labels"].append(meses_nomes[mes][:3])
        cash_flow_data["receitas"].append(float(receitas_mes))
        cash_flow_data["despesas"].append(float(despesas_mes))
        cash_flow_data["meses_projetados"].append(projetar_mes)
        total_entradas_recalc += float(receitas_mes)
        total_saidas_recalc += float(despesas_mes)
        saldo_mes = float(receitas_mes) - float(despesas_mes)
        saldo_acumulado += saldo_mes
        cash_flow_data["saldos"].append(saldo_mes)
        cash_flow_data["saldo_final"].append(saldo_acumulado)

    if estrategia == "projetado" and ajustes_cenario:
        total_entradas_periodo = total_entradas_recalc
        total_saidas_periodo = total_saidas_recalc
        disponibilidade_periodo = total_entradas_periodo - total_saidas_periodo
        
    return {
        "total_entradas_periodo": total_entradas_periodo,
        "total_saidas_periodo": total_saidas_periodo,
        "disponibilidade_periodo": disponibilidade_periodo,
        "cash_flow_data": cash_flow_data,
        "meses_nomes": meses_nomes,
    }
