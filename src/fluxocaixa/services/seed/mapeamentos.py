"""Seed data for Mapeamentos."""

from sqlalchemy import func

from ...models import Mapeamento, Qualificador
from ...models.base import db


def _encontrar_qualificador(descricao):
    """Find qualificador by description (case-insensitive)."""
    return Qualificador.query.filter(
        func.lower(Qualificador.dsc_qualificador) == func.lower(descricao)
    ).first()


def seed_mapeamentos(session=None):
    """Seed example Mapeamentos."""
    session = session or db.session

    try:
        if Mapeamento.query.first():
            return  # Already seeded

        # Mapeamentos de Receita
        icms_qual = _encontrar_qualificador('ICMS')
        if icms_qual:
            session.add(Mapeamento(
                seq_qualificador=icms_qual.seq_qualificador,
                dsc_mapeamento='Mapeamento ICMS - Análise de Arrecadação',
                txt_condicao="abc != CLASSIFICADOR('CAMPO')",
                ind_status='A'
            ))

        fpe_qual = _encontrar_qualificador('FPE')
        if fpe_qual:
            session.add(Mapeamento(
                seq_qualificador=fpe_qual.seq_qualificador,
                dsc_mapeamento='Mapeamento FPE - Transferências Federais',
                txt_condicao="abc != CLASSIFICADOR('CAMPO')",
                ind_status='A'
            ))

        # Mapeamentos de Despesa
        folha_qual = _encontrar_qualificador('FOLHA')
        if folha_qual:
            session.add(Mapeamento(
                seq_qualificador=folha_qual.seq_qualificador,
                dsc_mapeamento='Mapeamento Folha de Pagamento',
                txt_condicao="abc != CLASSIFICADOR('CAMPO')",
                ind_status='A'
            ))

        custeio_qual = _encontrar_qualificador('CUSTEIO')
        if custeio_qual:
            session.add(Mapeamento(
                seq_qualificador=custeio_qual.seq_qualificador,
                dsc_mapeamento='Mapeamento Custeio Administrativo',
                txt_condicao="abc != CLASSIFICADOR('CAMPO')",
                ind_status='A'
            ))

        # Mapeamento inativo
        repasse_mun_qual = _encontrar_qualificador('REPASSE MUNICÍPIOS')
        if repasse_mun_qual:
            session.add(Mapeamento(
                seq_qualificador=repasse_mun_qual.seq_qualificador,
                dsc_mapeamento='Mapeamento Repasse Municípios - Análise Suspensa',
                txt_condicao="abc != CLASSIFICADOR('CAMPO')",
                ind_status='I'
            ))

        session.commit()

    except Exception as e:
        print(f"Erro ao criar mapeamentos: {e}")
