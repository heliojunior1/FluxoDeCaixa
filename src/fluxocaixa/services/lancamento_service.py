from ..domain import LancamentoCreate, LancamentoOut
from ..repositories import LancamentoRepository


def list_lancamentos(repo: LancamentoRepository | None = None):
    repo = repo or LancamentoRepository()
    return repo.list()


def create_lancamento(data: LancamentoCreate, repo: LancamentoRepository | None = None) -> LancamentoOut:
    repo = repo or LancamentoRepository()
    lanc = repo.create(data)
    return LancamentoOut(
        seq_lancamento=lanc.seq_lancamento,
        dat_lancamento=lanc.dat_lancamento,
        seq_qualificador=lanc.seq_qualificador,
        val_lancamento=lanc.val_lancamento,
        cod_tipo_lancamento=lanc.cod_tipo_lancamento,
        cod_origem_lancamento=lanc.cod_origem_lancamento,
        dsc_lancamento=None,
    )


def update_lancamento(ident: int, data: LancamentoCreate, repo: LancamentoRepository | None = None) -> LancamentoOut:
    repo = repo or LancamentoRepository()
    lanc = repo.update(ident, data)
    return LancamentoOut(
        seq_lancamento=lanc.seq_lancamento,
        dat_lancamento=lanc.dat_lancamento,
        seq_qualificador=lanc.seq_qualificador,
        val_lancamento=lanc.val_lancamento,
        cod_tipo_lancamento=lanc.cod_tipo_lancamento,
        cod_origem_lancamento=lanc.cod_origem_lancamento,
        dsc_lancamento=None,
    )


def delete_lancamento(ident: int, repo: LancamentoRepository | None = None):
    repo = repo or LancamentoRepository()
    repo.soft_delete(ident)
