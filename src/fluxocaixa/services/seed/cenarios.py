"""Seed data for SimuladorCenario."""

from sqlalchemy import func

from ...models import (
    SimuladorCenario,
    CenarioReceita,
    CenarioDespesa,
    CenarioReceitaAjuste,
    CenarioDespesaAjuste,
    Qualificador,
)
from ...models.base import db


def _encontrar_qualificador(descricao):
    """Find qualificador by description (case-insensitive)."""
    return Qualificador.query.filter(
        func.lower(Qualificador.dsc_qualificador) == func.lower(descricao)
    ).first()


# Ajustes conservadores (percentual fixo por qualificador)
AJUSTES_CONSERVADORES_RECEITA = {
    'ICMS': 2.0, 'IPVA': 1.5, 'ITCMD': 1.0, 'FPE': 2.5,
    'FECOEP': 1.8, 'ROYALTIES': 0.5, 'APLICAÇÕES FINANCEIRAS': 3.0,
    'IR': 1.2, 'OUTRAS RECEITAS': 1.0,
}

# Ajustes realistas receita (variação mensal)
AJUSTES_REALISTAS_RECEITA = {
    'ICMS': [3.0, 2.8, 2.5, 2.2, 2.0, 2.0, 2.0, 2.1, 2.2, 2.3, 2.5, 2.8],
    'IPVA': [5.0, 4.0, 3.0, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 1.0, 1.5],
    'ITCMD': [1.0, 1.2, 1.5, 1.3, 1.0, 1.2, 1.4, 1.6, 1.5, 1.3, 1.2, 1.5],
    'FPE': [1.5, 1.8, 2.0, 2.2, 2.5, 2.3, 2.1, 2.0, 1.8, 1.6, 1.5, 1.4],
    'FECOEP': [2.0, 1.8, 1.5, 1.3, 1.5, 1.8, 2.0, 2.2, 2.0, 1.8, 2.0, 2.5],
    'ROYALTIES': [-1.0, 0.5, 1.0, 0.0, -0.5, 1.5, 2.0, 1.0, 0.5, 1.5, 2.5, 2.0],
    'APLICAÇÕES FINANCEIRAS': [4.0, 4.2, 4.5, 4.3, 4.0, 3.8, 3.5, 3.3, 3.0, 3.2, 3.5, 3.8],
    'IR': [1.0, 1.2, 1.5, 3.5, 2.0, 1.5, 1.2, 1.0, 1.0, 1.2, 1.5, 0.8],
    'OUTRAS RECEITAS': [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.5, 1.4, 1.3, 1.4, 1.5],
}

