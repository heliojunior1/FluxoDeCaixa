from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import TipoLancamento
from ..models.base import db


class TipoLancamentoRepository:
    """Data access layer for TipoLancamento records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def list_all(self):
        """Get all tipo lancamento records."""
        return self.session.query(TipoLancamento).all()

    def get_by_descricao(self, descricao: str):
        """Get tipo lancamento by description."""
        return self.session.query(TipoLancamento).filter_by(
            dsc_tipo_lancamento=descricao
        ).first()
