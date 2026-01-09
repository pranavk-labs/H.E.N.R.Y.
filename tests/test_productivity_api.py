"""Tests for productivity API endpoints (Pomodoro + Ideas)."""

from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_pomodoro_lifecycle():
    """Start, pause, resume, complete a Pomodoro session via API."""
    # Start
    resp = client.post(
        "/productivity/pomodoro/start",
        json={"work_duration_minutes": 1, "break_duration_minutes": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["id"]
    assert data["status"] == "running"

    # Pause
    resp = client.post(f"/productivity/pomodoro/{session_id}/pause")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"

    # Resume
    resp = client.post(f"/productivity/pomodoro/{session_id}/resume")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"

    # Complete
    resp = client.post(f"/productivity/pomodoro/{session_id}/complete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


def test_idea_crud_and_search():
    """Basic CRUD and search for ideas via API."""
    # Create
    resp = client.post(
        "/productivity/ideas",
        json={"text": "Test idea about productivity", "tags": ["test", "prod"]},
    )
    assert resp.status_code == 200
    idea = resp.json()
    idea_id = idea["id"]
    assert idea["text"].startswith("Test idea")

    # Get
    resp = client.get(f"/productivity/ideas/{idea_id}")
    assert resp.status_code == 200

    # Update
    resp = client.put(
        f"/productivity/ideas/{idea_id}",
        json={"text": "Updated test idea"},
    )
    assert resp.status_code == 200
    assert resp.json()["text"] == "Updated test idea"

    # Search
    resp = client.get("/productivity/ideas/search", params={"q": "updated"})
    assert resp.status_code == 200
    results = resp.json()
    assert any(r["id"] == idea_id for r in results)

    # Delete
    resp = client.delete(f"/productivity/ideas/{idea_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


