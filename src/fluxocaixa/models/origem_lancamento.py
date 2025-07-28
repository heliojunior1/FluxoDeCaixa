from sqlalchemy import Column, Integer, String

from .base import Base

class OrigemLancamento(Base):
    __tablename__ = 'flc_origem_lancamento'
    cod_origem_lancamento = Column(Integer, primary_key=True)
    dsc_origem_lancamento = Column(String(50), nullable=False)
