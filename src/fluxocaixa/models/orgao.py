from sqlalchemy import Column, Integer, String

from .base import Base

class Orgao(Base):
    __tablename__ = 'flc_orgao'
    cod_orgao = Column(Integer, primary_key=True)
    nom_orgao = Column(String(100), nullable=False)
