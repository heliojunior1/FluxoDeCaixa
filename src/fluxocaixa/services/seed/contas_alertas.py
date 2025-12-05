"""Seed data for ContaBancaria and AlertaGerado."""

from datetime import date

from ...models import ContaBancaria, AlertaGerado
from ...models.base import db


def seed_contas_bancarias(session=None):
    """Seed government bank accounts."""
    session = session or db.session

    if ContaBancaria.query.first():
        return  # Already seeded

    contas = [
        ContaBancaria(cod_banco='001', num_agencia='0001', num_conta='123456-7', dsc_conta='Conta Única - Tesouro'),
        ContaBancaria(cod_banco='104', num_agencia='4567', num_conta='00012345-0', dsc_conta='Conta Judicial'),
        ContaBancaria(cod_banco='237', num_agencia='1234', num_conta='98765-4', dsc_conta='Conta Salario'),
        ContaBancaria(cod_banco='341', num_agencia='3200', num_conta='556677-8', dsc_conta='Conta de FPE '),
        ContaBancaria(cod_banco='033', num_agencia='9999', num_conta='112233-4', dsc_conta='Contas de Recursos Próprios Vinculados'),
    ]
    session.add_all(contas)
    session.commit()


def seed_alertas(session=None):
    """Seed demo AlertaGerado records."""
    session = session or db.session

    if AlertaGerado.query.first():
        return  # Already seeded

    alertas_demo = [
        AlertaGerado(
            dat_processamento=None,
            dat_referencia=date.today(),
            mensagem='Limite prudencial (46.2%) atingido. Novas contratações requerem atenção do TCE.',
            categoria='DESPESA_PESSOAL',
            severidade='CRITICAL',
            valor_obtido=46.2,
            valor_esperado=46.0,
        ),
        AlertaGerado(
            dat_processamento=None,
            dat_referencia=date(2025, 12, 1),
            mensagem='Queda de arrecadação PPE prevista para Dezembro (-2%) devido à desaceleração econômica.',
            categoria='RECEITA',
            severidade='WARNING',
            valor_obtido=-2.0,
            valor_esperado=0.0,
        ),
        AlertaGerado(
            dat_processamento=None,
            dat_referencia=date.today(),
            mensagem='Superávit orçamentário de R$ 1.2M identificado. Considere investimentos estratégicos.',
            categoria='SALDO',
            severidade='INFO',
            valor_obtido=1200000.0,
            valor_esperado=0.0,
        ),
    ]
    session.add_all(alertas_demo)
    session.commit()
