from sqlalchemy.orm import Session

from ..models import Lancamento
from ..models.base import db
from ..domain import LancamentoCreate


class LancamentoRepository:
    """Data access layer for Lancamento records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def list(self):
        return (
            self.session.query(Lancamento)
            .filter_by(ind_status='A')
            .order_by(Lancamento.dat_lancamento.desc())
            .all()
        )

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
