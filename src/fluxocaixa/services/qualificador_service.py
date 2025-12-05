from ..repositories.qualificador_repository import QualificadorRepository
from ..models import Qualificador


def list_all_qualificadores(repo: QualificadorRepository | None = None):
    repo = repo or QualificadorRepository()
    return repo.get_all()


def list_active_qualificadores(repo: QualificadorRepository | None = None):
    repo = repo or QualificadorRepository()
    return repo.get_active()


def list_root_qualificadores(repo: QualificadorRepository | None = None):
    repo = repo or QualificadorRepository()
    return repo.get_root()


def get_qualificador(qualificador_id: int, repo: QualificadorRepository | None = None):
    repo = repo or QualificadorRepository()
    return repo.get_by_id(qualificador_id)


def get_qualificador_by_name(name: str, repo: QualificadorRepository | None = None):
    repo = repo or QualificadorRepository()
    return repo.get_by_name(name)


def list_receita_qualificadores(repo: QualificadorRepository | None = None):
    repo = repo or QualificadorRepository()
    return repo.get_receita()


def list_despesa_qualificadores(repo: QualificadorRepository | None = None):
    repo = repo or QualificadorRepository()
    return repo.get_despesa()


def list_receita_qualificadores_folha(repo: QualificadorRepository | None = None):
    """Retorna apenas qualificadores de receita que não têm filhos."""
    repo = repo or QualificadorRepository()
    return repo.get_receita_folha()


def list_despesa_qualificadores_folha(repo: QualificadorRepository | None = None):
    """Retorna apenas qualificadores de despesa que não têm filhos."""
    repo = repo or QualificadorRepository()
    return repo.get_despesa_folha()


def create_qualificador(
    num_qualificador: str,
    dsc_qualificador: str,
    cod_qualificador_pai: int = None,
    repo: QualificadorRepository | None = None
):
    repo = repo or QualificadorRepository()
    qualificador = Qualificador(
        num_qualificador=num_qualificador,
        dsc_qualificador=dsc_qualificador,
        cod_qualificador_pai=cod_qualificador_pai,
    )
    return repo.create(qualificador)


def update_qualificador(
    seq_qualificador: int,
    num_qualificador: str,
    dsc_qualificador: str,
    cod_qualificador_pai: int = None,
    repo: QualificadorRepository | None = None
):
    repo = repo or QualificadorRepository()
    qualificador = repo.get_by_id(seq_qualificador)
    if not qualificador:
        return None

    qualificador.num_qualificador = num_qualificador
    qualificador.dsc_qualificador = dsc_qualificador
    qualificador.cod_qualificador_pai = cod_qualificador_pai

    return repo.update(qualificador)


def delete_qualificador(seq_qualificador: int, repo: QualificadorRepository | None = None):
    repo = repo or QualificadorRepository()
    return repo.delete_logical(seq_qualificador)
