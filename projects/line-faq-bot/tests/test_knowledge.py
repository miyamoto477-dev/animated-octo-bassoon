from app.knowledge import load_system_prompt


def test_system_prompt_contains_faq_and_rules():
    prompt = load_system_prompt()
    assert "最低契約期間" in prompt          # FAQ本文が読み込まれている
    assert "一人称は「弊社」" in prompt        # ペルソナが読み込まれている
    assert "needs_human" in prompt           # 回答ルールが付与されている


def test_system_prompt_is_byte_stable():
    # 毎回同じ文字列でないとプロンプトキャッシュが効かない
    assert load_system_prompt() == load_system_prompt()
