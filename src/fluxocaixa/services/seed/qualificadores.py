"""Seed data for Qualificadores (hierarchical structure)."""

from ...models import Qualificador
from ...models.base import db


def seed_qualificadores(session=None):
    """Populate hierarchical Qualificadores structure."""
    session = session or db.session

    if Qualificador.query.first():
        return  # Already seeded

    # ========== RECEITA LÍQUIDA ==========
    receita_liquida = Qualificador(
        num_qualificador='1',
        dsc_qualificador='RECEITA LÍQUIDA',
        cod_qualificador_pai=None
    )
    session.add(receita_liquida)
    session.flush()

    # Impostos (dentro de Receita Líquida)
    impostos = Qualificador(
        num_qualificador='1.0',
        dsc_qualificador='IMPOSTOS',
        cod_qualificador_pai=receita_liquida.seq_qualificador
    )
    session.add(impostos)
    session.flush()

    # Impostos específicos
    for num, desc in [('1.0.0', 'ICMS'), ('1.0.1', 'IPVA'), ('1.5.2', 'ITCMD')]:
        session.add(Qualificador(
            num_qualificador=num,
            dsc_qualificador=desc,
            cod_qualificador_pai=impostos.seq_qualificador
        ))
    session.flush()

    # Transferências Federais
    transf_federais = Qualificador(
        num_qualificador='1.1',
        dsc_qualificador='TRANSFERÊNCIAS FEDERAIS',
        cod_qualificador_pai=receita_liquida.seq_qualificador
    )
    session.add(transf_federais)
    session.flush()

    # FPE
    session.add(Qualificador(
        num_qualificador='1.1.1',
        dsc_qualificador='FPE',
        cod_qualificador_pai=transf_federais.seq_qualificador
    ))

    # Demais Receitas
    demais_receitas = Qualificador(
        num_qualificador='1.2',
        dsc_qualificador='DEMAIS RECEITAS',
        cod_qualificador_pai=receita_liquida.seq_qualificador
    )
    session.add(demais_receitas)
    session.flush()

    for num, desc in [
        ('1.2.1', 'FECOEP'),
        ('1.2.2', 'ROYALTIES'),
        ('1.2.3', 'APLICAÇÕES FINANCEIRAS'),
        ('1.2.4', 'IR'),
        ('1.2.5', 'OUTRAS RECEITAS')
    ]:
        session.add(Qualificador(
            num_qualificador=num,
            dsc_qualificador=desc,
            cod_qualificador_pai=demais_receitas.seq_qualificador
        ))
    session.flush()

    # ========== DESPESAS ==========
    despesas = Qualificador(
        num_qualificador='2',
        dsc_qualificador='DESPESAS',
        cod_qualificador_pai=None
    )
    session.add(despesas)
    session.flush()

    # Pessoal
    pessoal = Qualificador(
        num_qualificador='2.0',
        dsc_qualificador='PESSOAL',
        cod_qualificador_pai=despesas.seq_qualificador
    )
    session.add(pessoal)
    session.flush()

    for num, desc in [('2.0.1', 'FOLHA'), ('2.0.2', 'PASEP')]:
        session.add(Qualificador(
            num_qualificador=num,
            dsc_qualificador=desc,
            cod_qualificador_pai=pessoal.seq_qualificador
        ))

    # Serviço da Dívida
    servico_divida = Qualificador(
        num_qualificador='2.1',
        dsc_qualificador='SERVIÇO DA DÍVIDA',
        cod_qualificador_pai=despesas.seq_qualificador
    )
    session.add(servico_divida)
    session.flush()

    for num, desc in [('2.1.1', 'DÍVIDAS'), ('2.1.2', 'PRECATÓRIOS')]:
        session.add(Qualificador(
            num_qualificador=num,
            dsc_qualificador=desc,
            cod_qualificador_pai=servico_divida.seq_qualificador
        ))

    # Custeio
    custeio = Qualificador(
        num_qualificador='2.2',
        dsc_qualificador='CUSTEIO - COTA FINANCEIRA',
        cod_qualificador_pai=despesas.seq_qualificador
    )
    session.add(custeio)
    session.flush()

    session.add(Qualificador(
        num_qualificador='2.2.1',
        dsc_qualificador='CUSTEIO',
        cod_qualificador_pai=custeio.seq_qualificador
    ))

    # Investimento
    investimento = Qualificador(
        num_qualificador='2.3',
        dsc_qualificador='INVESTIMENTO - COTA FINANCEIRA',
        cod_qualificador_pai=despesas.seq_qualificador
    )
    session.add(investimento)
    session.flush()

    session.add(Qualificador(
        num_qualificador='2.3.1',
        dsc_qualificador='INVESTIMENTO + AUMENTO DE CAPITAL',
        cod_qualificador_pai=investimento.seq_qualificador
    ))

    # Encargos Gerais
    encargos = Qualificador(
        num_qualificador='2.4',
        dsc_qualificador='ENCARGOS GERAIS',
        cod_qualificador_pai=despesas.seq_qualificador
    )
    session.add(encargos)
    session.flush()

    for num, desc in [
        ('2.4.1', 'REPASSE MUNICÍPIOS'),
        ('2.4.2', 'REPASSE FUNDEB'),
        ('2.4.3', 'SAÚDE 12%'),
        ('2.4.4', 'EDUCAÇÃO 5%'),
        ('2.4.5', 'PODERES')
    ]:
        session.add(Qualificador(
            num_qualificador=num,
            dsc_qualificador=desc,
            cod_qualificador_pai=encargos.seq_qualificador
        ))

    # Restos a Pagar
    restos_pagar = Qualificador(
        num_qualificador='2.5',
        dsc_qualificador='RESTOS A PAGAR',
        cod_qualificador_pai=despesas.seq_qualificador
    )
    session.add(restos_pagar)
    session.flush()

    for num, desc in [
        ('2.5.1', 'RESTOS A PAGAR TESOURO e DEMAIS'),
        ('2.5.2', 'FECOEP - RESTOS A PAGAR - FONTE 761')
    ]:
        session.add(Qualificador(
            num_qualificador=num,
            dsc_qualificador=desc,
            cod_qualificador_pai=restos_pagar.seq_qualificador
        ))

    session.commit()
