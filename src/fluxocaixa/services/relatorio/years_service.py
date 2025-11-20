"""Years service - extract available years from data."""
from sqlalchemy import extract
from ...models import db, Lancamento, Pagamento


def get_available_years() -> list[int]:
    """Get list of years with lancamentos or pagamentos data.
    
    Returns:
        List of years sorted in descending order
    """
    lancamento_years = db.session.query(extract("year", Lancamento.dat_lancamento)).distinct().all()
    pagamento_years = db.session.query(extract("year", Pagamento.dat_pagamento)).distinct().all()
    years = sorted({y[0] for y in lancamento_years + pagamento_years}, reverse=True)
    return years
