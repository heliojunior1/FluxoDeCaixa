"""Tests for pagamentos routes."""


def test_pagamentos_page(client):
    response = client.get('/pagamentos')
    assert response.status_code == 200
    assert 'pagamento' in response.text.lower() or 'Pagamento' in response.text


def test_relatorios_page(client):
    response = client.get('/relatorios')
    assert response.status_code == 200
    # Check for any report-related content
    assert 'relat' in response.text.lower()