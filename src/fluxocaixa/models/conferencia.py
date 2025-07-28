from sqlalchemy import Column, Date, Numeric

from .base import Base

class Conferencia(Base):
    __tablename__ = 'flc_conferencia'
    dat_conferencia = Column(Date, primary_key=True)
    val_saldo_anterior = Column(Numeric(18,2), nullable=False)
    val_liberacoes = Column(Numeric(18,2), nullable=False)
    val_conf_liberacoes = Column(Numeric(18,2), nullable=False)
    val_soma_anter_liberacoes = Column(Numeric(18,2), nullable=False)
    val_pagamentos = Column(Numeric(18,2), nullable=False)
    val_conf_pagamentos = Column(Numeric(18,2), nullable=False)
    val_saldo_final = Column(Numeric(18,2), nullable=False)
