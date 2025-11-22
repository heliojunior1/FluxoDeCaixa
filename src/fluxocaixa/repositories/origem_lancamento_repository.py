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
    
    def list_active(self):
        """Get only active origem lancamento records."""
        return self.session.query(OrigemLancamento).filter_by(ind_status='A').all()
    
    def get_by_description(self, description: str) -> OrigemLancamento | None:
        """
        Find origem by description (case-insensitive).
        
        Args:
            description: The description to search for (e.g., 'Manual', 'Automático', 'Importado')
            
        Returns:
            OrigemLancamento record if found, None otherwise
        """
        return self.session.query(OrigemLancamento).filter(
            OrigemLancamento.dsc_origem_lancamento.ilike(description)
        ).first()