# Ajustes realistas despesa (variação mensal)
AJUSTES_REALISTAS_DESPESA = {
    'FOLHA': [1.5, 1.5, 1.5, 1.5, 1.8, 1.8, 1.8, 1.8, 1.8, 1.8, 1.8, 3.5],
    'PASEP': [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 5.0, 0.5, 0.5, 0.5, 0.5, 0.5],
    'DÍVIDAS': [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
    'PRECATÓRIOS': [1.0, 0.5, 0.5, 1.5, 1.0, 0.5, 0.5, 2.0, 1.5, 1.0, 0.5, 3.0],
    'CUSTEIO': [3.0, 2.5, 2.0, 1.5, 1.2, 1.0, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0],
    'INVESTIMENTO + AUMENTO DE CAPITAL': [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
    'REPASSE MUNICÍPIOS': [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5],
    'REPASSE FUNDEB': [2.0, 1.8, 1.6, 1.5, 1.5, 1.5, 1.5, 1.6, 1.7, 1.8, 2.0, 2.2],
    'SAÚDE 12%': [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
    'EDUCAÇÃO 5%': [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
    'PODERES': [1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2],
    'RESTOS A PAGAR TESOURO e DEMAIS': [5.0, 4.0, 3.0, 2.5, 2.0, 1.5, 1.0, 0.8, 0.6, 0.5, 0.3, 0.2],
    'FECOEP - RESTOS A PAGAR - FONTE 761': [4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.2, 1.0, 0.8, 0.6, 0.4, 0.2],
}


def seed_cenarios(session=None):
    """Seed SimuladorCenario with example scenarios."""
    session = session or db.session

    if SimuladorCenario.query.first():
        return  # Already seeded

    ano_base = 2025
    meses_projecao = 12

    # ========== CENÁRIO 1: CONSERVADOR ==========
    cenario1 = SimuladorCenario(
        nom_cenario='Cenário Conservador',
        dsc_cenario='Projeção conservadora com receitas manuais e despesas baseadas na LDO',
        ano_base=ano_base,
        meses_projecao=meses_projecao,
        ind_status='A',
        cod_pessoa_inclusao=1
    )
    session.add(cenario1)
    session.flush()

    cenario1_receita = CenarioReceita(
        seq_simulador_cenario=cenario1.seq_simulador_cenario,
        cod_tipo_cenario='MANUAL'
    )
    session.add(cenario1_receita)
    session.flush()

    cenario1_despesa = CenarioDespesa(
        seq_simulador_cenario=cenario1.seq_simulador_cenario,
        cod_tipo_cenario='LOA'
    )
    session.add(cenario1_despesa)
    session.flush()

    # Add conservative adjustments
    for qual_nome, percentual in AJUSTES_CONSERVADORES_RECEITA.items():
        qual = _encontrar_qualificador(qual_nome)
        if qual:
            for mes in range(1, 13):
                session.add(CenarioReceitaAjuste(
                    seq_cenario_receita=cenario1_receita.seq_cenario_receita,
                    seq_qualificador=qual.seq_qualificador,
                    ano=ano_base,
                    mes=mes,
                    cod_tipo_ajuste='P',
                    val_ajuste=percentual
                ))

    # ========== CENÁRIO 2: REALISTA ==========
    cenario2 = SimuladorCenario(
        nom_cenario='Cenário Realista',
        dsc_cenario='Projeção realista com ajustes manuais variáveis em receitas e despesas',
        ano_base=ano_base,
        meses_projecao=meses_projecao,
        ind_status='A',
        cod_pessoa_inclusao=1
    )
    session.add(cenario2)
    session.flush()

    cenario2_receita = CenarioReceita(
        seq_simulador_cenario=cenario2.seq_simulador_cenario,
        cod_tipo_cenario='MANUAL'
    )
    session.add(cenario2_receita)
    session.flush()

    cenario2_despesa = CenarioDespesa(
        seq_simulador_cenario=cenario2.seq_simulador_cenario,
        cod_tipo_cenario='MANUAL'
    )
    session.add(cenario2_despesa)
    session.flush()

    # Add realistic revenue adjustments
    for qual_nome, percentuais in AJUSTES_REALISTAS_RECEITA.items():
        qual = _encontrar_qualificador(qual_nome)
        if qual:
            for mes, percentual in enumerate(percentuais, 1):
                session.add(CenarioReceitaAjuste(
                    seq_cenario_receita=cenario2_receita.seq_cenario_receita,
                    seq_qualificador=qual.seq_qualificador,
                    ano=ano_base,
                    mes=mes,
                    cod_tipo_ajuste='P',
                    val_ajuste=percentual
                ))

    # Add realistic expense adjustments
    for qual_nome, percentuais in AJUSTES_REALISTAS_DESPESA.items():
        qual = _encontrar_qualificador(qual_nome)
        if qual:
            for mes, percentual in enumerate(percentuais, 1):
                session.add(CenarioDespesaAjuste(
                    seq_cenario_despesa=cenario2_despesa.seq_cenario_despesa,
                    seq_qualificador=qual.seq_qualificador,
                    ano=ano_base,
                    mes=mes,
                    cod_tipo_ajuste='P',
                    val_ajuste=percentual
                ))

    session.commit()
    print("Seeded 2 complete simulador scenarios with adjustments for ALL qualifiers across 12 months")
