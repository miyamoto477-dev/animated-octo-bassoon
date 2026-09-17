from app.store import ConversationStore


def test_history_round_trips():
    store = ConversationStore(max_turns=4, ttl_seconds=3600)
    store.append("U1", "user", "こんにちは")
    store.append("U1", "assistant", "こんにちは。ご質問をどうぞ。")
    assert store.history("U1") == [
        {"role": "user", "content": "こんにちは"},
        {"role": "assistant", "content": "こんにちは。ご質問をどうぞ。"},
    ]


def test_users_are_isolated():
    store = ConversationStore(max_turns=4, ttl_seconds=3600)
    store.append("U1", "user", "A")
    store.append("U2", "user", "B")
    assert store.history("U1") == [{"role": "user", "content": "A"}]


def test_history_is_trimmed_and_starts_with_user():
    store = ConversationStore(max_turns=2, ttl_seconds=3600)
    for i in range(5):
        store.append("U1", "user", f"q{i}")
        store.append("U1", "assistant", f"a{i}")
    history = store.history("U1")
    assert len(history) == 4
    assert history[0]["role"] == "user"
    assert history[-1]["content"] == "a4"


def test_history_expires():
    store = ConversationStore(max_turns=4, ttl_seconds=0)
    store.append("U1", "user", "古い発言")
    assert store.history("U1") == []
