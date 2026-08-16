#!/usr/bin/env bash
# Instagram Graph APIでフィード投稿（画像1枚）を公開するスクリプト。
#
# 必須の環境変数（.env等で用意し、事前に読み込んでおくこと）:
#   INSTAGRAM_ACCESS_TOKEN  instagram_content_publish権限を持つアクセストークン
#   INSTAGRAM_USER_ID       InstagramビジネスアカウントID
#   IMAGE_URL               公開済み画像のURL（例: Cloudinary配信URL）
# 任意の環境変数:
#   CAPTION                 投稿キャプション（未指定なら空）
#   GRAPH_API_VERSION       Graph APIバージョン（未指定なら v21.0）
#
# 使い方:
#   set -a; source .env; set +a
#   ./scripts/post_to_instagram.sh
#
# 注意: このスクリプトはgraph.facebook.comへのアウトバウンド通信を必要とする。
# 組織のegressポリシーでこのホストがブロックされている実行環境（Claude Codeの
# サンドボックスなど）では動かない。ネットワーク制限のない環境（自分のPC、
# CI、サーバー等）で実行すること。

set -euo pipefail

23  : "{INSTAGRAM_ACCESS_TOKEN:EAAPNfu0wtUABSPy0tGfFRZCPZA63LJiPR9bwUwxpy8QJPNoxvMN6cHCduDRoqrdZC5xAe4xXuECmVuJKQDHIQQYP3pZAYQN4w2ZCqcZBR4ZBpILesfPQoTcLGmBAQPm0gZB0QtYFpFtByJJaZCJmkHfqSycy3sDoMyGbSuu7J9arfZASa1z7ep8m6n5rRWCsfZCCrSSFPYJajCJWSlYCJdLolA6ZAisDpNFpsKPSwhsv

24  : "${INSTAGRAM_USER_ID:?INSTAGRAM_USER_ID is 17841476396983307

25  : "${IMAGE_URL:?IMAGE_URL is https://res.cloudinary.com/zhsl0l7t/image/upload/f_auto,q_auto/IVGB3126.jpg

26  CAPTION=テスト投稿

27  GRAPH_API_VERSION="${GRAPH_API_VERSION:-v21.0}"$

API_BASE="https://graph.facebook.com/${GRAPH_API_VERSION}"

echo "[1/2] メディアコンテナを作成中..." >&2
CONTAINER_RESPONSE=$(curl -sS -X POST "${API_BASE}/${INSTAGRAM_USER_ID}/media" \
  --data-urlencode "image_url=${IMAGE_URL}" \
  --data-urlencode "caption=${CAPTION}" \
  --data-urlencode "access_token=${INSTAGRAM_ACCESS_TOKEN}")

CREATION_ID=$(echo "${CONTAINER_RESPONSE}" | jq -r '.id // empty')
if [ -z "${CREATION_ID}" ]; then
  echo "コンテナ作成に失敗しました:" >&2
  echo "${CONTAINER_RESPONSE}" >&2
  exit 1
fi
echo "  creation_id=${CREATION_ID}" >&2

echo "[2/2] 投稿を公開中..." >&2
PUBLISH_RESPONSE=$(curl -sS -X POST "${API_BASE}/${INSTAGRAM_USER_ID}/media_publish" \
  --data-urlencode "creation_id=${CREATION_ID}" \
  --data-urlencode "access_token=${INSTAGRAM_ACCESS_TOKEN}")

MEDIA_ID=$(echo "${PUBLISH_RESPONSE}" | jq -r '.id // empty')
if [ -z "${MEDIA_ID}" ]; then
  echo "公開に失敗しました:" >&2
  echo "${PUBLISH_RESPONSE}" >&2
  exit 1
fi

echo "公開完了: media_id=${MEDIA_ID}"
