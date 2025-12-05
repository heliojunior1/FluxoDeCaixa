"""
Seed module for populating the database with initial test data.

This module orchestrates all seed operations by calling specialized
sub-modules for different data types.
"""

from ...models import Mapeamento, Pagamento, Lancamento, Qualificador, Orgao, OrigemLancamento, TipoLancamento
from ...models.base import db

from .base_types import seed_base_types
from .qualificadores import seed_qualificadores
from .lancamentos import seed_lancamentos
from .pagamentos import seed_pagamentos
from .mapeamentos import seed_mapeamentos
from .conferencia import seed_conferencia
from .contas_alertas import seed_contas_bancarias, seed_alertas
from .saldos import seed_saldos_conta
from .cenarios import seed_cenarios


def seed_data(session=None):
    """Populate the database with basic records for testing."""
    session = session or db.session

    # Clear existing data to ensure a clean slate
    try:
        session.query(Mapeamento).delete()
    except Exception:
        pass  # Table might not exist yet

    session.query(Pagamento).delete()
    session.query(Lancamento).delete()
    session.query(Qualificador).delete()
    session.query(Orgao).delete()
    session.query(OrigemLancamento).delete()
    session.query(TipoLancamento).delete()
    session.commit()

    # Seed in order of dependencies
    seed_base_types(session)
    seed_qualificadores(session)
    seed_lancamentos(session)
    seed_pagamentos(session)
    seed_mapeamentos(session)
    seed_conferencia(session)
    seed_contas_bancarias(session)
    seed_alertas(session)
    seed_saldos_conta(session)
    seed_cenarios(session)


__all__ = ['seed_data']
