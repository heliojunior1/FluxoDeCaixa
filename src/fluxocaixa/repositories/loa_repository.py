"""Repository for LOA (Lei Orçamentária Anual) data access."""
from __future__ import annotations

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from ..models.loa import Loa
from ..models.qualificador import Qualificador
from ..models.base import db


class LoaRepository:
    """Data access layer for Loa records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def get_by_year(self, ano: int) -> list[Loa]:
        """Get all LOA records for a specific year.

        Args:
            ano: Year to query

        Returns:
            List of Loa objects with qualificador eagerly loaded
        """
        return (
            self.session.query(Loa)
            .options(joinedload(Loa.qualificador))
            .filter(
                Loa.num_ano == ano,
                Loa.ind_status == 'A'
            )
            .all()
        )

    def get_by_year_and_tipo(self, ano: int, tipo_fluxo: str) -> list[Loa]:
        """Get LOA records filtered by year and tipo_fluxo (receita/despesa).

        Filters using the qualificador hierarchy: root num_qualificador
        starting with '1' = receita, '2' = despesa.

        Args:
            ano: Year to query
            tipo_fluxo: 'receita' or 'despesa'

        Returns:
            List of Loa objects matching the criteria
        """
        all_loa = self.get_by_year(ano)
        return [
            loa for loa in all_loa
            if loa.qualificador and loa.qualificador.tipo_fluxo == tipo_fluxo
        ]

    def get_total_by_year(self, ano: int, tipo_fluxo: str | None = None) -> float:
        """Get total LOA value for a year, optionally filtered by tipo_fluxo.

        Args:
            ano: Year to query
            tipo_fluxo: Optional 'receita' or 'despesa' filter

        Returns:
            Total LOA value
        """
        if tipo_fluxo:
            records = self.get_by_year_and_tipo(ano, tipo_fluxo)
        else:
            records = self.get_by_year(ano)

        return sum(float(loa.val_loa) for loa in records)

    def get_by_qualificador_and_year(
        self,
        seq_qualificador: int,
        ano: int
    ) -> float:
        """Get LOA value for a specific qualificador and year.

        Args:
            seq_qualificador: Qualificador ID
            ano: Year

        Returns:
            LOA value (0 if not found)
        """
        result = self.session.query(Loa.val_loa).filter(
            Loa.seq_qualificador == seq_qualificador,
            Loa.num_ano == ano,
            Loa.ind_status == 'A'
        ).scalar()

        return float(result) if result else 0.0

    def get_dict_by_year(self, ano: int, tipo_fluxo: str | None = None) -> dict[int, float]:
        """Get LOA values as a dict keyed by seq_qualificador.

        Args:
            ano: Year to query
            tipo_fluxo: Optional 'receita' or 'despesa' filter

        Returns:
            Dict mapping seq_qualificador -> val_loa
        """
        if tipo_fluxo:
            records = self.get_by_year_and_tipo(ano, tipo_fluxo)
        else:
            records = self.get_by_year(ano)

        return {
            loa.seq_qualificador: float(loa.val_loa)
            for loa in records
        }
