from datetime import date
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Numeric,
    ForeignKey,
    UniqueConstraint,
    inspect,
    text,
)
from sqlalchemy.orm import relationship, backref

from .base import Base, engine

class Cenario(Base):
    __tablename__ = 'flc_cenario'
    seq_cenario = Column(Integer, primary_key=True)
    nom_cenario = Column(String(100), nullable=False)
    dsc_cenario = Column(String(255))
    dat_criacao = Column(Date, default=date.today, nullable=False)
    ind_status = Column(String(1), default='A', nullable=False)
    dat_inclusao = Column(Date, default=date.today, nullable=False)
    cod_pessoa_inclusao = Column(Integer, nullable=False)
    dat_alteracao = Column(Date)
    cod_pessoa_alteracao = Column(Integer)

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


def ensure_cenario_schema():
    inspector = inspect(engine)
    if 'flc_cenario' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('flc_cenario')}
    with engine.connect() as conn:
        if 'cod_pessoa_inclusao' not in columns:
            conn.execute(text('ALTER TABLE flc_cenario ADD COLUMN cod_pessoa_inclusao INTEGER'))
        if 'dat_alteracao' not in columns:
            conn.execute(text('ALTER TABLE flc_cenario ADD COLUMN dat_alteracao DATE'))
        if 'cod_pessoa_alteracao' not in columns:
            conn.execute(text('ALTER TABLE flc_cenario ADD COLUMN cod_pessoa_alteracao INTEGER'))
        conn.commit()
