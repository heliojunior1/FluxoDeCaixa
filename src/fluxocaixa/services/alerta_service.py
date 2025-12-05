"""Service layer for Alerta operations."""
from __future__ import annotations

from ..domain import AlertaCreate, AlertaUpdate
from ..models import Alerta, AlertaGerado, Qualificador
from ..repositories import AlertaRepository, AlertaGeradoRepository


def list_alertas(repo: AlertaRepository | None = None) -> tuple[list[Alerta], list[Qualificador]]:
    """List all alertas and qualificadores."""
    repo = repo or AlertaRepository()
    return repo.list(), repo.list_qualificadores()


def create_alerta(data: AlertaCreate, repo: AlertaRepository | None = None) -> Alerta:
    """Create a new alerta."""
    repo = repo or AlertaRepository()
    return repo.create(data)


def update_alerta(ident: int, data: AlertaUpdate, repo: AlertaRepository | None = None) -> Alerta:
    """Update an existing alerta."""
    repo = repo or AlertaRepository()
    return repo.update(ident, data)


def delete_alerta(ident: int, repo: AlertaRepository | None = None) -> None:
    """Soft delete an alerta."""
    repo = repo or AlertaRepository()
    repo.soft_delete(ident)


def get_alerta_by_id(ident: int, repo: AlertaRepository | None = None) -> Alerta | None:
    """Get alerta by ID."""
    repo = repo or AlertaRepository()
    return repo.get(ident)


# Funções para alertas gerados
def list_alertas_ativos(repo: AlertaGeradoRepository | None = None) -> list[AlertaGerado]:
    """Lista alertas ativos (do dia + alertas sem data) não lidos."""
    repo = repo or AlertaGeradoRepository()
    return repo.list_active()


def marcar_alerta_lido(ident: int, repo: AlertaGeradoRepository | None = None) -> AlertaGerado | None:
    """Marca um alerta como lido."""
    repo = repo or AlertaGeradoRepository()
    return repo.mark_as_read(ident)


def marcar_alerta_resolvido(ident: int, repo: AlertaGeradoRepository | None = None) -> AlertaGerado | None:
    """Marca um alerta como resolvido."""
    repo = repo or AlertaGeradoRepository()
    return repo.mark_as_resolved(ident)
