from datetime import date
from sqlalchemy import Column, Integer, String, Date

from .base import Base


class ContaBancaria(Base):
    __tablename__ = "flc_conta_bancaria"

    seq_conta = Column(Integer, primary_key=True)
    cod_banco = Column(String(10), nullable=False)
    num_agencia = Column(String(20), nullable=False)
    num_conta = Column(String(30), nullable=False)
    dsc_conta = Column(String(100))
    ind_status = Column(String(1), default="A", nullable=False)
    dat_cadastro = Column(Date, default=date.today)

    def display(self) -> str:
        desc = f" - {self.dsc_conta}" if self.dsc_conta else ""
        return f"{self.cod_banco} / {self.num_agencia} / {self.num_conta}{desc}"
