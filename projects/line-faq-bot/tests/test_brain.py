"""parse_response のテスト。APIは叩かない。"""

from dataclasses import dataclass

from app.brain import FALLBACK_REPLY, parse_response


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeThinkingBlock:
    type: str = "thinking"


def test_parses_structured_reply():
    block = FakeTextBlock('{"reply": "3か月からです。", "needs_human": false, "reason": ""}')
    result = parse_response([block])
    assert result.reply == "3か月からです。"
    assert result.needs_human is False


def test_flags_handoff():
    block = FakeTextBlock(
        '{"reply": "担当者に確認します。", "needs_human": true, "reason": "個別見積もりの相談"}'
    )
    result = parse_response([block])
    assert result.needs_human is True
    assert result.reason == "個別見積もりの相談"


def test_skips_non_text_blocks():
    blocks = [FakeThinkingBlock(), FakeTextBlock('{"reply": "はい", "needs_human": false, "reason": ""}')]
    assert parse_response(blocks).reply == "はい"


def test_no_text_block_falls_back_to_human():
    result = parse_response([FakeThinkingBlock()])
    assert result.reply == FALLBACK_REPLY
    assert result.needs_human is True


def test_non_json_text_is_used_as_body():
    result = parse_response([FakeTextBlock("こんにちは")])
    assert result.reply == "こんにちは"
    assert result.needs_human is False


def test_empty_reply_falls_back():
    result = parse_response([FakeTextBlock('{"reply": "  ", "needs_human": false, "reason": ""}')])
    assert result.reply == FALLBACK_REPLY
