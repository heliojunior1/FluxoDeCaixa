from ..domain import PagamentoCreate, PagamentoOut
from ..repositories import PagamentoRepository


def list_pagamentos(repo: PagamentoRepository | None = None):
    repo = repo or PagamentoRepository()
    return repo.list_pagamentos(), repo.list_orgaos()


def create_pagamento(data: PagamentoCreate, repo: PagamentoRepository | None = None) -> PagamentoOut:
    repo = repo or PagamentoRepository()
    pag = repo.create(data)
    return PagamentoOut(
        seq_pagamento=pag.seq_pagamento,
        dat_pagamento=pag.dat_pagamento,
        cod_orgao=pag.cod_orgao,
        val_pagamento=pag.val_pagamento,
        dsc_pagamento=pag.dsc_pagamento,
    )
