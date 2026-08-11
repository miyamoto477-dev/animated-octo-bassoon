#!/usr/bin/env python3
"""
Instagramフィード投稿の自動化スクリプト。

feed-auto/ フォルダ内の post-XXX.jpg + post-XXX.txt のペアを対象に、
1) 投稿候補と投稿済みステータスの一覧表示 (list)
2) 投稿前の内容確認・投稿先アカウント確認 (show)
3) 承認後の実投稿 (post)
を行う。

投稿処理の流れ（post コマンド）:
  画像を公開URLとして用意（Imgurへアップロード）
  → Instagram Graph API でメディアコンテナを作成
  → メディアコンテナを公開（実投稿）
  → permalink を取得
  → feed-auto/posted.json に記録（重複投稿防止）

必要な環境変数（.env、または実行環境の環境変数）:
  IG_ACCESS_TOKEN   Instagram Graph API 用の長期アクセストークン
  IG_USER_ID        投稿先の Instagram ビジネスアカウントID
  IMGUR_CLIENT_ID   画像を一時公開するための Imgur アプリの Client ID
  EXPECTED_IG_USERNAME （任意）投稿先アカウントのユーザーネーム。設定すると取得結果と突き合わせて警告する
  GRAPH_API_VERSION （任意）既定値 v21.0
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python 3.8以下は非対応
    print("Python 3.9以上が必要です（zoneinfo未対応）。")
    sys.exit(1)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv 未インストールでも、実行環境の環境変数だけで動作できるようにする
    pass

import requests

JST = ZoneInfo("Asia/Tokyo")
FEED_DIR = Path(__file__).resolve().parent.parent / "feed-auto"
POSTED_JSON = FEED_DIR / "posted.json"
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg"}
GRAPH_API_VERSION = os.environ.get("GRAPH_API_VERSION", "v21.0")
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class JapaneseError(Exception):
    """ユーザーに日本語で表示するためのエラー。原因と次のアクションを保持する。"""

    def __init__(self, title: str, cause: str, next_steps: list[str], raw: Optional[str] = None):
        self.title = title
        self.cause = cause
        self.next_steps = next_steps
        self.raw = raw
        super().__init__(title)

    def print_report(self) -> None:
        print()
        print(f"❌ {self.title}")
        print(f"   原因: {self.cause}")
        if self.next_steps:
            print("   次に必要な対応:")
            for step in self.next_steps:
                print(f"     - {step}")
        if self.raw:
            print(f"   (詳細ログ: {self.raw})")
        print()


@dataclass
class Candidate:
    post_id: str
    image_path: Path
    caption_path: Path

    @property
    def caption(self) -> str:
        return self.caption_path.read_text(encoding="utf-8").strip()


def natural_key(text: str):
    return [int(chunk) if chunk.isdigit() else chunk for chunk in re.split(r"(\d+)", text)]


def discover_candidates() -> list[Candidate]:
    if not FEED_DIR.exists():
        raise JapaneseError(
            "feed-auto フォルダが見つかりません",
            f"{FEED_DIR} が存在しません。",
            [f"リポジトリ直下に feed-auto フォルダを作成し、post-001.jpg / post-001.txt を配置してください。"],
        )

    images = {p.stem: p for p in FEED_DIR.iterdir() if p.suffix.lower() in ALLOWED_IMAGE_EXTS.union({".png"})}
    candidates = []
    for post_id, image_path in sorted(images.items(), key=lambda kv: natural_key(kv[0])):
        caption_path = FEED_DIR / f"{post_id}.txt"
        candidates.append(Candidate(post_id=post_id, image_path=image_path, caption_path=caption_path))
    return candidates


def load_posted() -> dict:
    if not POSTED_JSON.exists():
        return {}
    try:
        return json.loads(POSTED_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise JapaneseError(
            "posted.json の読み込みに失敗しました",
            f"JSON形式が壊れています ({e})",
            ["feed-auto/posted.json の内容を確認し、壊れている場合は直前のgit履歴から復元してください。"],
        )


def save_posted(posted: dict) -> None:
    POSTED_JSON.write_text(json.dumps(posted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_candidate(candidate: Candidate) -> None:
    if candidate.image_path.suffix.lower() not in ALLOWED_IMAGE_EXTS:
        raise JapaneseError(
            "画像形式が非対応です",
            f"{candidate.image_path.name} は JPEG (.jpg/.jpeg) ではありません。Instagram Graph API はフィード画像に JPEG のみ対応しています。",
            ["画像をJPEG形式に変換してから同じファイル名（拡張子は.jpg）で置き直してください。"],
        )
    if not candidate.caption_path.exists():
        raise JapaneseError(
            "キャプションファイルがありません",
            f"{candidate.caption_path.name} が見つかりません。",
            [f"{candidate.caption_path.name} を作成し、キャプション本文を書いてください。"],
        )
    if not candidate.caption:
        raise JapaneseError(
            "キャプションが空です",
            f"{candidate.caption_path.name} の中身が空です。",
            ["キャプション本文を記入してください。"],
        )


def get_candidate(post_id: str) -> Candidate:
    for c in discover_candidates():
        if c.post_id == post_id:
            return c
    raise JapaneseError(
        "指定した投稿IDが見つかりません",
        f"'{post_id}' に対応する画像ファイルが feed-auto フォルダにありません。",
        ["`python scripts/instagram_post.py list` で候補一覧を確認してください。"],
    )


def require_env(*names: str) -> dict:
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise JapaneseError(
            "必要な認証情報が設定されていません",
            f"環境変数 {', '.join(missing)} が未設定です。",
            [
                ".env ファイル（.env.example をコピーして作成）に値を設定してください。",
                "取得手順は docs/instagram-feed-auto-setup.md を参照してください。",
            ],
        )
    return {n: os.environ[n] for n in names}


def describe_graph_error(response: requests.Response) -> JapaneseError:
    raw_text = response.text
    try:
        err = response.json().get("error", {})
    except ValueError:
        err = {}
    code = err.get("code")
    subcode = err.get("error_subcode")
    message = err.get("message", raw_text)

    if code == 190:
        return JapaneseError(
            "アクセストークンが無効です",
            "トークンの期限切れ、失効、または不正なトークンです。",
            [
                "長期アクセストークンを再発行してください（docs/instagram-feed-auto-setup.md 参照）。",
                "再発行後、.env / GitHub Secrets の IG_ACCESS_TOKEN を更新してください。",
            ],
            raw=message,
        )
    if code in (200, 10) or "permission" in str(message).lower():
        return JapaneseError(
            "投稿権限が不足しています",
            "アクセストークンに instagram_content_publish 等の必要な権限がありません。",
            [
                "Meta for Developers でアプリに instagram_content_publish / pages_show_list / pages_read_engagement の権限を追加してください。",
                "権限追加後、アクセストークンを再発行してください。",
            ],
            raw=message,
        )
    if code in (4, 17, 32, 613):
        return JapaneseError(
            "APIのレート制限に達しました",
            "短時間に多くのリクエストを送ったため制限されています。",
            ["しばらく時間を置いてから再実行してください（1時間程度が目安です）。"],
            raw=message,
        )
    if subcode == 2207001 or "media" in str(message).lower() and "fetch" in str(message).lower():
        return JapaneseError(
            "画像を取得できませんでした",
            "Instagram側が画像URLへアクセスできませんでした。非公開設定や一時的な障害の可能性があります。",
            [
                "画像の公開URLをブラウザで開いて、ログイン無しで表示できるか確認してください。",
                "Imgurのアップロードが成功しているか（URLが発行されているか）を確認してください。",
            ],
            raw=message,
        )
    if "duplicate" in str(message).lower() or subcode == 9007:
        return JapaneseError(
            "重複投稿としてブロックされました",
            "同一内容の投稿がInstagram側の重複検出に引っかかりました。",
            ["画像またはキャプションを変えるか、時間を置いてから再実行してください。"],
            raw=message,
        )
    return JapaneseError(
        "Instagram APIがエラーを返しました",
        f"想定外のエラーです（code={code}, subcode={subcode}）。",
        [
            "エラーメッセージを確認し、必要であれば Meta for Developers のエラーコード一覧で code を調べてください。",
            "解決しない場合はこのログをそのまま開発者に共有してください。",
        ],
        raw=message,
    )


def fetch_account_info(ig_user_id: str, token: str) -> dict:
    resp = requests.get(
        f"{GRAPH_API_BASE}/{ig_user_id}",
        params={"fields": "username,name", "access_token": token},
        timeout=30,
    )
    if not resp.ok:
        raise describe_graph_error(resp)
    return resp.json()


def upload_to_imgur(image_path: Path, client_id: str) -> str:
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://api.imgur.com/3/image",
                headers={"Authorization": f"Client-ID {client_id}"},
                files={"image": f},
                timeout=60,
            )
    except requests.RequestException as e:
        raise JapaneseError(
            "Imgurへの接続に失敗しました",
            str(e),
            ["ネットワーク接続を確認し、再実行してください。"],
        )

    body = {}
    try:
        body = resp.json()
    except ValueError:
        pass

    if not resp.ok or not body.get("success"):
        status = resp.status_code
        detail = (body.get("data") or {}).get("error") if body else resp.text
        if status == 403:
            raise JapaneseError(
                "Imgurの認証に失敗しました",
                "IMGUR_CLIENT_ID が不正、または無効になっています。",
                ["docs/instagram-feed-auto-setup.md を参照し、Imgur Client ID を取得し直してください。"],
                raw=str(detail),
            )
        if status == 429:
            raise JapaneseError(
                "Imgurのレート制限に達しました",
                "短時間にアップロードが集中しました。",
                ["しばらく時間を置いてから再実行してください。"],
                raw=str(detail),
            )
        raise JapaneseError(
            "Imgurへの画像アップロードに失敗しました",
            f"HTTP {status}",
            ["エラー内容を確認し、画像ファイルが壊れていないか確認してください。"],
            raw=str(detail),
        )

    return body["data"]["link"]


def create_media_container(ig_user_id: str, token: str, image_url: str, caption: str) -> str:
    resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=60,
    )
    if not resp.ok:
        raise describe_graph_error(resp)
    return resp.json()["id"]


def publish_media(ig_user_id: str, token: str, creation_id: str) -> str:
    resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    if not resp.ok:
        raise describe_graph_error(resp)
    return resp.json()["id"]


def fetch_permalink(media_id: str, token: str) -> Optional[str]:
    resp = requests.get(
        f"{GRAPH_API_BASE}/{media_id}",
        params={"fields": "permalink", "access_token": token},
        timeout=30,
    )
    if not resp.ok:
        return None
    return resp.json().get("permalink")


def print_candidate_detail(candidate: Candidate, posted: dict) -> None:
    now = datetime.now(JST)
    print("=" * 60)
    print(f"投稿ID       : {candidate.post_id}")
    print(f"画像ファイル : {candidate.image_path}")
    print(f"キャプション :")
    for line in candidate.caption.splitlines() or [""]:
        print(f"    {line}")
    print(f"現在時刻     : {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("実行予定     : 即時（テスト実行のため）")
    print("参考         : 本番稼働を有効化すると、毎日 09:00 (Asia/Tokyo) に自動実行される設定です（現時点では未有効化・GitHub Actions）")

    if candidate.post_id in posted:
        info = posted[candidate.post_id]
        print(f"ステータス   : 投稿済み ({info.get('posted_at')}) - 対象外")
    else:
        print("ステータス   : 未投稿（投稿対象）")

    ig_user_id = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_ACCESS_TOKEN")
    if ig_user_id and token:
        try:
            info = fetch_account_info(ig_user_id, token)
            username = info.get("username", "(取得不可)")
            print(f"投稿先アカウント: @{username} (name={info.get('name')}, IG_USER_ID={ig_user_id})")
            expected = os.environ.get("EXPECTED_IG_USERNAME")
            if expected and expected != username:
                print(f"⚠️ 警告: EXPECTED_IG_USERNAME ({expected}) と取得したユーザーネーム (@{username}) が一致しません。投稿先を再確認してください。")
        except JapaneseError as e:
            print("投稿先アカウント: 取得失敗")
            e.print_report()
    else:
        print("投稿先アカウント: (IG_ACCESS_TOKEN / IG_USER_ID が未設定のため確認できません)")
    print("=" * 60)


def cmd_list(_args: argparse.Namespace) -> int:
    candidates = discover_candidates()
    posted = load_posted()
    if not candidates:
        print(f"{FEED_DIR} に post-XXX.jpg / post-XXX.txt のペアが見つかりませんでした。")
        return 0

    print(f"{'投稿ID':<12} {'画像':<8} {'キャプション先頭':<24} {'ステータス'}")
    for c in candidates:
        caption_preview = "(読み込み不可)"
        issue = None
        try:
            validate_candidate(c)
            caption_preview = c.caption[:24].replace("\n", " ")
        except JapaneseError as e:
            issue = e.title

        if c.post_id in posted:
            status = f"投稿済み ({posted[c.post_id].get('posted_at', '')})"
        elif issue:
            status = f"⚠ {issue}"
        else:
            status = "未投稿"
        print(f"{c.post_id:<12} {c.image_path.suffix:<8} {caption_preview:<24} {status}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    candidate = get_candidate(args.file)
    validate_candidate(candidate)
    posted = load_posted()
    print_candidate_detail(candidate, posted)
    return 0


def pick_next_pending() -> Candidate:
    posted = load_posted()
    for c in discover_candidates():
        if c.post_id in posted:
            continue
        try:
            validate_candidate(c)
        except JapaneseError:
            continue
        return c
    raise JapaneseError(
        "投稿可能な未投稿素材がありません",
        "feed-auto フォルダの全素材が投稿済み、または不備（画像形式・キャプション未設定）です。",
        ["新しい post-XXX.jpg / post-XXX.txt を feed-auto フォルダに追加してください。"],
    )


def cmd_post(args: argparse.Namespace) -> int:
    candidate = pick_next_pending() if args.next else get_candidate(args.file)
    posted = load_posted()

    if candidate.post_id in posted:
        info = posted[candidate.post_id]
        print(f"'{candidate.post_id}' は既に投稿済みです（{info.get('posted_at')} / {info.get('permalink')}）。")
        print("同じ素材は再投稿されません。処理を中止します。")
        return 1

    validate_candidate(candidate)
    print_candidate_detail(candidate, posted)

    if args.dry_run:
        print("\n[DRY RUN] ここから先（Imgurアップロード・Instagram投稿）は実行していません。")
        return 0

    if not args.yes:
        answer = input('\n上記の内容で投稿します。よろしければ "Accept" と入力してください: ').strip()
        if answer != "Accept":
            print("承認が得られなかったため、投稿を中止しました。")
            return 1

    env = require_env("IG_ACCESS_TOKEN", "IG_USER_ID", "IMGUR_CLIENT_ID")
    token = env["IG_ACCESS_TOKEN"]
    ig_user_id = env["IG_USER_ID"]
    imgur_client_id = env["IMGUR_CLIENT_ID"]

    print("\n1/4 画像をImgurへアップロード中...")
    image_url = upload_to_imgur(candidate.image_path, imgur_client_id)
    print(f"   公開URL: {image_url}")

    print("2/4 Instagramメディアコンテナを作成中...")
    creation_id = create_media_container(ig_user_id, token, image_url, candidate.caption)
    print(f"   creation_id: {creation_id}")

    print("3/4 Instagramへ公開中...")
    media_id = publish_media(ig_user_id, token, creation_id)
    print(f"   media_id: {media_id}")

    print("4/4 permalinkを取得中...")
    permalink = fetch_permalink(media_id, token)

    posted[candidate.post_id] = {
        "status": "posted",
        "posted_at": datetime.now(JST).isoformat(),
        "media_id": media_id,
        "permalink": permalink,
    }
    save_posted(posted)

    print("\n✅ 投稿が完了しました。")
    print(f"   media_id : {media_id}")
    print(f"   permalink: {permalink}")
    print(f"   feed-auto/posted.json に記録し、'{candidate.post_id}' は今後の投稿対象から除外されます。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Instagramフィード投稿自動化")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="投稿候補と投稿済みステータスの一覧を表示する")

    p_show = sub.add_parser("show", help="投稿前の内容（画像・キャプション・予定時刻・投稿先アカウント）を表示する")
    p_show.add_argument("--file", required=True, help="投稿ID（例: post-001）")

    p_post = sub.add_parser("post", help="承認フローを経て実際に投稿する")
    target_group = p_post.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--file", help="投稿ID（例: post-001）")
    target_group.add_argument("--next", action="store_true", help="未投稿の中から最も古い1件を自動選択する（定期実行向け）")
    p_post.add_argument("--yes", action="store_true", help='対話プロンプトを省略する（人間の承認は別途取得済みであることが前提）')
    p_post.add_argument("--dry-run", action="store_true", help="内容確認までを行い、実際のアップロード・投稿は行わない")

    args = parser.parse_args()

    try:
        if args.command == "list":
            return cmd_list(args)
        if args.command == "show":
            return cmd_show(args)
        if args.command == "post":
            return cmd_post(args)
    except JapaneseError as e:
        e.print_report()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
