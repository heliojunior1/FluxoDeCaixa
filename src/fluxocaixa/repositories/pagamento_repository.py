from sqlalchemy.orm import Session

from ..models import Pagamento, Orgao
from ..models.base import db
from ..domain import PagamentoCreate


class PagamentoRepository:
    """Data access layer for Pagamento records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def list_pagamentos(self):
        return (
            self.session.query(Pagamento)
            .order_by(Pagamento.dat_pagamento.desc())
            .all()
        )

    def list_orgaos(self):
        return self.session.query(Orgao).all()

    def create(self, data: PagamentoCreate) -> Pagamento:
        pag = Pagamento(
            dat_pagamento=data.dat_pagamento,
            cod_orgao=data.cod_orgao,
            val_pagamento=data.val_pagamento,
            dsc_pagamento=data.dsc_pagamento,
        )
        self.session.add(pag)
        self.session.commit()
        return pag
