"""Modelo para histórico de cenários do simulador."""
from datetime import date
from sqlalchemy import Column, Integer, Date, Text, ForeignKey

from .base import Base


class SimuladorCenarioHistorico(Base):
    """Armazena snapshots históricos de cenários do simulador."""
    
    __tablename__ = 'flc_simulador_cenario_historico'
    
    seq_historico = Column(Integer, primary_key=True)
    seq_simulador_cenario = Column(
        Integer, 
        ForeignKey('flc_simulador_cenario.seq_simulador_cenario'),
        nullable=False
    )
    dat_snapshot = Column(Date, nullable=False, default=date.today)
    cod_pessoa_snapshot = Column(Integer, nullable=False)
    json_snapshot = Column(Text, nullable=False)  # JSON completo do cenário
