from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_reports_mock_mode():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["monday_mode"] == "mock"


def test_data_quality_endpoint_shape():
    resp = client.get("/api/data-quality")
    assert resp.status_code == 200
    body = resp.json()
    assert {"work_orders", "deals", "cross_board_notes"} <= body.keys()


def test_chat_without_message_is_rejected():
    resp = client.post("/api/chat", json={"message": "   "})
    assert resp.status_code == 400


def test_chat_without_llm_key_returns_503(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import backend.main as backend_main

    backend_main._llm = None
    backend_main._llm_error = None

    resp = client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code == 503
