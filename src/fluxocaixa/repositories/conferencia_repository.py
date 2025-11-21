from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Conferencia
from ..models.base import db


class ConferenciaRepository:
    """Data access layer for Conferencia records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def list_all(self):
        """Get all conferencia records ordered by date descending."""
        return self.session.query(Conferencia).order_by(
            Conferencia.dat_conferencia.desc()
        ).all()
