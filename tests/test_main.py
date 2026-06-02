import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.database import get_db

client = TestClient(app)


# ─── HEALTH CHECK ────────────────────────────────────────────

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ─── CREATE EVENT ─────────────────────────────────────────────

def test_create_event_invalid_url():
    response = client.post("/events", json={
        "target_url": "not-a-valid-url",
        "event_type": "payment.completed",
        "payload": '{"event": "payment.completed"}'
    })
    assert response.status_code == 422


def test_create_event_missing_event_type():
    response = client.post("/events", json={
        "target_url": "https://example.com/webhook",
        "payload": '{"event": "payment.completed"}'
    })
    assert response.status_code == 422


def test_create_event_missing_target_url():
    response = client.post("/events", json={
        "event_type": "payment.completed",
        "payload": '{"event": "payment.completed"}'
    })
    assert response.status_code == 422


# ─── GET DELIVERIES ───────────────────────────────────────────

def test_get_deliveries_event_not_found():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.query.return_value.filter.return_value.all.return_value = []

    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/events/999/deliveries")

    app.dependency_overrides.clear()