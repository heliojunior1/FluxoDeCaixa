"""Placeholder tests for basic page loads."""


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    # Check that the page loads with some content
    assert len(response.text) > 100