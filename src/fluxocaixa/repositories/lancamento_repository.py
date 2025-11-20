from datetime import date
from sqlalchemy.orm import Session

from ..models import Lancamento, Qualificador
from ..models.base import db
from ..domain import LancamentoCreate


class LancamentoRepository:
    """Data access layer for Lancamento records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session


    def list(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        descricao: str | None = None,
        tipo: int | None = None,
        qualificador_folha: int | None = None,
    ):
        query = self.session.query(Lancamento).filter_by(ind_status='A')

        if start_date and end_date:
            query = query.filter(Lancamento.dat_lancamento.between(start_date, end_date))

        if descricao:
            query = query.join(Qualificador).filter(Qualificador.dsc_qualificador.ilike(f"%{descricao}%"))

        if tipo:
            query = query.filter(Lancamento.cod_tipo_lancamento == tipo)

        if qualificador_folha:
            query = query.filter(Lancamento.seq_qualificador == qualificador_folha)

        return query.order_by(Lancamento.dat_lancamento.desc()).all()

    def create(self, data: LancamentoCreate) -> Lancamento:
        lanc = Lancamento(
            dat_lancamento=data.dat_lancamento,
            seq_qualificador=data.seq_qualificador,
            val_lancamento=data.val_lancamento,
            cod_tipo_lancamento=data.cod_tipo_lancamento,
            cod_origem_lancamento=data.cod_origem_lancamento,
            ind_origem='M',
            cod_pessoa_inclusao=1,
            seq_conta=data.seq_conta,
        )
        self.session.add(lanc)
        self.session.commit()
        return lanc

    def get(self, ident: int) -> Lancamento:
        return self.session.query(Lancamento).get_or_404(ident)

    def update(self, ident: int, data: LancamentoCreate) -> Lancamento:
        lanc = self.get(ident)
        lanc.dat_lancamento = data.dat_lancamento
        lanc.seq_qualificador = data.seq_qualificador
        lanc.val_lancamento = data.val_lancamento
        lanc.cod_tipo_lancamento = data.cod_tipo_lancamento
        lanc.cod_origem_lancamento = data.cod_origem_lancamento
        lanc.seq_conta = data.seq_conta
        self.session.commit()
        return lanc

    def soft_delete(self, ident: int) -> None:
        lanc = self.get(ident)
        lanc.ind_status = 'I'
        self.session.commit()
