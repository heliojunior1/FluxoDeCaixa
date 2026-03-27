from datetime import date
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Numeric,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from .base import Base


class Loa(Base):
    """Lei Orçamentária Anual – previsão de receita/despesa por qualificador e ano."""
    __tablename__ = 'flc_loa'

    seq_loa = Column(Integer, primary_key=True)
    num_ano = Column(Integer, nullable=False)
    seq_qualificador = Column(Integer, ForeignKey('flc_qualificador.seq_qualificador'), nullable=False)
    val_loa = Column(Numeric(18, 2), nullable=False)
    dat_inclusao = Column(Date, default=date.today, nullable=False)
    ind_status = Column(String(1), default='A', nullable=False)

    qualificador = relationship('Qualificador')
