from ..domain import MapeamentoCreate, MapeamentoOut
from ..repositories import MapeamentoRepository


def list_mapeamentos(status: str | None = None, tipo: str | None = None, repo: MapeamentoRepository | None = None):
    repo = repo or MapeamentoRepository()
    return repo.list(status, tipo), repo.list_qualificadores()


def get_mapeamento_by_id(ident: int, repo: MapeamentoRepository | None = None) -> MapeamentoOut:
    repo = repo or MapeamentoRepository()
    mp = repo.get(ident)
    return MapeamentoOut(
        seq_mapeamento=mp.seq_mapeamento,
        seq_qualificador=mp.seq_qualificador,
        dsc_mapeamento=mp.dsc_mapeamento,
        txt_condicao=mp.txt_condicao,
        ind_status=mp.ind_status,
        dat_inclusao=mp.dat_inclusao,
    )


def create_mapeamento(data: MapeamentoCreate, repo: MapeamentoRepository | None = None) -> MapeamentoOut:
    repo = repo or MapeamentoRepository()
    mp = repo.create(data)
    return MapeamentoOut(
        seq_mapeamento=mp.seq_mapeamento,
        seq_qualificador=mp.seq_qualificador,
        dsc_mapeamento=mp.dsc_mapeamento,
        txt_condicao=mp.txt_condicao,
        ind_status=mp.ind_status,
        dat_inclusao=mp.dat_inclusao,
    )


def update_mapeamento(ident: int, data: MapeamentoCreate, repo: MapeamentoRepository | None = None) -> MapeamentoOut:
    repo = repo or MapeamentoRepository()
    mp = repo.update(ident, data)
    return MapeamentoOut(
        seq_mapeamento=mp.seq_mapeamento,
        seq_qualificador=mp.seq_qualificador,
        dsc_mapeamento=mp.dsc_mapeamento,
        txt_condicao=mp.txt_condicao,
        ind_status=mp.ind_status,
        dat_inclusao=mp.dat_inclusao,
    )


def delete_mapeamento(ident: int, repo: MapeamentoRepository | None = None):
    repo = repo or MapeamentoRepository()
    repo.soft_delete(ident)
