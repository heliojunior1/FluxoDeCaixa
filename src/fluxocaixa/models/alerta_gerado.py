from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship

from .base import Base


class AlertaGerado(Base):
    """Representa um alerta gerado pelo sistema.
    
    Alertas podem ser criados automaticamente por processamento de regras
    ou manualmente para fins de demonstração.
    
    Regra Especial: Alertas com dat_processamento = NULL aparecem sempre
    na tela, independente do dia, facilitando demonstrações.
    """
    
    __tablename__ = 'flc_alerta_gerado'
    
    seq_alerta_gerado = Column(Integer, primary_key=True)
    seq_alerta = Column(Integer, ForeignKey('flc_alerta.seq_alerta'), nullable=True)
    dat_processamento = Column(Date, nullable=True)  # NULL = alerta de demonstração (sempre visível)
    dat_referencia = Column(Date, nullable=False)
    valor_obtido = Column(Numeric(18, 2))
    valor_esperado = Column(Numeric(18, 2))
    mensagem = Column(Text, nullable=False)
    categoria = Column(String(50), nullable=False)  # RECEITA, DESPESA_PESSOAL, SALDO, etc
    severidade = Column(String(20), default='INFO')  # INFO, WARNING, CRITICAL
    ind_lido = Column(String(1), default='N', nullable=False)
    ind_resolvido = Column(String(1), default='N', nullable=False)
    dat_leitura = Column(DateTime)
    dat_resolucao = Column(DateTime)
    
    # Relacionamento com a regra de alerta (opcional, pois pode ser um alerta manual)
    alerta = relationship('Alerta', foreign_keys=[seq_alerta])
    
    def __repr__(self):
        return f'<AlertaGerado {self.seq_alerta_gerado}: {self.categoria} - {self.mensagem[:50]}>'
