from datetime import date
from sqlalchemy import Column, Integer, Date, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import Base


class SaldoConta(Base):
    """Model for daily bank account balances."""
    __tablename__ = 'flc_saldo_conta'
    
    seq_saldo_conta = Column(Integer, primary_key=True)
    seq_conta = Column(Integer, ForeignKey('flc_conta_bancaria.seq_conta'), nullable=False)
    dat_saldo = Column(Date, nullable=False)
    val_saldo = Column(Numeric(18, 2), nullable=False)
    dat_inclusao = Column(Date, default=date.today, nullable=False)
    cod_pessoa_inclusao = Column(Integer, nullable=False)
    dat_alteracao = Column(Date)
    cod_pessoa_alteracao = Column(Integer)
    
    # Relationship to ContaBancaria
    conta = relationship('ContaBancaria', backref='saldos')
    
    # Unique constraint: one balance per account per date
    __table_args__ = (
        UniqueConstraint('seq_conta', 'dat_saldo', name='uk_saldo_conta_data'),
    )
    
    def __repr__(self):
        return f"<SaldoConta(seq_conta={self.seq_conta}, dat_saldo={self.dat_saldo}, val_saldo={self.val_saldo})>"
