from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_read_root_status():
    """Test that root endpoint returns 200 OK"""
    response = client.get("/")
    assert response.status_code == 200


def test_read_root_content():
    """Test that root endpoint returns correct JSON"""
    response = client.get("/")
    assert response.json() == {"Hello": "Python"}
