from datetime import date
from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base

class Pagamento(Base):
    __tablename__ = 'flc_pagamento'
    seq_pagamento = Column(Integer, primary_key=True)
    dat_pagamento = Column(Date, nullable=False)
    cod_orgao = Column(Integer, ForeignKey('flc_orgao.cod_orgao'), nullable=False)
    val_pagamento = Column(Numeric(18,2), nullable=False)
    dsc_pagamento = Column(String(255))
    dat_inclusao = Column(Date, default=date.today, nullable=False)

    orgao = relationship('Orgao')
