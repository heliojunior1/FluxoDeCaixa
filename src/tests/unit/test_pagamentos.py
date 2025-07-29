import pytest


def test_pagamentos_page(client):
    response = client.get('/pagamentos')
    assert response.status_code == 200
    assert 'Pagamentos' in response.text


def test_relatorios_page(client):
    response = client.get('/relatorios')
    assert response.status_code == 200
    assert 'Relatórios de Fluxo de Caixa' in response.text