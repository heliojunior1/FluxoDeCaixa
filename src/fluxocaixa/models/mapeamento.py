from datetime import date
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base
from .qualificador import Qualificador

class Mapeamento(Base):
    __tablename__ = 'flc_mapeamento'
    seq_mapeamento = Column(Integer, primary_key=True)
    seq_qualificador = Column(Integer, ForeignKey('flc_qualificador.seq_qualificador'), nullable=False)
    dsc_mapeamento = Column(String(255), nullable=False)
    txt_condicao = Column(String(500))
    ind_status = Column(String(1), default='A', nullable=False)
    dat_inclusao = Column(Date, default=date.today, nullable=False)

    qualificador = relationship('Qualificador')
