from __future__ import annotations

from fastapi.testclient import TestClient

from reglament_agent.adapters.mail import MemoryMailbox
from reglament_agent.api.app import create_app
from reglament_agent.container import Container


def client(app_fixture: tuple[Container, MemoryMailbox]) -> TestClient:
    c, _ = app_fixture
    settings = c.settings.model_copy(update={"mail_poll_seconds": 0, "rate_limit_per_minute": 100})
    return TestClient(create_app(settings, container=c))


def test_chat_flow_and_document_anchor(app: tuple[Container, MemoryMailbox]) -> None:
    with client(app) as http:
        assert http.get("/api/health").json()["status"] == "ok"
        conv = http.post("/api/conversations", json={"profile": {"name": "Иван", "email": "i@corp.test"}}).json()["id"]
        r = http.post(
            f"/api/conversations/{conv}/messages", json={"text": "Как часто РП обновляет реестр рисков?"}
        ).json()
        assert r["kind"] == "clarify"
        r2 = http.post(f"/api/conversations/{conv}/options", json={"option_id": "dep:alpha"}).json()
        assert r2["kind"] == "answer"
        doc = http.get("/api/documents/alpha-doc").text
        assert 'id="2.1"' in doc
        assert http.post(f"/api/turns/{r2['turn_id']}/rating", json={"rating": 1}).json() == {"status": "ok"}
        stats = http.get("/api/admin/analytics").json()
        assert stats["totals"]["questions"] == 2


def test_webhook_channel_keeps_dialog(app: tuple[Container, MemoryMailbox]) -> None:
    with client(app) as http:
        user = {"name": "Иван", "email": "i@corp.test"}
        r = http.post(
            "/api/channels/webhook",
            json={"chat_id": "42", "user": user, "text": "Как часто РП обновляет реестр рисков?"},
        ).json()
        assert any(b["id"] == "dep:beta" for b in r["buttons"])
        r2 = http.post("/api/channels/webhook", json={"chat_id": "42", "user": user, "option_id": "dep:beta"}).json()
        assert "Бета" in r2["text"]


def test_validation_and_unknown_conversation(app: tuple[Container, MemoryMailbox]) -> None:
    with client(app) as http:
        assert http.post("/api/conversations/nope/messages", json={"text": "?"}).status_code == 404
        assert http.post("/api/conversations/nope/messages", json={"text": ""}).status_code == 422
