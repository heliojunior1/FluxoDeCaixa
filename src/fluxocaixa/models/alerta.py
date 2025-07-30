from datetime import date
from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base

class Alerta(Base):
    __tablename__ = 'flc_alerta'
    seq_alerta = Column(Integer, primary_key=True)
    nom_alerta = Column(String(255), nullable=False)
    metric = Column(String(20), nullable=False)
    seq_qualificador = Column(Integer, ForeignKey('flc_qualificador.seq_qualificador'))
    logic = Column(String(20), nullable=False)
    valor = Column(Numeric(18, 2))
    period = Column(String(20))
    emails = Column(String(255))
    notif_system = Column(String(1), default='S')
    notif_email = Column(String(1), default='N')
    ind_status = Column(String(1), default='A', nullable=False)
    dat_inclusao = Column(Date, default=date.today, nullable=False)

    qualificador = relationship('Qualificador')

