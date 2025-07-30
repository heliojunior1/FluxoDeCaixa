from datetime import date
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Numeric,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, backref

from .base import Base

class Cenario(Base):
    __tablename__ = 'flc_cenario'
    seq_cenario = Column(Integer, primary_key=True)
    nom_cenario = Column(String(100), nullable=False)
    dsc_cenario = Column(String(255))
    dat_criacao = Column(Date, default=date.today, nullable=False)
    ind_status = Column(String(1), default='A', nullable=False)
    dat_inclusao = Column(Date, default=date.today, nullable=False)

class CenarioAjusteMensal(Base):
    __tablename__ = 'flc_cenario_ajuste_mensal'
    __table_args__ = (
        UniqueConstraint('seq_cenario', 'seq_qualificador', 'ano', 'mes', name='uix_cenario_ajuste_mes'),
    )

    seq_cenario_ajuste = Column(Integer, primary_key=True)
    seq_cenario = Column(Integer, ForeignKey('flc_cenario.seq_cenario'), nullable=False)
    seq_qualificador = Column(
        Integer,
        ForeignKey('flc_qualificador.seq_qualificador'),
        nullable=False,
    )
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    cod_tipo_ajuste = Column(String(1), nullable=False)  # 'P' percentual, 'V' valor fixo
    val_ajuste = Column(Numeric(18, 2), nullable=False)
    dsc_ajuste = Column(String(100))
    dat_inclusao = Column(Date, default=date.today, nullable=False)

    cenario = relationship(
        'Cenario', backref=backref('ajustes_mensais', cascade="all, delete-orphan")
    )
    qualificador = relationship('Qualificador')
