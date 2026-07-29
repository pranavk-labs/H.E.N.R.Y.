"""Tests for GTK runtime HTTP client."""

from unittest.mock import MagicMock

from app.gtk_ui.runtime_client import RuntimeClient


def test_runtime_client_fetches_status():
    """Runtime status is fetched from the voice runtime route."""
    http = MagicMock()
    response = MagicMock()
    response.json.return_value = {"state": "stopped"}
    response.raise_for_status.return_value = None
    http.get.return_value = response
    client = RuntimeClient(api_base_url="http://testserver", http_client=http)

    assert client.get_runtime_status() == {"state": "stopped"}
    http.get.assert_called_once_with("http://testserver/voice-runtime/status")


def test_runtime_client_posts_preload_model():
    """Preload posts the selected model to the runtime API."""
    http = MagicMock()
    response = MagicMock()
    response.json.return_value = {"state": "loaded", "model": "qwen3"}
    response.raise_for_status.return_value = None
    http.post.return_value = response
    client = RuntimeClient(api_base_url="http://testserver", http_client=http)

    assert client.preload_model("qwen3")["state"] == "loaded"
    http.post.assert_called_once_with(
        "http://testserver/voice-runtime/preload", json={"model": "qwen3"}
    )
