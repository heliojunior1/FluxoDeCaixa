from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract

from ..models import Pagamento, Orgao, Qualificador
from ..models.base import db
from ..domain import PagamentoCreate


class PagamentoRepository:
    """Data access layer for Pagamento records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def list_pagamentos(self):
        return (
            self.session.query(Pagamento)
            .options(joinedload(Pagamento.qualificador))
            .order_by(Pagamento.dat_pagamento.desc())
            .all()
        )

    def list_orgaos(self):
        return self.session.query(Orgao).order_by(Orgao.nom_orgao).all()
    
    def list_qualificadores(self):
        """List all active qualificadores for payment selection."""
        return self.session.query(Qualificador).filter_by(ind_status='A').order_by(Qualificador.num_qualificador).all()

    def get_sum_by_orgao_and_period(
        self,
        start_date: date,
        end_date: date
    ) -> dict[str, float]:
        """Get sum of pagamentos by orgao in a period.
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            Dictionary mapping orgao name to sum
        """
        results = self.session.query(
            Orgao.nom_orgao,
            func.sum(Pagamento.val_pagamento)
        ).join(Orgao).filter(
            Pagamento.dat_pagamento >= start_date,
            Pagamento.dat_pagamento <= end_date,
        ).group_by(Orgao.nom_orgao).all()
        
        return {r[0]: float(r[1] or 0) for r in results}

    def get_stats(self) -> tuple[int, float]:
        """Get count and total sum of all pagamentos.
        
        Returns:
            Tuple (count, total)
        """
        count = self.session.query(Pagamento).count()
        total = self.session.query(func.sum(Pagamento.val_pagamento)).scalar()
        
        return count, float(total or 0)

    def get_available_years(self) -> list[int]:
        """Get list of years with pagamento data.
        
        Returns:
            List of years sorted descending
        """
        years = self.session.query(
            extract("year", Pagamento.dat_pagamento)
        ).distinct().all()
        
        return sorted([int(y[0]) for y in years if y[0]], reverse=True)

    def get_comparative_by_orgao(
        self,
        anos: list[int],
        meses: list[int]
    ) -> list:
        """Get comparative data by orgao.
        
        Args:
            anos: List of years to compare
            meses: List of months to include
        
        Returns:
            List of tuples (orgao, year, month, total)
        """
        results = self.session.query(
            Orgao.nom_orgao,
            extract("year", Pagamento.dat_pagamento).label("year"),
            extract("month", Pagamento.dat_pagamento).label("month"),
            func.sum(Pagamento.val_pagamento).label("total"),
        ).join(Orgao).filter(
            extract("year", Pagamento.dat_pagamento).in_(anos),
            extract("month", Pagamento.dat_pagamento).in_(meses),
        ).group_by("nom_orgao", "year", "month").all()
        
        return results

    def get_comparative_by_qualificador(
        self,
        anos: list[int],
        meses: list[int]
    ) -> list:
        """Get comparative data by qualificador.
        
        Args:
            anos: List of years to compare
            meses: List of months to include
        
        Returns:
            List of tuples (qualificador_name, year, month, total)
        """
        results = self.session.query(
            Qualificador.dsc_qualificador,
            extract("year", Pagamento.dat_pagamento).label("year"),
            extract("month", Pagamento.dat_pagamento).label("month"),
            func.sum(Pagamento.val_pagamento).label("total"),
        ).join(Qualificador).filter(
            extract("year", Pagamento.dat_pagamento).in_(anos),
            extract("month", Pagamento.dat_pagamento).in_(meses),
        ).group_by(Qualificador.dsc_qualificador, "year", "month").all()
        
        return results

    def create(self, data: PagamentoCreate) -> Pagamento:
        pag = Pagamento(
            dat_pagamento=data.dat_pagamento,
            cod_orgao=data.cod_orgao,
            seq_qualificador=data.seq_qualificador,
            val_pagamento=data.val_pagamento,
            dsc_pagamento=data.dsc_pagamento,
        )
        self.session.add(pag)
        self.session.commit()
        return pag

