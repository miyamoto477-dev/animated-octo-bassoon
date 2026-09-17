"""Claude APIへの問い合わせ。

設計上のポイント:
- システムプロンプト（ペルソナ+FAQ）は毎回同じバイト列にして cache_control を付ける。
  問い合わせが続くほどキャッシュヒットし、入力コストが1/10近くまで落ちる。
  裏返すと、ここに時刻やユーザー名などの可変値を混ぜた瞬間にキャッシュは死ぬ。
- 返答は構造化出力で {reply, needs_human, reason} に固定する。
  「答えられないときに黙って作り話をする」のを防ぐのが目的で、
  needs_human が立ったら有人対応に流す。
- effort は low。FAQ応答に深い推論は要らず、LINEは応答が遅いと離脱するため。
  thinking自体は切らない（Opus 5で切ると本文に内部テキストが漏れることがある）。
"""

import json
import logging
from functools import lru_cache
from typing import Any

import anthropic

from app.config import get_settings
from app.knowledge import load_system_prompt

logger = logging.getLogger(__name__)

# LINEのテキストメッセージ上限は5,000文字。3〜4文の回答に2,000トークンあれば足りる。
MAX_TOKENS = 2000

FALLBACK_REPLY = "申し訳ありません、うまくお答えできませんでした。担当者に確認のうえ、改めてご連絡いたします。"

_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "reply": {
                "type": "string",
                "description": "LINEでそのまま送る返信本文。3〜4文以内。",
            },
            "needs_human": {
                "type": "boolean",
                "description": "FAQで答えられず有人対応に引き継ぐべきならtrue。",
            },
            "reason": {
                "type": "string",
                "description": "needs_humanがtrueのとき、運用者向けに引き継ぐ理由を1文で。",
            },
        },
        "required": ["reply", "needs_human", "reason"],
        "additionalProperties": False,
    },
}


class BotReply:
    def __init__(self, reply: str, needs_human: bool, reason: str = "") -> None:
        self.reply = reply
        self.needs_human = needs_human
        self.reason = reason


@lru_cache
def _client() -> anthropic.Anthropic:
    settings = get_settings()
    if settings.anthropic_api_key:
        return anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return anthropic.Anthropic()


def generate_reply(user_message: str, history: list[dict[str, Any]]) -> BotReply:
    """ユーザー発言と会話履歴から返信を作る。例外は投げず、必ずBotReplyを返す。"""
    settings = get_settings()
    messages = [*history, {"role": "user", "content": user_message}]

    try:
        response = _client().messages.create(
            model=settings.claude_model,
            max_tokens=MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": load_system_prompt(),
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
            output_config={"effort": "low", "format": _RESPONSE_SCHEMA},
        )
    except anthropic.BadRequestError as e:
        logger.error("リクエストが不正です: %s", e.message)
        return BotReply(FALLBACK_REPLY, needs_human=True, reason="APIリクエストエラー")
    except anthropic.AuthenticationError:
        logger.error("ANTHROPIC_API_KEY が無効です")
        return BotReply(FALLBACK_REPLY, needs_human=True, reason="APIキーが無効")
    except anthropic.RateLimitError as e:
        retry_after = e.response.headers.get("retry-after", "60")
        logger.warning("レート制限。%s秒後に再試行可能", retry_after)
        return BotReply(
            "ただいま混み合っております。少し時間をおいて、もう一度お送りいただけますか。",
            needs_human=False,
            reason="",
        )
    except anthropic.APIStatusError as e:
        logger.error("APIエラー (%s): %s", e.status_code, e.message)
        return BotReply(FALLBACK_REPLY, needs_human=True, reason="APIエラー")
    except anthropic.APIConnectionError:
        logger.error("Anthropic APIに接続できませんでした")
        return BotReply(FALLBACK_REPLY, needs_human=True, reason="ネットワークエラー")

    _log_cache_usage(response)

    if response.stop_reason == "refusal":
        category = response.stop_details.category if response.stop_details else None
        logger.warning("モデルが応答を拒否しました (category=%s)", category)
        return BotReply(FALLBACK_REPLY, needs_human=True, reason="モデルが応答を拒否")

    return parse_response(response.content)


def parse_response(content: list[Any]) -> BotReply:
    """レスポンスのcontentブロックからBotReplyを組み立てる（テストから直接叩ける）。"""
    text = next((b.text for b in content if getattr(b, "type", None) == "text"), None)
    if not text:
        logger.error("テキストブロックが返ってきませんでした")
        return BotReply(FALLBACK_REPLY, needs_human=True, reason="応答が空")

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # 構造化出力を指定しているので通常は起きないが、起きたら本文として扱う
        logger.warning("JSONとして解釈できませんでした。本文として扱います。")
        return BotReply(text.strip(), needs_human=False)

    reply = str(data.get("reply", "")).strip() or FALLBACK_REPLY
    return BotReply(
        reply=reply,
        needs_human=bool(data.get("needs_human", False)),
        reason=str(data.get("reason", "")),
    )


def _log_cache_usage(response: Any) -> None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    logger.info(
        "tokens: input=%s cache_read=%s cache_write=%s output=%s",
        usage.input_tokens,
        getattr(usage, "cache_read_input_tokens", 0),
        getattr(usage, "cache_creation_input_tokens", 0),
        usage.output_tokens,
    )
