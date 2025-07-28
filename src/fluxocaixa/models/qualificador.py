from datetime import date
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base

class Qualificador(Base):
    __tablename__ = 'flc_qualificador'
    seq_qualificador = Column(Integer, primary_key=True)
    num_qualificador = Column(String(20), nullable=False, unique=True)
    dsc_qualificador = Column(String(255), nullable=False)
    cod_qualificador_pai = Column(Integer, ForeignKey('flc_qualificador.seq_qualificador'))
    dat_inclusao = Column(Date, default=date.today, nullable=False)
    ind_status = Column(String(1), default='A', nullable=False)

    pai = relationship('Qualificador', remote_side=[seq_qualificador], backref='filhos')

    @property
    def get_root(self):
        node = self
        while node.pai:
            node = node.pai
        return node

    @property
    def tipo_fluxo(self):
        root_num = self.get_root.num_qualificador
        if root_num.startswith('1'):
            return 'receita'
        elif root_num.startswith('2'):
            return 'despesa'
        return 'indefinido'

    @property
    def nivel(self):
        if self.cod_qualificador_pai is None:
            return 0
        return self.pai.nivel + 1

    @property
    def path_completo(self):
        if self.cod_qualificador_pai is None:
            return self.dsc_qualificador
        return f"{self.pai.path_completo} > {self.dsc_qualificador}"

    def get_todos_filhos(self):
        result = []
        for filho in self.filhos:
            if filho.ind_status == 'A':
                result.append(filho)
                result.extend(filho.get_todos_filhos())
        return result

    def is_folha(self):
        return len([f for f in self.filhos if f.ind_status == 'A']) == 0
