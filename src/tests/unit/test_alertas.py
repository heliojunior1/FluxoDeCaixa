import pytest


def test_alertas_page(client):
    response = client.get('/alertas')
    assert response.status_code == 200
    assert 'Gestão de Alertas' in response.text
