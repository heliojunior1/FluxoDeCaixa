"""Saldos diários (Daily balance) service."""
from datetime import date, timedelta

from ...models import ContaBancaria
from ...repositories.lancamento_repository import LancamentoRepository
from ...repositories.saldo_conta_repository import SaldoContaRepository


def get_saldos_diarios_data(data_ref: date) -> dict:
    """Get daily balance data for all active bank accounts.
    
    This service crosses bank balance information (from flc_saldo_conta)
    with transaction data (from flc_lancamento).
    
    Args:
        data_ref: Reference date for balance calculation
    
    Returns:
        Dictionary with daily balances per account, totals, and 30-day evolution chart
    """
    lancamento_repo = LancamentoRepository()
    saldo_repo = SaldoContaRepository()
    contas = ContaBancaria.query.filter_by(ind_status="A").all()
    rows = []
    total_saldo_anterior = total_entradas = total_saidas = total_saldo_final = 0.0

    for c in contas:
        # Get initial balance from SaldoConta table
        saldo_conta = saldo_repo.get_saldo_by_conta_and_date(c.seq_conta, data_ref)
        
        # If no exact balance for this date, get the most recent one before it
        saldo_exato = True
        if not saldo_conta:
            saldo_conta = saldo_repo.get_latest_saldo_before_date(c.seq_conta, data_ref)
            saldo_exato = False
        
        saldo_inicial = float(saldo_conta.val_saldo) if saldo_conta else 0.0
        
        # Get transactions linked to this specific account (seq_conta filter)
        entradas_dia = lancamento_repo.get_sum_by_account_on_date_positive(
            seq_conta=c.seq_conta,
            on_date=data_ref
        )
        
        saidas_dia = lancamento_repo.get_sum_by_account_on_date_negative(
            seq_conta=c.seq_conta,
            on_date=data_ref
        )

        # Calculate final balance
        saldo_final = saldo_inicial + float(entradas_dia) - float(saidas_dia)
        
        # Check for divergence with next day's bank balance
        saldo_proximo_dia = saldo_repo.get_saldo_by_conta_and_date(
            c.seq_conta, 
            data_ref + timedelta(days=1)
        )
        
        divergencia = None
        if saldo_proximo_dia:
            divergencia = float(saldo_proximo_dia.val_saldo) - saldo_final

        rows.append(
            {
                "conta": c,
                "saldo_inicial": saldo_inicial,
                "saldo_exato": saldo_exato,  # Indicator if balance is exact or estimated
                "entradas_dia": float(entradas_dia),
                "saidas_dia": float(saidas_dia),
                "saldo_final": saldo_final,
                "divergencia": divergencia,
            }
        )

        total_saldo_anterior += saldo_inicial
        total_entradas += float(entradas_dia)
        total_saidas += float(saidas_dia)
        total_saldo_final += saldo_final

    # Compute 30-day evolution using SaldoConta data
    labels = []
    serie_saldo = []
    start_day = data_ref - timedelta(days=29)
    
    cur = start_day
    while cur <= data_ref:
        # Get total balance for all accounts on this date
        total_dia = saldo_repo.get_saldo_total_by_date(cur)
        
        # If no balance for this specific date, try to get from previous date
        if total_dia == 0:
            total_dia = saldo_repo.get_latest_saldo_total_before_date(cur)
        
        labels.append(cur.strftime("%Y-%m-%d"))
        serie_saldo.append(total_dia)
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
