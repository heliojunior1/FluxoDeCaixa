"""Seed data for SaldoConta (daily balances)."""

from datetime import date, timedelta
from sqlalchemy import and_

from ...models import SaldoConta, Lancamento, ContaBancaria
from ...models.base import db


def seed_saldos_conta(session=None):
    """Seed daily account balances."""
    session = session or db.session

    if SaldoConta.query.first():
        return  # Already seeded

    contas = ContaBancaria.query.filter_by(ind_status='A').all()
    if not contas:
        return

    # Base initial balances for each account (as of Dec 31, 2023)
    saldos_base = {
        1: 250000000.00,  # Conta Única - Tesouro
        2: 180000000.00,  # Conta Judicial
        3: 80000000.00,   # Conta Salário
        4: 150000000.00,  # Conta FPE
        5: 90000000.00,   # Recursos Próprios
    }

    data_inicio = date(2024, 1, 1)
    data_fim = date.today()

    for conta in contas:
        seq_conta = conta.seq_conta
        saldo_atual = saldos_base.get(seq_conta, 100000000.00)

        data_atual = data_inicio
        while data_atual <= data_fim:
            # Get transactions for this account on this day
            lancamentos_dia = session.query(Lancamento).filter(
                and_(
                    Lancamento.seq_conta == seq_conta,
                    Lancamento.dat_lancamento == data_atual
                )
            ).all()

            # Apply transactions to balance
            for lanc in lancamentos_dia:
                saldo_atual += float(lanc.val_lancamento)

            # Create balance record
            session.add(SaldoConta(
                seq_conta=seq_conta,
                dat_saldo=data_atual,
                val_saldo=round(saldo_atual, 2),
                cod_pessoa_inclusao=1
            ))

            data_atual += timedelta(days=1)

    session.commit()
    print(f"Seeded daily balances for {len(contas)} accounts from {data_inicio} to {data_fim}")
