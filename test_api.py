from fastapi.testclient import TestClient


from api import app
client = TestClient(app)

def test_invalid_login():
    response = client.post(
        "/login",
        data={
            "username": "wrong",
            "password": "wrong"
        }
    )

    assert response.status_code == 401

def test_login():
    response = client.post(
        "/login",
        data={
            "username": "john",
            "password": "smith"
        }
    )

    assert response.status_code == 200
    assert "access_token" in response.json()

def test_products():
    login = client.post(
        "/login",
        data={
            "username": "john",
            "password": "smith"
        }
    )

    token = login.json()["access_token"]

    response = client.get(
        "/products",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200

def test_products_without_token():
    response = client.get("/products")

    assert response.status_code == 401
