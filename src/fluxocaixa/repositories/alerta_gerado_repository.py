from datetime import date, datetime
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import AlertaGerado
from ..models.base import db
from ..domain import AlertaGeradoCreate, AlertaGeradoUpdate


class AlertaGeradoRepository:
    """Data access layer for AlertaGerado records."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def list_all(self):
        """Lista todos os alertas gerados ordenados por data de processamento (mais recentes primeiro)."""
        return (
            self.session.query(AlertaGerado)
            .order_by(AlertaGerado.dat_processamento.desc())
            .all()
        )

    def list_active(self):
        """Lista alertas ativos (do dia atual OU sem data de processamento) e não lidos.
        
        Regra especial: Alertas com dat_processamento=NULL aparecem sempre.
        """
        hoje = date.today()
        return (
            self.session.query(AlertaGerado)
            .filter(AlertaGerado.ind_lido == 'N')
            .filter(
                or_(
                    AlertaGerado.dat_processamento == None,  # Alertas de demonstração
                    AlertaGerado.dat_processamento == hoje   # Alertas do dia
                )
            )
            .order_by(
                AlertaGerado.severidade.desc(),  # CRITICAL, WARNING, INFO
                AlertaGerado.seq_alerta_gerado
            )
            .all()
        )

    def list_by_date(self, data: date):
        """Lista alertas gerados em uma data específica."""
        return (
            self.session.query(AlertaGerado)
            .filter_by(dat_processamento=data)
            .order_by(AlertaGerado.severidade.desc(), AlertaGerado.seq_alerta_gerado)
            .all()
        )

    def list_unread(self):
        """Lista alertas não lidos."""
        return (
            self.session.query(AlertaGerado)
            .filter_by(ind_lido='N')
            .order_by(AlertaGerado.dat_processamento.desc())
            .all()
        )

    def get_unread_count(self) -> int:
        """Retorna a quantidade de alertas não lidos."""
        return self.session.query(AlertaGerado).filter_by(ind_lido='N').count()

    def create(self, data: AlertaGeradoCreate) -> AlertaGerado:
        """Cria um novo alerta gerado."""
        alerta = AlertaGerado(
            seq_alerta=data.seq_alerta,
            dat_processamento=data.dat_processamento,
            dat_referencia=data.dat_referencia,
            valor_obtido=data.valor_obtido,
            valor_esperado=data.valor_esperado,
            mensagem=data.mensagem,
            categoria=data.categoria,
            severidade=data.severidade,
        )
        self.session.add(alerta)
        self.session.commit()
        return alerta

    def get(self, ident: int) -> AlertaGerado:
        """Busca um alerta gerado por ID."""
        return self.session.query(AlertaGerado).get_or_404(ident)

    def mark_as_read(self, ident: int) -> AlertaGerado:
        """Marca um alerta como lido."""
        alerta = self.get(ident)
        alerta.ind_lido = 'S'
        alerta.dat_leitura = datetime.now()
        self.session.commit()
        return alerta

    def mark_as_resolved(self, ident: int) -> AlertaGerado:
        """Marca um alerta como resolvido."""
        alerta = self.get(ident)
        alerta.ind_resolvido = 'S'
        alerta.dat_resolucao = datetime.now()
        self.session.commit()
        return alerta

    def update(self, ident: int, data: AlertaGeradoUpdate) -> AlertaGerado:
        """Atualiza um alerta gerado."""
        alerta = self.get(ident)
        
        if data.ind_lido is not None:
            alerta.ind_lido = data.ind_lido
            if data.ind_lido == 'S' and not alerta.dat_leitura:
                alerta.dat_leitura = datetime.now()
        
        if data.ind_resolvido is not None:
            alerta.ind_resolvido = data.ind_resolvido
            if data.ind_resolvido == 'S' and not alerta.dat_resolucao:
                alerta.dat_resolucao = datetime.now()
        
        self.session.commit()
        return alerta
