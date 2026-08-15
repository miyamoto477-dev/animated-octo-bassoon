from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import shutil
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PENDING_DIR = BASE_DIR / "pending"
POSTED_DIR = BASE_DIR / "posted"
FAILED_DIR = BASE_DIR / "failed"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "post_log.csv"
LOCK_FILE = BASE_DIR / ".lock"
LOCK_MAX_AGE_SECONDS = 15 * 60

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
REQUIRED_ENV_VARS = ("IG_USER_ID", "ACCESS_TOKEN", "IMGBB_API_KEY")


def log(status: str, filename: str, detail: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    is_new = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "status", "filename", "detail"])
        writer.writerow([dt.datetime.now().isoformat(timespec="seconds"), status, filename, detail])


def find_next_pair() -> tuple[Path, Path] | None:
    """pending/ を名前順に見て、キャプション(.txt)が揃っている最初の画像を返す。"""
    images = sorted(
        p for p in PENDING_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )
    for image_path in images:
        caption_path = image_path.with_suffix(".txt")
        if caption_path.exists():
            return image_path, caption_path
        log("skipped", image_path.name, "対応するキャプションファイル(.txt)が見つかりません")
    return None


def acquire_lock() -> bool:
    if LOCK_FILE.exists():
        age = time.time() - LOCK_FILE.stat().st_mtime
        if age < LOCK_MAX_AGE_SECONDS:
            return False
        LOCK_FILE.unlink()
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    return True


def release_lock() -> None:
    LOCK_FILE.unlink(missing_ok=True)


def check_token_expiry(api_version: str, access_token: str, warn_days: int) -> None:
    """アクセストークンの有効期限を確認し、期限が近ければ警告するだけの補助チェック（失敗しても投稿処理は続行する）。"""
    try:
        resp = requests.get(
            f"https://graph.facebook.com/{api_version}/debug_token",
            params={"input_token": access_token, "access_token": access_token},
            timeout=15,
        )
        data = resp.json()["data"]
        if not data.get("is_valid", True):
            print("警告: アクセストークンが無効です。セットアップ手順に従って再発行してください。")
            return
        expires_at = data.get("expires_at")
        if expires_at:
            remaining_days = (dt.datetime.fromtimestamp(expires_at) - dt.datetime.now()).days
            if remaining_days <= warn_days:
                print(f"警告: アクセストークンの有効期限まで残り{remaining_days}日です。近日中に更新してください。")
    except Exception as e:
        print(f"（トークン有効期限チェックに失敗しましたが投稿処理は続行します: {e}）")


def upload_to_imgbb(image_path: Path, api_key: str) -> str:
    with image_path.open("rb") as f:
        resp = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": api_key},
            files={"image": f},
            timeout=60,
        )
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("success"):
        raise RuntimeError(f"imgbbアップロード失敗: {payload}")
    return payload["data"]["url"]


def create_media_container(api_version: str, ig_user_id: str, access_token: str, image_url: str, caption: str) -> str:
    resp = requests.post(
        f"https://graph.facebook.com/{api_version}/{ig_user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": access_token},
        timeout=30,
    )
    payload = resp.json()
    if "id" not in payload:
        raise RuntimeError(f"メディアコンテナ作成失敗: {payload}")
    return payload["id"]


def wait_until_ready(api_version: str, container_id: str, access_token: str, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        resp = requests.get(
            f"https://graph.facebook.com/{api_version}/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=15,
        )
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"メディア処理が失敗しました（status_code={status}）")
        time.sleep(3)
    raise RuntimeError("メディア処理がタイムアウトしました")


def publish_media(api_version: str, ig_user_id: str, access_token: str, container_id: str) -> str:
    resp = requests.post(
        f"https://graph.facebook.com/{api_version}/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": access_token},
        timeout=30,
    )
    payload = resp.json()
    if "id" not in payload:
        raise RuntimeError(f"投稿公開失敗: {payload}")
    return payload["id"]


def move_pair(image_path: Path, caption_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(exist_ok=True)
    shutil.move(str(image_path), str(dest_dir / image_path.name))
    shutil.move(str(caption_path), str(dest_dir / caption_path.name))


def main() -> int:
    parser = argparse.ArgumentParser(description="feed-auto/pending から1件をInstagramフィードに自動投稿する")
    parser.add_argument("--dry-run", action="store_true", help="実際には投稿せず、ファイル選択・移動の動作だけ確認する")
    args = parser.parse_args()

    for d in (PENDING_DIR, POSTED_DIR, FAILED_DIR, LOG_DIR):
        d.mkdir(exist_ok=True)

    if not acquire_lock():
        print("前回の実行がまだロック中のためスキップします（多重実行防止）。")
        return 0

    try:
        pair = find_next_pair()
        if pair is None:
            print("投稿待ちの画像はありません。")
            return 0

        image_path, caption_path = pair
        caption = caption_path.read_text(encoding="utf-8").strip()
        print(f"投稿対象: {image_path.name}")

        if args.dry_run:
            print("[dry-run] 実際のAPI呼び出しはスキップし、posted/への移動のみ行います。")
            move_pair(image_path, caption_path, POSTED_DIR)
            log("dry-run", image_path.name, "dry-runのためposted/へ移動のみ実施")
            return 0

        load_dotenv(BASE_DIR / ".env")
        missing = [k for k in REQUIRED_ENV_VARS if not os.environ.get(k)]
        if missing:
            print(
                f"エラー: feed-auto/.env に {', '.join(missing)} が設定されていません。"
                " feed-auto/.env.example を参考に設定してください（キューは消費しません）。"
            )
            return 1

        ig_user_id = os.environ["IG_USER_ID"]
        access_token = os.environ["ACCESS_TOKEN"]
        imgbb_key = os.environ["IMGBB_API_KEY"]
        api_version = os.environ.get("GRAPH_API_VERSION", "v21.0")
        warn_days = int(os.environ.get("TOKEN_EXPIRY_WARN_DAYS", "7"))

        check_token_expiry(api_version, access_token, warn_days)

        try:
            image_url = upload_to_imgbb(image_path, imgbb_key)
            container_id = create_media_container(api_version, ig_user_id, access_token, image_url, caption)
            wait_until_ready(api_version, container_id, access_token)
            media_id = publish_media(api_version, ig_user_id, access_token, container_id)
        except Exception as e:
            move_pair(image_path, caption_path, FAILED_DIR)
            (FAILED_DIR / f"{image_path.stem}.error.txt").write_text(str(e), encoding="utf-8")
            log("failed", image_path.name, str(e))
            print(f"投稿に失敗しました: {e}")
            return 1

        move_pair(image_path, caption_path, POSTED_DIR)
        log("success", image_path.name, f"media_id={media_id}")
        print(f"投稿完了: {image_path.name} (media_id={media_id})")
        return 0
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())
