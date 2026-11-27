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
        # уточнение и выбор подразделения - один вопрос, и он с ответом
        assert stats["totals"]["questions"] == 1
        assert stats["totals"]["answered"] == 1


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


def test_quality_mailbox_demo_reply(app: tuple[Container, MemoryMailbox]) -> None:
    with client(app) as http:
        profile = {"name": "Иван", "email": "ivan@corp.test", "department": "alpha"}
        conv = http.post("/api/conversations", json={"profile": profile}).json()["id"]
        r = http.post(
            f"/api/conversations/{conv}/messages",
            json={"text": "Компенсируют ли такси в командировке в выходной день?"},
        ).json()
        assert r["kind"] == "not_found"
        sent = http.post(f"/api/conversations/{conv}/options", json={"option_id": "escalate"}).json()
        code = sent["ticket"]["code"]
        threads = http.get("/api/admin/mail").json()
        assert threads["demo"] is True
        assert threads["threads"][0]["code"] == code
        res = http.post(
            "/api/admin/mail/reply",
            json={"ticket_code": code, "sender": "quality@corp.test", "body": "Компенсируется по согласованию с РП."},
        )
        assert res.status_code == 200
        msgs = http.get("/api/admin/mail").json()["threads"][0]["messages"]
        assert [m["direction"] for m in msgs][:2] == ["out", "in"]
