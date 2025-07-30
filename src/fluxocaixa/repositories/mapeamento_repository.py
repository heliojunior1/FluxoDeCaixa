from sqlalchemy.orm import Session

from ..models import Mapeamento, Qualificador
from ..models.base import db
from ..domain import MapeamentoCreate


class MapeamentoRepository:
    """Data access layer for Mapeamento records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def list(self):
        return self.session.query(Mapeamento).order_by(Mapeamento.dat_inclusao.desc()).all()

    def list_qualificadores(self):
        return (
            self.session.query(Qualificador)
            .filter_by(ind_status='A')
            .order_by(Qualificador.num_qualificador)
            .all()
        )

    def create(self, data: MapeamentoCreate) -> Mapeamento:
        mapeamento = Mapeamento(
            seq_qualificador=data.seq_qualificador,
            dsc_mapeamento=data.dsc_mapeamento,
            txt_condicao=data.txt_condicao,
            ind_status=data.ind_status,
        )
        self.session.add(mapeamento)
        self.session.commit()
        return mapeamento

    def get(self, ident: int) -> Mapeamento:
        return self.session.query(Mapeamento).get_or_404(ident)

    def update(self, ident: int, data: MapeamentoCreate) -> Mapeamento:
        mapeamento = self.get(ident)
        mapeamento.seq_qualificador = data.seq_qualificador
        mapeamento.dsc_mapeamento = data.dsc_mapeamento
        mapeamento.txt_condicao = data.txt_condicao
        self.session.commit()
        return mapeamento

    def soft_delete(self, ident: int) -> None:
        mapeamento = self.get(ident)
        mapeamento.ind_status = 'I'
        self.session.commit()
