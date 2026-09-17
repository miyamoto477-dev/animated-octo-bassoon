"""環境変数の読み込み。値の検証はここに集約する。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    line_channel_secret: str
    line_channel_access_token: str
    anthropic_api_key: str = ""  # 空ならSDKが環境変数/プロファイルから解決する

    claude_model: str = "claude-opus-5"
    operator_user_id: str = ""
    knowledge_dir: Path = Path("knowledge")

    # 1ユーザーあたり保持する会話ターン数（user+assistantで1ターン）
    history_turns: int = 8
    # 履歴を破棄するまでの無操作時間（秒）
    history_ttl_seconds: int = 60 * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
