from fastapi.testclient import TestClient


def test_add_lancamento_flow(client: TestClient):
    from fluxocaixa.models import (
        db,
        Lancamento,
        Qualificador,
        TipoLancamento,
        OrigemLancamento,
    )

    # initial count
    initial = db.session.query(Lancamento).count()
    qual = Qualificador.query.first()
    tipo = TipoLancamento.query.first()
    origem = OrigemLancamento.query.first()
    resp = client.post(
        '/saldos/add',
        data={
            'dat_lancamento': '2025-01-01',
            'seq_qualificador': qual.seq_qualificador,
            'val_lancamento': '123.45',
            'cod_tipo_lancamento': tipo.cod_tipo_lancamento,
            'cod_origem_lancamento': origem.cod_origem_lancamento,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert db.session.query(Lancamento).count() == initial + 1


def test_add_pagamento_flow(client: TestClient):
    from fluxocaixa.models import db, Pagamento, Orgao

    initial = db.session.query(Pagamento).count()
    orgao = Orgao.query.first()
    resp = client.post(
        '/pagamentos/add',
        data={
            'dat_pagamento': '2025-02-01',
            'cod_orgao': orgao.cod_orgao,
            'val_pagamento': '200.00',
            'dsc_pagamento': 'Teste de pagamento',
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert db.session.query(Pagamento).count() == initial + 1


def test_relatorio_resumo_page(client: TestClient):
    resp = client.get('/relatorios/resumo')
    assert resp.status_code == 200
    assert 'Resumo do Fluxo de Caixa' in resp.text

def test_criar_alerta_flow(client: TestClient):
    from fluxocaixa.models import db, Alerta

    initial = db.session.query(Alerta).count()
    resp = client.post(
        '/alertas/novo',
        data={
            'nom_alerta': 'Teste',
            'metric': 'saldo',
            'logic': 'menor',
            'valor': '1000',
            'period': 'dia',
            'notif_system': 'S',
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert db.session.query(Alerta).count() == initial + 1


def test_editar_e_desativar_alerta_flow(client: TestClient):
    from fluxocaixa.models import db, Alerta

    alerta = Alerta(
        nom_alerta='Editar',
        metric='saldo',
        logic='menor',
        valor=50,
        period='dia',
        notif_system='S',
        cod_pessoa_inclusao=1,
    )
    db.session.add(alerta)
    db.session.commit()

    resp = client.post(
        f'/alertas/edit/{alerta.seq_alerta}',
        data={'nom_alerta': 'Editado', 'metric': 'saldo', 'logic': 'maior', 'valor': '60', 'period': 'mes'},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    db.session.refresh(alerta)
    assert alerta.nom_alerta == 'Editado'
    assert alerta.logic == 'maior'

    resp = client.post(f'/alertas/delete/{alerta.seq_alerta}', follow_redirects=False)
    assert resp.status_code == 303
    db.session.refresh(alerta)
    assert alerta.ind_status == 'I'


def test_criar_alerta_comparativo_flow(client: TestClient):
    from fluxocaixa.models import Alerta, Qualificador
    qual = Qualificador.query.first()
    resp = client.post(
        '/alertas/novo',
        data={
            'nom_alerta': 'Comparativo Teste',
            'metric': 'comparativo',
            'seq_qualificador': qual.seq_qualificador,
            'logic': 'maior',
            'valor': '15',
            # period not required for comparativo
            'notif_system': 'S',
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    alerta = Alerta.query.order_by(Alerta.seq_alerta.desc()).first()
    assert alerta.metric == 'comparativo'
    assert alerta.seq_qualificador == qual.seq_qualificador
    assert alerta.period is None
