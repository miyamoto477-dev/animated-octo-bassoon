"""会話履歴の保持。

プロセス内メモリ実装。デモとシングルインスタンス運用はこれで足りる。
本番で複数インスタンスに増やす／再起動をまたいで履歴を残すなら、
ConversationStore と同じインターフェースでRedis実装に差し替える。
"""

import threading
import time
from collections import defaultdict
from functools import lru_cache
from typing import Any

from app.config import get_settings


class ConversationStore:
    def __init__(self, max_turns: int, ttl_seconds: int) -> None:
        self._max_messages = max_turns * 2
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._messages: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._touched_at: dict[str, float] = {}

    def history(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            self._expire(user_id)
            return list(self._messages[user_id])

    def append(self, user_id: str, role: str, content: str) -> None:
        with self._lock:
            self._expire(user_id)
            self._messages[user_id].append({"role": role, "content": content})
            # 先頭がuserで始まるように、はみ出した分を偶数個ずつ落とす
            overflow = len(self._messages[user_id]) - self._max_messages
            if overflow > 0:
                self._messages[user_id] = self._messages[user_id][overflow + (overflow % 2):]
            self._touched_at[user_id] = time.monotonic()

    def reset(self, user_id: str) -> None:
        with self._lock:
            self._messages.pop(user_id, None)
            self._touched_at.pop(user_id, None)

    def _expire(self, user_id: str) -> None:
        last = self._touched_at.get(user_id)
        if last is not None and time.monotonic() - last > self._ttl:
            self._messages.pop(user_id, None)
            self._touched_at.pop(user_id, None)


@lru_cache
def get_store() -> ConversationStore:
    settings = get_settings()
    return ConversationStore(
        max_turns=settings.history_turns,
        ttl_seconds=settings.history_ttl_seconds,
    )
