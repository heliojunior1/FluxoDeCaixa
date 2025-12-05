"""Seed data for Pagamentos."""

from datetime import date
import calendar
from sqlalchemy import func

from ...models import Pagamento, Orgao, Qualificador
from ...models.base import db
from .financial_data import DESPESAS_2024, DESPESAS_2025, DESPESA_ORGAO_MAP


def _encontrar_qualificador(descricao):
    """Find qualificador by description (case-insensitive)."""
    return Qualificador.query.filter(
        func.lower(Qualificador.dsc_qualificador) == func.lower(descricao)
    ).first()


def seed_pagamentos(session=None):
    """Seed Pagamentos for 2024 and 2025."""
    session = session or db.session

    if Pagamento.query.first():
        return  # Already seeded

    def add_pagamentos_ano(despesas, ano):
        for despesa_nome, valores in despesas.items():
            if despesa_nome not in DESPESA_ORGAO_MAP:
                continue

            orgao_nome, qualificador_nome = DESPESA_ORGAO_MAP[despesa_nome]
            orgao = Orgao.query.filter_by(nom_orgao=orgao_nome).first()
            qualificador = _encontrar_qualificador(qualificador_nome)

            if orgao:
                for month, valor in enumerate(valores, 1):
                    if valor > 0:
                        session.add(Pagamento(
                            dat_pagamento=date(ano, month, 15),
                            cod_orgao=orgao.cod_orgao,
                            seq_qualificador=qualificador.seq_qualificador if qualificador else None,
                            val_pagamento=valor * 1000,
                            dsc_pagamento=f'Despesa {despesa_nome} - {calendar.month_name[month]} {ano}'
                        ))

    add_pagamentos_ano(DESPESAS_2024, 2024)
    add_pagamentos_ano(DESPESAS_2025, 2025)
    session.commit()
