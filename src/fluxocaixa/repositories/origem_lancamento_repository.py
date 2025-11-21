from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import OrigemLancamento
from ..models.base import db


class OrigemLancamentoRepository:
    """Data access layer for OrigemLancamento records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def list_all(self):
        """Get all origem lancamento records."""
        return self.session.query(OrigemLancamento).all()
