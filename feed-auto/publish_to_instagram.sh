#!/usr/bin/env bash
# Publish one image + caption to Instagram via the Meta Graph API
# (Content Publishing API: create a media container, then publish it).
#
# Requirements:
#   - An Instagram professional (Business/Creator) account
#   - A Meta app with the instagram_content_publish permission
#   - IMAGE_URL must be a public HTTPS URL (JPEG) that Meta's servers can fetch
#     -- this script does not host the image, it only calls the API.
#
# Usage:
#   IG_USER_ID=xxxx \
#   IG_ACCESS_TOKEN=xxxx \
#   IMAGE_URL=https://example.com/test-post-2026-08-15.jpg \
#   CAPTION="テスト投稿" \
#   ./publish_to_instagram.sh
#
# Never commit real values for IG_USER_ID / IG_ACCESS_TOKEN to git.

set -euo pipefail

: "${IG_USER_ID:?Set IG_USER_ID (Instagram professional account id)}"
: "${IG_ACCESS_TOKEN:?Set IG_ACCESS_TOKEN}"
: "${IMAGE_URL:?Set IMAGE_URL to a public HTTPS JPEG url}"
CAPTION="${CAPTION:-テスト投稿}"
API_VERSION="${API_VERSION:-v21.0}"

echo "Step 1/2: creating media container..." >&2
create_response=$(curl -sS -X POST "https://graph.facebook.com/${API_VERSION}/${IG_USER_ID}/media" \
  --data-urlencode "image_url=${IMAGE_URL}" \
  --data-urlencode "caption=${CAPTION}" \
  --data-urlencode "access_token=${IG_ACCESS_TOKEN}")
echo "$create_response" >&2

creation_id=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$create_response")

echo "Step 2/2: publishing container ${creation_id}..." >&2
publish_response=$(curl -sS -X POST "https://graph.facebook.com/${API_VERSION}/${IG_USER_ID}/media_publish" \
  --data-urlencode "creation_id=${creation_id}" \
  --data-urlencode "access_token=${IG_ACCESS_TOKEN}")
echo "$publish_response" >&2

echo "$publish_response" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("Published. media id:", d.get("id", d))'
