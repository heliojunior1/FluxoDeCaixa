from __future__ import annotations

from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from ..models import Pagamento, Orgao
from ..models.base import db
from ..domain import PagamentoCreate


class PagamentoRepository:
    """Data access layer for Pagamento records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def list_pagamentos(self):
        return (
            self.session.query(Pagamento)
            .order_by(Pagamento.dat_pagamento.desc())
            .all()
        )

    def list_orgaos(self):
        return self.session.query(Orgao).all()

    def get_sum_by_orgao_and_period(
        self,
        cod_orgao: int,
        start_date: date,
        end_date: date
    ) -> float:
        """Get sum of pagamentos by orgao and period.
        
        Args:
            cod_orgao: Orgao code
            start_date: Start date
            end_date: End date
        
        Returns:
            Sum value
        """
        result = self.session.query(func.sum(Pagamento.val_pagamento)).filter(
            Pagamento.dat_pagamento.between(start_date, end_date),
            Pagamento.cod_orgao == cod_orgao,
        ).scalar()
        
        return float(result or 0)

    def get_available_years(self) -> list[int]:
        """Get list of years with pagamento data.
        
        Returns:
            List of years sorted descending
        """
        years = self.session.query(
            extract("year", Pagamento.dat_pagamento)
        ).distinct().all()
        
        return sorted([int(y[0]) for y in years if y[0]], reverse=True)

    def create(self, data: PagamentoCreate) -> Pagamento:
        pag = Pagamento(
            dat_pagamento=data.dat_pagamento,
            cod_orgao=data.cod_orgao,
            val_pagamento=data.val_pagamento,
            dsc_pagamento=data.dsc_pagamento,
        )
        self.session.add(pag)
        self.session.commit()
        return pag

