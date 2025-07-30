from ..domain import AlertaCreate, AlertaUpdate
from ..repositories import AlertaRepository


def list_alertas(repo: AlertaRepository | None = None):
    repo = repo or AlertaRepository()
    return repo.list(), repo.list_qualificadores()


def create_alerta(data: AlertaCreate, repo: AlertaRepository | None = None):
    repo = repo or AlertaRepository()
    return repo.create(data)


def update_alerta(ident: int, data: AlertaUpdate, repo: AlertaRepository | None = None):
    repo = repo or AlertaRepository()
    return repo.update(ident, data)


def delete_alerta(ident: int, repo: AlertaRepository | None = None):
    repo = repo or AlertaRepository()
    repo.soft_delete(ident)
