import pytest


def test_relatorio_dre_page(client):
    resp = client.get('/relatorios/dre')
    assert resp.status_code == 200
    assert 'Demonstra' in resp.text
