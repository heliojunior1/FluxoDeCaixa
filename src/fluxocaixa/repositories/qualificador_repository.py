"""Repository for Qualificador data access."""
from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import Qualificador
from ..models.base import db


class QualificadorRepository:
    """Data access layer for Qualificador records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def get_all(self) -> list[Qualificador]:
        """Get all qualificadores ordered by number."""
        return self.session.query(Qualificador).order_by(Qualificador.num_qualificador).all()

    def get_active(self) -> list[Qualificador]:
        """Get only active qualificadores."""
        return (
            self.session.query(Qualificador)
            .filter_by(ind_status='A')
            .order_by(Qualificador.num_qualificador)
            .all()
        )

    def get_root(self) -> list[Qualificador]:
        """Get root qualificadores (no parent)."""
        return (
            self.session.query(Qualificador)
            .filter_by(ind_status='A', cod_qualificador_pai=None)
            .order_by(Qualificador.num_qualificador)
            .all()
        )

    def get_by_id(self, qualificador_id: int) -> Qualificador | None:
        """Get qualificador by ID."""
        return self.session.get(Qualificador, qualificador_id)

    def get_by_ids(self, ids: list[int]) -> list[Qualificador]:
        """Get qualificadores by list of IDs."""
        return (
            self.session.query(Qualificador)
            .filter(Qualificador.seq_qualificador.in_(ids))
            .all()
        )

    def get_by_name(self, name: str) -> Qualificador | None:
        """Get qualificador by name (case-insensitive)."""
        return (
            self.session.query(Qualificador)
            .filter(func.lower(Qualificador.dsc_qualificador) == name.lower())
            .first()
        )

    def get_receita(self) -> list[Qualificador]:
        """Get receita qualificadores (num starts with '1')."""
        return (
            self.session.query(Qualificador)
            .filter(
                Qualificador.num_qualificador.startswith('1'),
                Qualificador.ind_status == 'A',
            )
            .order_by(Qualificador.num_qualificador)
            .all()
        )

    def get_despesa(self) -> list[Qualificador]:
        """Get despesa qualificadores (num starts with '2')."""
        return (
            self.session.query(Qualificador)
            .filter(
                Qualificador.num_qualificador.startswith('2'),
                Qualificador.ind_status == 'A',
            )
            .order_by(Qualificador.num_qualificador)
            .all()
        )

    def get_receita_folha(self) -> list[Qualificador]:
        """Get receita qualificadores that have no children (leaf nodes)."""
        todos = (
            self.session.query(Qualificador)
            .filter(
                Qualificador.num_qualificador.startswith('1'),
                Qualificador.ind_status == 'A',
            )
            .order_by(Qualificador.num_qualificador)
            .all()
        )
        ids_pais = set(q.cod_qualificador_pai for q in todos if q.cod_qualificador_pai)
        return [q for q in todos if q.seq_qualificador not in ids_pais]

    def get_despesa_folha(self) -> list[Qualificador]:
        """Get despesa qualificadores that have no children (leaf nodes)."""
        todos = (
            self.session.query(Qualificador)
            .filter(
                Qualificador.num_qualificador.startswith('2'),
                Qualificador.ind_status == 'A',
            )
            .order_by(Qualificador.num_qualificador)
            .all()
        )
        ids_pais = set(q.cod_qualificador_pai for q in todos if q.cod_qualificador_pai)
        return [q for q in todos if q.seq_qualificador not in ids_pais]

    def create(self, qualificador: Qualificador) -> Qualificador:
        """Create a new qualificador."""
        self.session.add(qualificador)
        self.session.commit()
        return qualificador

    def update(self, qualificador: Qualificador) -> Qualificador:
        """Update an existing qualificador."""
        self.session.commit()
        return qualificador

    def delete_logical(self, qualificador_id: int) -> Qualificador | None:
        """Logically delete a qualificador by setting ind_status to 'I'."""
        qualificador = self.get_by_id(qualificador_id)
        if qualificador:
            qualificador.ind_status = 'I'
            self.session.commit()
        return qualificador

    def count(self) -> int:
        """Count all qualificadores."""
        return self.session.query(Qualificador).count()

    def get_limit(self, limit: int) -> list[Qualificador]:
        """Get qualificadores with a limit."""
        return self.session.query(Qualificador).limit(limit).all()
