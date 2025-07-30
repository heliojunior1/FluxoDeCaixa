from datetime import date
from sqlalchemy.orm import Session

from ..models import Alerta, Qualificador
from ..models.base import db
from ..domain import AlertaCreate, AlertaUpdate


class AlertaRepository:
    """Data access layer for Alerta records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def list(self):
        return self.session.query(Alerta).order_by(Alerta.nom_alerta).all()

    def list_qualificadores(self):
        return (
            self.session.query(Qualificador)
            .filter_by(ind_status='A')
            .order_by(Qualificador.dsc_qualificador)
            .all()
        )

    def create(self, data: AlertaCreate) -> Alerta:
        alerta = Alerta(
            nom_alerta=data.nom_alerta,
            metric=data.metric,
            seq_qualificador=data.seq_qualificador,
            logic=data.logic,
            valor=data.valor,
            period=data.period,
            notif_system=data.notif_system,
            notif_email=data.notif_email,
            cod_pessoa_inclusao=1,
        )
        self.session.add(alerta)
        self.session.commit()
        return alerta

    def get(self, ident: int) -> Alerta:
        return self.session.query(Alerta).get_or_404(ident)

    def update(self, ident: int, data: AlertaUpdate) -> Alerta:
        alerta = self.get(ident)
        alerta.nom_alerta = data.nom_alerta
        alerta.metric = data.metric
        alerta.seq_qualificador = data.seq_qualificador
        alerta.logic = data.logic
        alerta.valor = data.valor
        alerta.period = data.period
        alerta.notif_system = data.notif_system
        alerta.notif_email = data.notif_email
        alerta.dat_alteracao = data.dat_alteracao or date.today()
        alerta.cod_pessoa_alteracao = 1
        self.session.commit()
        return alerta

    def soft_delete(self, ident: int) -> None:
        alerta = self.get(ident)
        alerta.ind_status = 'I'
        alerta.dat_alteracao = date.today()
        alerta.cod_pessoa_alteracao = 1
        self.session.commit()
