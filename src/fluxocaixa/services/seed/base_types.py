"""Seed data for basic types: TipoLancamento, OrigemLancamento, Orgao."""

from ...models import TipoLancamento, OrigemLancamento, Orgao
from ...models.base import db


def seed_base_types(session=None):
    """Populate base types: TipoLancamento, OrigemLancamento, Orgao."""
    session = session or db.session

    # Tipos de Lançamento
    if not TipoLancamento.query.first():
        session.add_all([
            TipoLancamento(dsc_tipo_lancamento='Entrada'),
            TipoLancamento(dsc_tipo_lancamento='Saída'),
        ])

    # Origens de Lançamento
    if not OrigemLancamento.query.first():
        session.add_all([
            OrigemLancamento(dsc_origem_lancamento='Manual', ind_status='A'),
            OrigemLancamento(dsc_origem_lancamento='Automático', ind_status='A'),
            OrigemLancamento(dsc_origem_lancamento='Importado', ind_status='A'),
        ])

    # Órgãos
    if not Orgao.query.first():
        session.add_all([
            Orgao(nom_orgao='Secretaria de Saúde'),
            Orgao(nom_orgao='Secretaria de Educação'),
            Orgao(nom_orgao='Secretaria de Fazenda'),
            Orgao(nom_orgao='Secretaria de Administração'),
            Orgao(nom_orgao='Secretaria de Infraestrutura'),
            Orgao(nom_orgao='Secretaria de Segurança Pública'),
            Orgao(nom_orgao='Universidade Estadual'),
            Orgao(nom_orgao='Assembleia Legislativa'),
            Orgao(nom_orgao='Tribunal de Contas'),
            Orgao(nom_orgao='Tribunal de Justiça'),
            Orgao(nom_orgao='Ministério Público'),
            Orgao(nom_orgao='Defensoria Pública'),
        ])

    session.commit()
