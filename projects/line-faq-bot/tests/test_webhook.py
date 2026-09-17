"""webhookの受け口のテスト。LINE APIとClaude APIは差し替える。"""

import base64
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app import main
from app.brain import BotReply

SECRET = "test-channel-secret"


def _post(client, payload: dict, signature: str | None = None):
    body = json.dumps(payload).encode()
    if signature is None:
        signature = base64.b64encode(
            hmac.new(SECRET.encode(), body, hashlib.sha256).digest()
        ).decode()
    return client.post("/webhook", content=body, headers={"X-Line-Signature": signature})


@pytest.fixture
def sent(monkeypatch):
    """送信されたLINEメッセージを記録し、外部通信を止める。"""
    records: list[tuple[str, str]] = []
    monkeypatch.setattr(main.line_client, "reply_text", lambda token, text: records.append((token, text)))
    monkeypatch.setattr(main.line_client, "show_loading", lambda *a, **k: None)
    monkeypatch.setattr(main.line_client, "push_text", lambda *a, **k: None)
    main.get_store().reset("U123")
    return records


def _text_event(text: str) -> dict:
    return {
        "events": [
            {
                "type": "message",
                "replyToken": "RT1",
                "source": {"userId": "U123"},
                "message": {"type": "text", "text": text},
            }
        ]
    }


def test_replies_and_records_history(monkeypatch, sent):
    monkeypatch.setattr(main, "generate_reply", lambda m, h: BotReply("3か月からです。", False))
    client = TestClient(main.app)

    response = _post(client, _text_event("最低契約期間は？"))

    assert response.status_code == 200
    assert sent == [("RT1", "3か月からです。")]
    assert main.get_store().history("U123") == [
        {"role": "user", "content": "最低契約期間は？"},
        {"role": "assistant", "content": "3か月からです。"},
    ]


def test_handoff_appends_notice(monkeypatch, sent):
    monkeypatch.setattr(
        main, "generate_reply", lambda m, h: BotReply("確認いたします。", True, "個別見積もり")
    )
    client = TestClient(main.app)

    _post(client, _text_event("うちの場合いくらになりますか"))

    assert main.HANDOFF_NOTICE in sent[0][1]
    # 引き継ぎ文言は履歴に残さない（次ターンの文脈を汚さないため）
    assert main.get_store().history("U123")[-1]["content"] == "確認いたします。"


def test_invalid_signature_is_rejected(sent):
    client = TestClient(main.app)
    response = _post(client, _text_event("こんにちは"), signature="wrong")
    assert response.status_code == 400
    assert sent == []


def test_follow_event_sends_greeting(sent):
    client = TestClient(main.app)
    _post(client, {"events": [{"type": "follow", "replyToken": "RT1", "source": {"userId": "U123"}}]})
    assert sent == [("RT1", main.GREETING)]


def test_non_text_message_is_ignored(sent):
    client = TestClient(main.app)
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "RT1",
                "source": {"userId": "U123"},
                "message": {"type": "sticker", "packageId": "1"},
            }
        ]
    }
    _post(client, payload)
    assert sent == []
