---
name: ig-feed-auto
description: feed-autoフォルダに置いた画像とキャプションを使い、Instagram公式APIでフィード投稿（画像1枚）を行うスキル。投稿前に必ず対象画像・キャプション・投稿先アカウントを表示し、ユーザーの明示的な承認（"Accept"）を得てから投稿する。「Instagramに投稿して」「フィード投稿のテストして」「feed-autoの中身を投稿して」などのトリガーで発動。scripts/instagram_post.py と連携する設計。
---

# Instagramフィード自動投稿スキル

## 概要

`feed-auto/` フォルダの `post-XXX.jpg` + `post-XXX.txt` のペアを、Instagram Graph API経由でフィード投稿するスキル。
投稿・運用管理の工程（企画→台本→サムネ→**投稿・運用管理**→分析→提案）に対応する。

**このスキルは実際にSNSへ投稿する操作を含む。** 誤操作・二重投稿・誤アカウントへの投稿を防ぐため、必ず以下の手順を順守すること。

## 実行手順

### STEP1｜候補確認

```bash
python scripts/instagram_post.py list
```

を実行し、投稿候補と投稿済みステータスを確認する。投稿済みのものは対象にしない。

### STEP2｜内容表示（投稿はしない）

対象を1件に絞り、

```bash
python scripts/instagram_post.py show --file <post-id>
```

を実行して、画像パス・キャプション全文・投稿先アカウント（`@username`）・実行予定時刻をユーザーに提示する。
`.env` が未設定などで認証情報がない場合は、その旨を伝え、`docs/instagram-feed-auto-setup.md` の手順を案内する。

### STEP3｜ユーザーの承認を得る

STEP2の内容をチャット上でユーザーに提示し、「この内容で投稿してよいか」を明示的に確認する。
**ユーザーから明確な承認（「Accept」「投稿してOK」等）が得られるまで、次のステップに進んではならない。** 承認を先回りして仮定しない。

### STEP4｜投稿実行

ユーザーが承認した場合のみ、

```bash
python scripts/instagram_post.py post --file <post-id> --yes
```

を実行する（`--yes` はSTEP3でチャット上の承認を既に得ているため、スクリプト側の対話プロンプトを省略する目的で使う。ユーザーの承認を代替するものではない）。

成功時は `media_id` と `permalink` を報告する。
失敗時はスクリプトが出力する日本語のエラー内容（原因・次に必要な対応）をそのままユーザーに伝える。

### STEP5｜定期実行について聞かれたら

現時点で `.github/workflows/instagram-feed-post.yml` の定期実行（毎日09:00 JST）は無効化されている。
有効化を求められた場合は、勝手に有効化せず `docs/instagram-feed-auto-setup.md` のSTEP7の手順（GitHub Secrets設定・Environment承認ゲート設定・cronコメントアウト解除）を案内し、実施してよいか確認してから進める。

## 注意点

- 投稿は画像1枚のフィード投稿のみが対象（カルーセル・リール・ストーリーズ・X/TikTokは対象外）。
- 投稿先アカウントの確認（`@username`）を省略しない。想定と違うアカウントが表示された場合は投稿を中止し、ユーザーに確認する。
- `feed-auto/posted.json` は投稿済み管理の唯一の情報源。ユーザーから明示的に依頼されない限り、内容を書き換えたり削除したりしない。
- 認証情報（`IG_ACCESS_TOKEN` 等）をチャット上に出力・要求しない。設定は `.env`（ローカル）または GitHub Secrets（本番）で行う。
