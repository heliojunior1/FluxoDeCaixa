from datetime import date
from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, inspect, text
from sqlalchemy.orm import relationship

from .base import Base, engine

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
    cod_pessoa_inclusao = Column(Integer, nullable=False)
    dat_alteracao = Column(Date)
    cod_pessoa_alteracao = Column(Integer)

    qualificador = relationship('Qualificador')


def ensure_alerta_schema():
    """Add missing columns to flc_alerta table if needed."""
    inspector = inspect(engine)
    if 'flc_alerta' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('flc_alerta')}
    with engine.connect() as conn:
        if 'cod_pessoa_inclusao' not in columns:
            conn.execute(text('ALTER TABLE flc_alerta ADD COLUMN cod_pessoa_inclusao INTEGER'))
        if 'dat_alteracao' not in columns:
            conn.execute(text('ALTER TABLE flc_alerta ADD COLUMN dat_alteracao DATE'))
        if 'cod_pessoa_alteracao' not in columns:
            conn.execute(text('ALTER TABLE flc_alerta ADD COLUMN cod_pessoa_alteracao INTEGER'))
        conn.commit()

