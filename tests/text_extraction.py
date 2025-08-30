import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_info_endpoint():
    response = client.get("/info")
    assert response.status_code == 200
    assert "version" in response.json()

def test_extract_without_file():
    response = client.post("/extract")
    assert response.status_code == 422  # Validation error

# Add more tests with actual marksheet samples
