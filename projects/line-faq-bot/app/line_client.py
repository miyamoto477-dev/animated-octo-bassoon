"""LINE Messaging API との入出力。署名検証もここ。"""

import base64
import hashlib
import hmac
import logging

import httpx2 as httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

API_BASE = "https://api.line.me/v2/bot"
# LINEのテキストメッセージ上限
MAX_TEXT_LENGTH = 5000


def verify_signature(body: bytes, signature: str, channel_secret: str) -> bool:
    """X-Line-Signature を検証する。

    チャネルシークレットでリクエストボディのHMAC-SHA256を取り、Base64にしたものが
    ヘッダと一致するか見る。ここを省くと、URLさえ知られれば誰でも
    偽のイベントを投げ込めるので必須。
    """
    if not signature:
        return False
    expected = base64.b64encode(
        hmac.new(channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    ).decode("utf-8")
    # タイミング攻撃を避けるため == では比較しない
    return hmac.compare_digest(expected, signature)


def _headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.line_channel_access_token}",
        "Content-Type": "application/json",
    }


def reply_text(reply_token: str, text: str) -> None:
    """replyTokenを使って返信する（無料枠。1トークン1回きり）。"""
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text[:MAX_TEXT_LENGTH]}],
    }
    _post("/message/reply", payload)


def push_text(to: str, text: str) -> None:
    """任意のタイミングで送る（運用者への通知など。従量課金対象）。"""
    payload = {"to": to, "messages": [{"type": "text", "text": text[:MAX_TEXT_LENGTH]}]}
    _post("/message/push", payload)


def show_loading(chat_id: str, seconds: int = 20) -> None:
    """入力中アニメーションを出す。失敗しても本筋に影響しないので握りつぶす。"""
    try:
        _post("/chat/loading/start", {"chatId": chat_id, "loadingSeconds": seconds})
    except Exception:  # noqa: BLE001 - 表示上の演出なので落とさない
        logger.debug("ローディング表示に失敗しました", exc_info=True)


def _post(path: str, payload: dict) -> None:
    try:
        response = httpx.post(
            f"{API_BASE}{path}", headers=_headers(), json=payload, timeout=10.0
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        # 400はreplyTokenの期限切れ・二重使用が多い
        logger.error("LINE API %s が %s: %s", path, e.response.status_code, e.response.text)
        raise
    except httpx.HTTPError:
        logger.error("LINE API %s への接続に失敗しました", path, exc_info=True)
        raise
