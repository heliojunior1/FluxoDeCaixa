from ..domain import MapeamentoCreate, MapeamentoOut
from ..repositories import MapeamentoRepository


def list_mapeamentos(repo: MapeamentoRepository | None = None):
    repo = repo or MapeamentoRepository()
    return repo.list(), repo.list_qualificadores()


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
