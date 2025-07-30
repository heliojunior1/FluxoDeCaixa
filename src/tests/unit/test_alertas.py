import pytest


def test_alertas_page(client):
    response = client.get('/alertas')
    assert response.status_code == 200
    assert 'Gestão de Alertas' in response.text
    assert 'Período' in response.text
    assert 'Ações' in response.text


def test_alertas_novo_contains_comparativo_option(client):
    resp = client.get('/alertas/novo')
    assert resp.status_code == 200
    assert 'Comparativo Realizado vs Projetado' in resp.text
    assert 'Período' in resp.text


def test_alertas_edit_page(client):
    from fluxocaixa.models import db, Alerta

    alerta = Alerta(
        nom_alerta='Edit Test',
        metric='saldo',
        logic='menor',
        valor=100,
        period='dia',
        notif_system='S',
        cod_pessoa_inclusao=1,
    )
    db.session.add(alerta)
    db.session.commit()

    resp = client.get(f'/alertas/edit/{alerta.seq_alerta}')
    assert resp.status_code == 200
    assert 'Editar Regra de Alerta' in resp.text
