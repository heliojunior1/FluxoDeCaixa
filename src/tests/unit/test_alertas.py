import pytest


def test_alertas_page(client):
    response = client.get('/alertas')
    assert response.status_code == 200
    assert 'Gestão de Alertas' in response.text


def test_alertas_novo_contains_comparativo_option(client):
    resp = client.get('/alertas/novo')
    assert resp.status_code == 200
    assert 'Comparativo Realizado vs Projetado' in resp.text
