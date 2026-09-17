"""LINE webhookの入り口。

LINEはwebhookへの応答が遅いとリトライや配信停止の対象になるので、
受け取ったら即200を返し、Claudeの呼び出しはバックグラウンドに回す。
"""

import logging

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from app import line_client
from app.brain import generate_reply
from app.config import get_settings
from app.store import get_store

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="LINE FAQ Bot")

GREETING = (
    "友だち追加ありがとうございます。\n"
    "ご質問があればこのトークにそのまま送ってください。担当が確認してお答えします。"
)
HANDOFF_NOTICE = "\n\n※こちらの件は担当者より改めてご連絡いたします。"


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature: str = Header(default=""),
) -> dict[str, str]:
    body = await request.body()
    settings = get_settings()

    if not line_client.verify_signature(body, x_line_signature, settings.line_channel_secret):
        logger.warning("署名検証に失敗しました")
        raise HTTPException(status_code=400, detail="invalid signature")

    payload = await request.json()
    for event in payload.get("events", []):
        background_tasks.add_task(handle_event, event)

    return {"status": "ok"}


def handle_event(event: dict) -> None:
    """1イベントを処理する。例外はここで止め、webhook全体を巻き込まない。"""
    try:
        event_type = event.get("type")
        if event_type == "follow":
            _safe_reply(event.get("replyToken", ""), GREETING)
            return
        if event_type != "message" or event.get("message", {}).get("type") != "text":
            # スタンプ・画像・位置情報などは今回のスコープ外
            return

        user_id = event.get("source", {}).get("userId", "")
        reply_token = event.get("replyToken", "")
        text = event["message"]["text"].strip()
        if not user_id or not reply_token or not text:
            return

        line_client.show_loading(user_id)

        store = get_store()
        result = generate_reply(text, store.history(user_id))

        message = result.reply + (HANDOFF_NOTICE if result.needs_human else "")
        _safe_reply(reply_token, message)

        store.append(user_id, "user", text)
        store.append(user_id, "assistant", result.reply)

        if result.needs_human:
            _notify_operator(user_id, text, result.reason)

    except Exception:  # noqa: BLE001 - バックグラウンドタスクなので必ず握る
        logger.exception("イベント処理に失敗しました")


def _safe_reply(reply_token: str, text: str) -> None:
    if not reply_token:
        return
    try:
        line_client.reply_text(reply_token, text)
    except Exception:  # noqa: BLE001
        logger.exception("返信に失敗しました")


def _notify_operator(user_id: str, question: str, reason: str) -> None:
    operator = get_settings().operator_user_id
    if not operator:
        return
    try:
        line_client.push_text(
            operator,
            f"【有人対応の依頼】\nユーザー: {user_id}\n質問: {question}\n理由: {reason}",
        )
    except Exception:  # noqa: BLE001
        logger.exception("運用者への通知に失敗しました")
