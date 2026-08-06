"""Tests for /conversation API endpoints."""

from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_chat_endpoint_basic():
    resp = client.post("/conversation/chat", json={"text": "Hello Henry", "user_id": "api-user"})
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "intent" in data


def test_history_endpoint_round_trip():
    # Send a couple of messages
    client.post("/conversation/chat", json={"text": "Hi", "user_id": "history-user"})
    client.post("/conversation/chat", json={"text": "How are you?", "user_id": "history-user"})

    resp = client.get("/conversation/history", params={"user_id": "history-user"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert data[0]["role"] == "user"


def test_ui_state_endpoint():
    resp = client.get("/conversation/ui/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_view" in data
    assert "status_text" in data
    assert "timer_state" in data
    assert "idea_view" in data
    assert "active_todo_title" in data
    assert "active_event_title" in data
