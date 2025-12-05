"""Seed data for Lancamentos (entries/exits)."""

from datetime import date
from sqlalchemy import func

from ...models import Lancamento, TipoLancamento, OrigemLancamento, Qualificador
from ...models.base import db
from .financial_data import (
    RECEITAS_2024, RECEITAS_2025,
    DESPESAS_2024, DESPESAS_2025,
    QUALIFICADOR_CONTA_MAP
)


def _encontrar_qualificador(descricao):
    """Find qualificador by description (case-insensitive)."""
    return Qualificador.query.filter(
        func.lower(Qualificador.dsc_qualificador) == func.lower(descricao)
    ).first()


def seed_lancamentos(session=None):
    """Seed Lancamentos (receitas e despesas) for 2024 and 2025."""
    session = session or db.session

    if Lancamento.query.first():
        return  # Already seeded

    tipo_entrada = TipoLancamento.query.filter_by(dsc_tipo_lancamento='Entrada').first()
    tipo_saida = TipoLancamento.query.filter_by(dsc_tipo_lancamento='Saída').first()
    origem_manual = OrigemLancamento.query.filter_by(dsc_origem_lancamento='Manual').first()

    if not tipo_entrada or not origem_manual:
        return

    # Helper to add lancamentos for a year
    def add_lancamentos_ano(dados_receita, dados_despesa, ano):
        # Receitas
        for origem_nome, valores in dados_receita.items():
            qualificador = _encontrar_qualificador(origem_nome)
            if qualificador:
                seq_conta = QUALIFICADOR_CONTA_MAP.get(origem_nome, 1)
                for month, valor in enumerate(valores, 1):
                    session.add(Lancamento(
                        dat_lancamento=date(ano, month, 15),
                        seq_qualificador=qualificador.seq_qualificador,
                        val_lancamento=valor * 1000,
                        cod_tipo_lancamento=tipo_entrada.cod_tipo_lancamento,
                        cod_origem_lancamento=origem_manual.cod_origem_lancamento,
                        cod_pessoa_inclusao=1,
                        seq_conta=seq_conta
                    ))

        # Despesas
        if tipo_saida:
            for orgao_nome, valores in dados_despesa.items():
                qualificador = _encontrar_qualificador(orgao_nome)
                if qualificador:
                    seq_conta = QUALIFICADOR_CONTA_MAP.get(orgao_nome, 1)
                    for month, valor in enumerate(valores, 1):
                        if valor > 0:
                            session.add(Lancamento(
                                dat_lancamento=date(ano, month, 15),
                                seq_qualificador=qualificador.seq_qualificador,
                                val_lancamento=-valor * 1000,
                                cod_tipo_lancamento=tipo_saida.cod_tipo_lancamento,
                                cod_origem_lancamento=origem_manual.cod_origem_lancamento,
                                cod_pessoa_inclusao=1,
                                seq_conta=seq_conta
                            ))

    add_lancamentos_ano(RECEITAS_2024, DESPESAS_2024, 2024)
    add_lancamentos_ano(RECEITAS_2025, DESPESAS_2025, 2025)
    session.commit()
