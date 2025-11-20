"""Comparative analysis service."""
from datetime import date
import calendar
from sqlalchemy import func, extract

from ...models import db, Lancamento, Pagamento, OrigemLancamento, Orgao, TipoLancamento


def get_analise_comparativa_data(
    ano1: int,
    ano2: int,
    meses_selecionados: list[int],
    tipo_analise: str
) -> dict:
    """Get comparative analysis data between two years.
    
    Args:
        ano1: First year to compare
        ano2: Second year to compare
        meses_selecionados: List of months to include (1-12)
        tipo_analise: 'receitas' or 'despesas'
    
    Returns:
        Dictionary with comparative data per item and totals
    """
    meses_nomes = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
    data = {}
    totals = {str(m): {str(ano1): 0, str(ano2): 0} for m in meses_selecionados}
    totals["total"] = {str(ano1): 0, str(ano2): 0}

    if tipo_analise == "receitas":
        tipo_entrada = TipoLancamento.query.filter_by(
            dsc_tipo_lancamento="Entrada"
        ).first()
        id_entrada = tipo_entrada.cod_tipo_lancamento if tipo_entrada else -1
        query = (
            db.session.query(
                OrigemLancamento.dsc_origem_lancamento,
                extract("year", Lancamento.dat_lancamento).label("year"),
                extract("month", Lancamento.dat_lancamento).label("month"),
                func.sum(Lancamento.val_lancamento).label("total"),
            )
            .join(OrigemLancamento)
            .filter(
                Lancamento.cod_tipo_lancamento == id_entrada,
                extract("year", Lancamento.dat_lancamento).in_([ano1, ano2]),
                extract("month", Lancamento.dat_lancamento).in_(meses_selecionados),
            )
            .group_by("dsc_origem_lancamento", "year", "month")
        )
        results = query.all()
        all_items = [
            item[0]
            for item in db.session.query(OrigemLancamento.dsc_origem_lancamento)
            .distinct()
            .all()
        ]
    else:
        query = (
            db.session.query(
                Orgao.nom_orgao,
                extract("year", Pagamento.dat_pagamento).label("year"),
                extract("month", Pagamento.dat_pagamento).label("month"),
                func.sum(Pagamento.val_pagamento).label("total"),
            )
            .join(Orgao)
            .filter(
                extract("year", Pagamento.dat_pagamento).in_([ano1, ano2]),
                extract("month", Pagamento.dat_pagamento).in_(meses_selecionados),
            )
            .group_by("nom_orgao", "year", "month")
        )
        results = query.all()
        all_items = [
            item[0] for item in db.session.query(Orgao.nom_orgao).distinct().all()
        ]

    for item_name in all_items:
        data[item_name] = {str(m): {str(ano1): 0, str(ano2): 0} for m in range(1, 13)}
        data[item_name]["total"] = {str(ano1): 0, str(ano2): 0}

    for item, year, month, total_val in results:
        if item in data:
            data[item][str(month)][str(year)] = float(total_val or 0)

    for item_name, item_data in data.items():
        total1 = sum(item_data[str(m)][str(ano1)] for m in meses_selecionados)
        total2 = sum(item_data[str(m)][str(ano2)] for m in meses_selecionados)
        data[item_name]["total"][str(ano1)] = total1
        data[item_name]["total"][str(ano2)] = total2
        totals["total"][str(ano1)] += total1
        totals["total"][str(ano2)] += total2
        for m in meses_selecionados:
            totals[str(m)][str(ano1)] += item_data[str(m)][str(ano1)]
            totals[str(m)][str(ano2)] += item_data[str(m)][str(ano2)]
            
    return {
        "data": data,
        "totals": totals,
        "meses_nomes": meses_nomes,
    }
