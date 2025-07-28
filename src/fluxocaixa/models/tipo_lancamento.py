from sqlalchemy import Column, Integer, String

from .base import Base

class TipoLancamento(Base):
    __tablename__ = 'flc_tipo_lancamento'
    cod_tipo_lancamento = Column(Integer, primary_key=True)
    dsc_tipo_lancamento = Column(String(50), nullable=False)
