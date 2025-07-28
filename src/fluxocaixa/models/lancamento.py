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
from .tipo_lancamento import TipoLancamento
from .origem_lancamento import OrigemLancamento
from .qualificador import Qualificador

class Lancamento(Base):
    __tablename__ = 'flc_lancamento'
    seq_lancamento = Column(Integer, primary_key=True)
    dat_lancamento = Column(Date, nullable=False)
    seq_qualificador = Column(Integer, ForeignKey('flc_qualificador.seq_qualificador'), nullable=False)
    val_lancamento = Column(Numeric(18,2), nullable=False)
    cod_tipo_lancamento = Column(Integer, ForeignKey('flc_tipo_lancamento.cod_tipo_lancamento'), nullable=False)
    cod_origem_lancamento = Column(Integer, ForeignKey('flc_origem_lancamento.cod_origem_lancamento'), nullable=False)
    ind_origem = Column(String(1), nullable=False)
    dat_inclusao = Column(Date, default=date.today, nullable=False)
    cod_pessoa_inclusao = Column(Integer, nullable=False)
    dat_alteracao = Column(Date)
    cod_pessoa_alteracao = Column(Integer)
    ind_status = Column(String(1), default='A', nullable=False)

    tipo = relationship('TipoLancamento')
    origem = relationship('OrigemLancamento')
    qualificador = relationship('Qualificador')
