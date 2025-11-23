from datetime import date
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Numeric,
    ForeignKey,
    UniqueConstraint,
    Text,
)
from sqlalchemy.orm import relationship, backref

from .base import Base


class SimuladorCenario(Base):
    """Cenário principal do simulador que combina receita e despesa."""
    
    __tablename__ = 'flc_simulador_cenario'
    
    seq_simulador_cenario = Column(Integer, primary_key=True)
    nom_cenario = Column(String(100), nullable=False)
    dsc_cenario = Column(String(255))
    ano_base = Column(Integer, nullable=False)
    meses_projecao = Column(Integer, nullable=False, default=12)
    dat_criacao = Column(Date, default=date.today, nullable=False)
    ind_status = Column(String(1), default='A', nullable=False)  # 'A' Ativo, 'I' Inativo
    dat_inclusao = Column(Date, default=date.today, nullable=False)
    cod_pessoa_inclusao = Column(Integer, nullable=False, default=1)
    dat_alteracao = Column(Date)
    cod_pessoa_alteracao = Column(Integer)


class CenarioReceita(Base):
    """Configuração de cenário de receita."""
    
    __tablename__ = 'flc_cenario_receita'
    
    seq_cenario_receita = Column(Integer, primary_key=True)
    seq_simulador_cenario = Column(
        Integer,
        ForeignKey('flc_simulador_cenario.seq_simulador_cenario'),
        nullable=False,
        unique=True,
    )
    # Tipos: 'MANUAL', 'HOLT_WINTERS', 'ARIMA', 'SARIMA', 'REGRESSAO'
    cod_tipo_cenario = Column(String(20), nullable=False)
    # JSON com configurações específicas de cada modelo
    # Ex: {"alpha": 0.5, "beta": 0.3} para Holt-Winters
    # Ex: {"p": 1, "d": 1, "q": 1} para ARIMA
    json_configuracao = Column(Text)
    dat_inclusao = Column(Date, default=date.today, nullable=False)
    
    simulador_cenario = relationship(
        'SimuladorCenario',
        backref=backref('cenario_receita', uselist=False, cascade="all, delete-orphan")
    )


class CenarioReceitaAjuste(Base):
    """Ajustes mensais para cenário manual de receita."""
    
    __tablename__ = 'flc_cenario_receita_ajuste'
    __table_args__ = (
        UniqueConstraint(
            'seq_cenario_receita',
            'seq_qualificador',
            'ano',
            'mes',
            name='uix_cenario_receita_ajuste'
        ),
    )
    
    seq_cenario_receita_ajuste = Column(Integer, primary_key=True)
    seq_cenario_receita = Column(
        Integer,
        ForeignKey('flc_cenario_receita.seq_cenario_receita'),
        nullable=False,
    )
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
    
    cenario_receita = relationship(
        'CenarioReceita',
        backref=backref('ajustes', cascade="all, delete-orphan")
    )
    qualificador = relationship('Qualificador')


class CenarioDespesa(Base):
    """Configuração de cenário de despesa."""
    
    __tablename__ = 'flc_cenario_despesa'
    
    seq_cenario_despesa = Column(Integer, primary_key=True)
    seq_simulador_cenario = Column(
        Integer,
        ForeignKey('flc_simulador_cenario.seq_simulador_cenario'),
        nullable=False,
        unique=True,
    )
    # Tipos: 'MANUAL', 'LOA', 'MEDIA_HISTORICA'
    cod_tipo_cenario = Column(String(20), nullable=False)
    # JSON com configurações específicas
    # Ex: {"periodo_meses": 12, "fator_ajuste": 1.05} para Média Histórica
    # Ex: {"ano_loa": 2025} para LOA
    json_configuracao = Column(Text)
    dat_inclusao = Column(Date, default=date.today, nullable=False)
    
    simulador_cenario = relationship(
        'SimuladorCenario',
        backref=backref('cenario_despesa', uselist=False, cascade="all, delete-orphan")
    )


class CenarioDespesaAjuste(Base):
    """Ajustes mensais para cenário manual de despesa."""
    
    __tablename__ = 'flc_cenario_despesa_ajuste'
    __table_args__ = (
        UniqueConstraint(
            'seq_cenario_despesa',
            'seq_qualificador',
            'ano',
            'mes',
            name='uix_cenario_despesa_ajuste'
        ),
    )
    
    seq_cenario_despesa_ajuste = Column(Integer, primary_key=True)
    seq_cenario_despesa = Column(
        Integer,
        ForeignKey('flc_cenario_despesa.seq_cenario_despesa'),
        nullable=False,
    )
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
    
    cenario_despesa = relationship(
        'CenarioDespesa',
        backref=backref('ajustes', cascade="all, delete-orphan")
    )
    qualificador = relationship('Qualificador')


class ModeloEconomicoParametro(Base):
    """Parâmetros para modelos de regressão linear múltipla."""
    
    __tablename__ = 'flc_modelo_economico_parametro'
    
    seq_parametro = Column(Integer, primary_key=True)
    seq_cenario_receita = Column(
        Integer,
        ForeignKey('flc_cenario_receita.seq_cenario_receita'),
        nullable=False,
    )
    nom_variavel = Column(String(50), nullable=False)  # Ex: "PIB", "Inflacao", "Selic"
    val_coeficiente = Column(Numeric(18, 6), nullable=False)  # Valor do β para a variável
    # JSON com série temporal da variável: [{"mes": 1, "ano": 2025, "valor": 1.5}, ...]
    json_valores_historicos = Column(Text)
    dat_inclusao = Column(Date, default=date.today, nullable=False)
    
    cenario_receita = relationship(
        'CenarioReceita',
        backref=backref('parametros_economicos', cascade="all, delete-orphan")
    )
