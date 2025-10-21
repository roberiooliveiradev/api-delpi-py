# tests/test_healthcheck.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_status():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"
