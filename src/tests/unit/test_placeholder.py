

def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Dashboard" in response.text
    assert "Acesso Rápido" in response.text