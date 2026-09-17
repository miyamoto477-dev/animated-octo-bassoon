"""FAQとペルソナの読み込み。

クライアントごとに差し替えるのはこの2ファイルだけで済むようにしてある。
起動時に1度だけ読み、システムプロンプトの固定プレフィックスとして使う
（毎回同じバイト列でないとプロンプトキャッシュが効かないため）。
"""

from functools import lru_cache
from pathlib import Path

from app.config import get_settings

_SYSTEM_TEMPLATE = """{persona}

## あなたに与えられたナレッジ

以下のFAQが、あなたが答えてよい内容のすべてです。

{faq}

## 回答ルール

1. 上のFAQに書かれていることだけを根拠に答える。書かれていないことは推測で埋めない。
2. FAQで答えられない質問、クレーム、見積もり・料金の個別相談、契約や解約に関わる話は、
   自分で答えずに needs_human を true にする。
3. 回答は3〜4文以内。LINEのトーク画面で読むので、箇条書きは最大3項目まで。
4. 挨拶や雑談には短く応じてよい。その場合 needs_human は false。
5. 絶対に「AIなので分かりません」とは言わない。答えられないときは
   「担当者に確認してお返事します」と伝える。
"""


@lru_cache
def load_system_prompt() -> str:
    """FAQ + ペルソナを1つのシステムプロンプトに組み立てて返す（プロセス内でキャッシュ）。"""
    settings = get_settings()
    base: Path = settings.knowledge_dir
    persona = _read(base / "persona.md")
    faq = _read(base / "faq.md")
    return _SYSTEM_TEMPLATE.format(persona=persona.strip(), faq=faq.strip())


def _read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(
            f"ナレッジファイルが見つかりません: {path}. "
            "KNOWLEDGE_DIR の設定か、ファイルの配置を確認してください。"
        )
    return path.read_text(encoding="utf-8")
