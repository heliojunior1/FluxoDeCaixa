"""Service layer for Pagamento operations."""
from __future__ import annotations

from ..domain import PagamentoCreate, PagamentoOut
from ..models import Pagamento, Orgao, Qualificador
from ..repositories import PagamentoRepository


def list_pagamentos(
    repo: PagamentoRepository | None = None
) -> tuple[list[Pagamento], list[Orgao], list[Qualificador]]:
    """List all pagamentos with their orgaos and qualificadores."""
    repo = repo or PagamentoRepository()
    return repo.list_pagamentos(), repo.list_orgaos(), repo.list_qualificadores()


def create_pagamento(data: PagamentoCreate, repo: PagamentoRepository | None = None) -> PagamentoOut:
    """Create a new pagamento."""
    repo = repo or PagamentoRepository()
    pag = repo.create(data)
    return PagamentoOut(
        seq_pagamento=pag.seq_pagamento,
        dat_pagamento=pag.dat_pagamento,
        cod_orgao=pag.cod_orgao,
        seq_qualificador=pag.seq_qualificador,
        val_pagamento=pag.val_pagamento,
        dsc_pagamento=pag.dsc_pagamento,
    )
