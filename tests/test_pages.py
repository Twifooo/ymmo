"""Tests d'intégration HTTP de base."""

def test_home_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Ymmo" in resp.data


def test_list_page(client):
    resp = client.get("/biens")
    assert resp.status_code == 200


def test_login_page(client):
    resp = client.get("/auth/connexion")
    assert resp.status_code == 200
    assert b"Connexion" in resp.data


def test_market_page(client):
    resp = client.get("/marche")
    assert resp.status_code == 200


def test_estimate_page(client):
    resp = client.get("/estimer")
    assert resp.status_code == 200


def test_404(client):
    resp = client.get("/route-inconnue")
    assert resp.status_code == 404


def test_admin_requires_login(client):
    resp = client.get("/admin/", follow_redirects=False)
    assert resp.status_code in (302, 401)
