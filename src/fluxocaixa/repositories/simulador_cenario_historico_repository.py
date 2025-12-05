"""Repository para histórico de cenários do simulador."""
from __future__ import annotations

from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session

from ..models import SimuladorCenarioHistorico
from ..models.base import db


class SimuladorCenarioHistoricoRepository:
    """Repository para operações com histórico de cenários."""
    
    def __init__(self, session: Session | None = None):
        self.session = session or db.session
    
    def create_snapshot(self, snapshot: SimuladorCenarioHistorico) -> SimuladorCenarioHistorico:
        """Cria um novo snapshot de cenário."""
        self.session.add(snapshot)
        self.session.commit()
        return snapshot
    
    def get_snapshots_by_cenario(
        self, 
        seq_simulador_cenario: int
    ) -> List[SimuladorCenarioHistorico]:
        """Retorna todos os snapshots de um cenário, ordenados por data."""
        return (
            self.session.query(SimuladorCenarioHistorico)
            .filter_by(seq_simulador_cenario=seq_simulador_cenario)
            .order_by(SimuladorCenarioHistorico.dat_snapshot.asc())
            .all()
        )
    
    def get_primeiro_snapshot(
        self, 
        seq_simulador_cenario: int,
        ano: Optional[int] = None
    ) -> Optional[SimuladorCenarioHistorico]:
        """Retorna o primeiro snapshot de um cenário."""
        query = (
            self.session.query(SimuladorCenarioHistorico)
            .filter_by(seq_simulador_cenario=seq_simulador_cenario)
        )
        
        if ano:
            data_inicio = date(ano, 1, 1)
            data_fim = date(ano, 12, 31)
            query = query.filter(
                SimuladorCenarioHistorico.dat_snapshot >= data_inicio,
                SimuladorCenarioHistorico.dat_snapshot <= data_fim
            )
        
        return query.order_by(SimuladorCenarioHistorico.dat_snapshot.asc()).first()
    
    def get_ultimo_snapshot(
        self, 
        seq_simulador_cenario: int,
        ano: Optional[int] = None
    ) -> Optional[SimuladorCenarioHistorico]:
        """Retorna o último snapshot de um cenário."""
        query = (
            self.session.query(SimuladorCenarioHistorico)
            .filter_by(seq_simulador_cenario=seq_simulador_cenario)
        )
        
        if ano:
            data_inicio = date(ano, 1, 1)
            data_fim = date(ano, 12, 31)
            query = query.filter(
                SimuladorCenarioHistorico.dat_snapshot >= data_inicio,
                SimuladorCenarioHistorico.dat_snapshot <= data_fim
            )
        
        return query.order_by(SimuladorCenarioHistorico.dat_snapshot.desc()).first()
    
    def get_snapshot_by_id(self, seq_historico: int) -> Optional[SimuladorCenarioHistorico]:
        """Retorna um snapshot específico por ID."""
        return self.session.query(SimuladorCenarioHistorico).get(seq_historico)
    
    def delete_snapshots_by_cenario(self, seq_simulador_cenario: int) -> int:
        """Deleta todos os snapshots de um cenário. Retorna quantidade deletada."""
        count = (
            self.session.query(SimuladorCenarioHistorico)
            .filter_by(seq_simulador_cenario=seq_simulador_cenario)
            .delete()
        )
        self.session.commit()
        return count
