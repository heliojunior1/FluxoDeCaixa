"""Modelos para o sistema de fórmulas parametrizáveis de projeção."""

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


class RubricaFormula(Base):
    """Fórmula de projeção parametrizável por qualificador.

    Cada qualificador (rubrica) pode ter uma fórmula associada que será usada
    para calcular projeções quando o cenário for do tipo FORMULA.

    Exemplo de expressão: base * (1 + ipca) * (1 + pib * elasticidade)

    A variável especial 'base' é calculada a partir de dados históricos,
    usando o método configurado em cod_metodo_base.
    """

    __tablename__ = 'flc_rubrica_formula'

    seq_rubrica_formula = Column(Integer, primary_key=True)
    seq_qualificador = Column(
        Integer,
        ForeignKey('flc_qualificador.seq_qualificador'),
        nullable=False,
        unique=True,
    )
    nom_formula = Column(String(100), nullable=False)
    dsc_formula_expressao = Column(Text, nullable=False)
    # 'MEDIA_SIMPLES', 'MEDIA_PONDERADA', 'VALOR_FIXO'
    cod_metodo_base = Column(String(20), nullable=False, default='MEDIA_SIMPLES')
    # JSON com anos selecionados e pesos. Exemplos:
    # MEDIA_SIMPLES:   {"anos": [2023, 2024]}
    # MEDIA_PONDERADA: {"anos": [2022,2023,2024], "pesos": {"2022":1,"2023":2,"2024":3}}
    # VALOR_FIXO:      {"valor": 150000.00}
    json_config_base = Column(Text)
    ind_status = Column(String(1), default='A', nullable=False)
    dat_inclusao = Column(Date, default=date.today, nullable=False)

    qualificador = relationship('Qualificador')


class ParametroGlobal(Base):
    """Parâmetros macroeconômicos globais (IPCA, PIB, Selic, etc.).

    São variáveis que podem ser usadas em qualquer fórmula de rubrica.
    O nome do parâmetro deve coincidir com o nome da variável na expressão.
    Ex: se a fórmula é 'base * (1 + ipca)', deve existir um ParametroGlobal
    com nom_parametro = 'ipca'.
    """

    __tablename__ = 'flc_parametro_global'

    seq_parametro_global = Column(Integer, primary_key=True)
    nom_parametro = Column(String(50), nullable=False, unique=True)
    dsc_parametro = Column(String(255))
    # 'P' percentual (ex: 0.045 = 4.5%), 'V' valor absoluto
    cod_tipo = Column(String(1), default='P', nullable=False)
    ind_status = Column(String(1), default='A', nullable=False)
    dat_inclusao = Column(Date, default=date.today, nullable=False)


class CenarioParametroValor(Base):
    """Valor de um parâmetro para um cenário específico.

    Quando o usuário cria um cenário do tipo FORMULA, ele preenche os valores
    de cada parâmetro (global ou específico). Esta tabela armazena esses valores.
    """

    __tablename__ = 'flc_cenario_parametro_valor'
    __table_args__ = (
        UniqueConstraint(
            'seq_simulador_cenario',
            'nom_parametro',
            name='uix_cenario_param_nome',
        ),
    )

    seq_cenario_parametro_valor = Column(Integer, primary_key=True)
    seq_simulador_cenario = Column(
        Integer,
        ForeignKey('flc_simulador_cenario.seq_simulador_cenario'),
        nullable=False,
    )
    # Nome da variável na fórmula (pode ser global ou específico da rubrica)
    nom_parametro = Column(String(50), nullable=False)
    val_parametro = Column(Numeric(18, 6), nullable=False)
    dat_inclusao = Column(Date, default=date.today, nullable=False)

    simulador_cenario = relationship(
        'SimuladorCenario',
        backref=backref('parametros_cenario', cascade='all, delete-orphan'),
    )
