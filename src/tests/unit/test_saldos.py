def test_saldos_page(client):
    response = client.get('/saldos')
    assert response.status_code == 200
    assert 'Lançamentos' in response.text
