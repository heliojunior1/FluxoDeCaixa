"""Saldos diários (Daily balance) service."""
from datetime import date, timedelta
from sqlalchemy import func

from ...models import db, Lancamento, ContaBancaria


def get_saldos_diarios_data(data_ref: date) -> dict:
    """Get daily balance data for all active bank accounts.
    
    Args:
        data_ref: Reference date for balance calculation
    
    Returns:
        Dictionary with daily balances per account, totals, and 30-day evolution chart
    """
    contas = ContaBancaria.query.filter_by(ind_status="A").all()
    rows = []
    total_saldo_anterior = total_entradas = total_saidas = total_saldo_final = 0.0

    for c in contas:
        saldo_ate_ontem = (
            db.session.query(func.sum(Lancamento.val_lancamento))
            .filter(
                Lancamento.seq_conta == c.seq_conta,
                Lancamento.dat_lancamento < data_ref,
                Lancamento.ind_status == "A",
            )
            .scalar()
            or 0
        )
        entradas_dia = (
            db.session.query(func.sum(Lancamento.val_lancamento))
            .filter(
                Lancamento.seq_conta == c.seq_conta,
                Lancamento.dat_lancamento == data_ref,
                Lancamento.val_lancamento > 0,
                Lancamento.ind_status == "A",
            )
            .scalar()
            or 0
        )
        saidas_dia = abs(
            db.session.query(func.sum(Lancamento.val_lancamento))
            .filter(
                Lancamento.seq_conta == c.seq_conta,
                Lancamento.dat_lancamento == data_ref,
                Lancamento.val_lancamento < 0,
                Lancamento.ind_status == "A",
            )
            .scalar()
            or 0
        )

        saldo_final = float(saldo_ate_ontem) + float(entradas_dia) - float(saidas_dia)

        rows.append(
            {
                "conta": c,
                "saldo_anterior": float(saldo_ate_ontem),
                "entradas_dia": float(entradas_dia),
                "saidas_dia": float(saidas_dia),
                "saldo_final": float(saldo_final),
            }
        )

        total_saldo_anterior += float(saldo_ate_ontem)
        total_entradas += float(entradas_dia)
        total_saidas += float(saidas_dia)
        total_saldo_final += float(saldo_final)

    # Compute 30-day evolution of total saldo (all accounts combined) ending at data_ref
    labels = []
    serie_saldo = []
    # Pre-calc cumulative up to previous day for first point efficiency
    start_day = data_ref - timedelta(days=29)
    # Build a map date->sum(val) for the window to avoid N*day queries
    vals_by_day = {
        d[0]: d[1] or 0
        for d in (
            db.session.query(Lancamento.dat_lancamento, func.sum(Lancamento.val_lancamento))
            .filter(
                Lancamento.ind_status == "A",
                Lancamento.dat_lancamento >= start_day,
                Lancamento.dat_lancamento <= data_ref,
            )
            .group_by(Lancamento.dat_lancamento)
            .all()
        )
    }
    # saldo up to day before start_day
    saldo_ate_vigencia_anterior = (
        db.session.query(func.sum(Lancamento.val_lancamento))
        .filter(
            Lancamento.ind_status == "A",
            Lancamento.dat_lancamento < start_day,
        )
        .scalar()
        or 0
    )
    running = float(saldo_ate_vigencia_anterior)
    cur = start_day
    while cur <= data_ref:
        running += float(vals_by_day.get(cur, 0))
        labels.append(cur.strftime("%Y-%m-%d"))
        serie_saldo.append(running)
        cur += timedelta(days=1)
        
    return {
        "rows": rows,
        "totais": {
            "saldo_anterior": total_saldo_anterior,
            "entradas": total_entradas,
            "saidas": total_saidas,
            "saldo_final": total_saldo_final,
        },
        "evolucao_labels": labels,
        "evolucao_saldos": serie_saldo,
    }
