from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import ContaBancaria
from ..models.base import db


class ContaBancariaRepository:
    """Data access layer for ContaBancaria records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def list_all(self):
        """Get all conta bancaria records."""
        return self.session.query(ContaBancaria).all()

    def list_active(self):
        """Get only active conta bancaria records."""
        return self.session.query(ContaBancaria).filter_by(ind_status='A').all()
