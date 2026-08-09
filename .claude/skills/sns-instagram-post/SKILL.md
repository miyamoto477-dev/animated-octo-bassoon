---
name: sns-instagram-post
description: Instagram Graph API（Content Publishing API）を使って、画像・動画・リールをInstagramアカウントに実際に投稿するスキル。「Instagramに投稿して」「APIで投稿して」「この画像を今すぐアップして」などのトリガーで発動。SNS運用管理シートの「投稿・運用管理」工程と連携する設計。
---

# Instagram Media API 投稿スキル

## 概要

企画（`sns-kikaku-30`）・台本（`sns-script-gen`）・サムネ（`sns-thumbword-gen`）で仕上げたコンテンツを、Instagram Graph API経由で実際にそのアカウントへ投稿する。
Graph APIの投稿は「①メディアコンテナ作成 → ②公開」の2段階フローになっている。動画・リールは①のあとに処理完了を待つ必要がある。

**このスキルは「今すぐ公開する」ための実行スキル。** 投稿内容そのものの企画・作成には他スキルを使い、このスキルは最後の「送信」だけを担当する。

## 事前準備｜長期アクセストークンの取得

ユーザーが持っているのがログイン直後などの**短期トークン**（有効期限1〜2時間）の場合、投稿処理の途中でトークン切れになりやすい。投稿前に、以下で**長期トークン**（約60日間有効）へ交換しておくことを勧める。

```bash
curl -G "https://graph.facebook.com/v21.0/oauth/access_token" \
  -d "grant_type=fb_exchange_token" \
  -d "client_id={APP_ID}" \
  -d "client_secret={APP_SECRET}" \
  -d "fb_exchange_token={短期トークン}"
```

- `APP_ID` / `APP_SECRET` はMeta for Developersで作成したアプリの認証情報。`APP_SECRET`はアクセストークン以上に機密性が高い（アプリ全体を乗っ取られうる）ため、`ACCESS_TOKEN`と同様にファイルへ平文保存せず、都度ユーザーに入力してもらう。
- レスポンスの `access_token` が長期トークン。以降のSTEP1〜STEP5ではこちらを使う。
- 長期トークンにも有効期限があるため、運用を継続する場合は期限が近づいたら同じ手順で再交換する。

## 事前準備｜IG User IDを調べる

「IG User ID」が分からない場合は、長期トークンで連携済みFacebookページ一覧と、各ページに紐づくInstagramビジネスアカウントIDを取得する。

```bash
curl -G "https://graph.facebook.com/v21.0/me/accounts" \
  -d "fields=id,name,instagram_business_account" \
  -d "access_token={長期アクセストークン}"
```

- レスポンスの各要素が管理しているFacebookページ。`instagram_business_account.id` が、投稿対象アカウントの **IG User ID**。
- 目的のページに `instagram_business_account` フィールド自体が含まれない場合、そのページにInstagramビジネス/クリエイターアカウントが連携されていない（Instagram側の設定でFacebookページと接続する必要がある）。
- 複数ページを管理している場合は `name` で見比べて、投稿先を取り違えないようユーザーに確認する。

## 事前に必要なもの（ユーザーに確認）

投稿を実行する前に、以下が揃っているか確認する。揃っていなければ先に質問する。

1. **Instagramアカウントの種類**：ビジネス／クリエイターアカウントであり、Facebookページに連携済みであること（個人アカウントはAPI投稿不可）
2. **IG User ID**（投稿先のInstagramアカウントのID）
3. **アクセストークン**（`instagram_basic` `instagram_content_publish` などの権限を持つ長期トークン）
4. **投稿する画像・動画のURL**（公開アクセス可能なURLであること。ローカルファイルは直接使えない）
5. **キャプション**（ハッシュタグ込みでこの時点までに確定していること）

## 実行手順

### STEP1｜投稿タイプを確認

以下のどれかをユーザーに確認する。

| タイプ | media_type パラメータ | 備考 |
| --- | --- | --- |
| 画像（フィード） | 不要（image_url指定のみ） | |
| 動画（フィード） | `REELS` または動画対応の指定 | 現行APIは動画フィードもREELSとして扱われることが多い |
| リール | `REELS` | `video_url` 必須 |
| カルーセル（複数枚） | `CAROUSEL` | 子コンテナを先に複数作成し `children` で束ねる |
| ストーリーズ | `STORIES` | 24時間で消える投稿 |

### STEP2｜メディアコンテナを作成

**画像の場合：**

```bash
curl -X POST "https://graph.facebook.com/v21.0/{IG_USER_ID}/media" \
  -d "image_url={画像URL}" \
  -d "caption={キャプション}" \
  -d "access_token={ACCESS_TOKEN}"
```

**動画・リールの場合：**

```bash
curl -X POST "https://graph.facebook.com/v21.0/{IG_USER_ID}/media" \
  -d "media_type=REELS" \
  -d "video_url={動画URL}" \
  -d "caption={キャプション}" \
  -d "access_token={ACCESS_TOKEN}"
```

レスポンスの `id` が `creation_id`（コンテナID）。これを次のSTEPで使う。

### STEP3｜（動画・リールのみ）処理完了を待つ

動画は非同期でエンコードされるため、`status_code` が `FINISHED` になるまでポーリングする。

```bash
curl -X GET "https://graph.facebook.com/v21.0/{creation_id}?fields=status_code&access_token={ACCESS_TOKEN}"
```

- `IN_PROGRESS`：数秒〜数十秒待って再確認
- `ERROR`：STEP2からやり直し。動画の形式・アスペクト比・長さの要件を確認する
- `FINISHED`：STEP4へ進む

### STEP4｜公開する

```bash
curl -X POST "https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish" \
  -d "creation_id={creation_id}" \
  -d "access_token={ACCESS_TOKEN}"
```

成功すると投稿済みメディアの `id` が返る。

### STEP5｜投稿結果を確認・報告

```bash
curl -X GET "https://graph.facebook.com/v21.0/{media_id}?fields=permalink,timestamp&access_token={ACCESS_TOKEN}"
```

取得した `permalink`（投稿URL）をユーザーに提示し、SNS運用管理シートを使っている場合は該当行の「ステータス」を `投稿済み`、「投稿日」を実行日に更新する（ユーザーに更新してよいか確認してから行う）。

## トラブルシューティング｜まずトークンの権限を確認する

投稿系のエラー（特に `OAuth`・`permission`・`authorized` を含むもの）が出た場合は、原因の切り分けとして最初にトークンの保有権限を確認する。

```bash
curl "https://graph.facebook.com/v21.0/me/permissions?access_token={ACCESS_TOKEN}"
```

レスポンスの `data` 配列に、投稿に必要な権限が **すべて `status: granted`** で含まれているかを確認する。

| 権限 | 用途 | 欠けている/declinedの場合の症状 |
| --- | --- | --- |
| `instagram_basic` | IGアカウント情報の読み取り | アカウント情報取得やコンテナ作成が失敗する |
| `instagram_content_publish` | 投稿の作成・公開 | `/media` `/media_publish` が権限エラーで失敗する（投稿系エラーの最頻出原因） |
| `pages_show_list` | 連携Facebookページの一覧取得 | IG User IDの特定に失敗する |
| `pages_read_engagement` | ページとIGアカウントの連携情報取得 | ページ⇔IGアカウントの紐付け確認が失敗する |

- `status: granted` 以外（`declined` など）になっている権限があれば、そのトークンではなく再認可（OAuth再承認）が必要。ユーザーにアプリの権限リクエスト画面からの再認可を依頼する。
- `instagram_basic` だけが確認できても、投稿には `instagram_content_publish` が別途必須なので、それが揃っているかも必ずセットで確認する。
- 全権限が `granted` なのにエラーが続く場合は、STEP2以降（画像URLの到達性、メディア形式、IG User IDの誤り等）を切り分ける。

## よくあるエラーと対処

| エラー | 原因 | 対処 |
| --- | --- | --- |
| `Invalid OAuth access token` | トークン失効・権限不足 | 長期トークンを再発行してもらう |
| `Media type not supported` | 画像/動画の形式・サイズ要件を満たしていない | 画像はJPEG推奨、動画はMP4/MOVでアスペクト比要件を確認 |
| `User not authorized to perform this action` | 個人アカウント、またはページ連携が未設定 | ビジネス/クリエイターアカウント化とページ連携を確認 |
| レート制限エラー | 投稿API呼び出し過多（1日の上限あり） | 時間を空けて再実行 |

## 注意点（セキュリティ・運用）

- **アクセストークン・APP_SECRETをファイルやメモリ（`memory/`配下等）に平文保存しない。** 実行の都度ユーザーに貼り付けてもらい、会話内でのみ使う。
- コマンド例をそのまま実行する前に、`{IG_USER_ID}` `{ACCESS_TOKEN}` `{画像URL}` `{キャプション}` を実際の値に置き換えたことをユーザーと一緒に確認してから実行する。
- 実際にAPIへリクエストを送信する（＝実アカウントに投稿される）操作なので、実行前に必ず「この内容で今すぐ投稿してよいか」をユーザーに確認する。生成しただけのcurlコマンドを提示する場合と、実際に実行する場合を混同しない。
- クライアントのアクセストークンや投稿内容を、ユーザーの許可なく外部に共有・記録しない。
- 投稿の中身（キャプション・画像・訴求内容）についての誇張・断定表現のチェックは、企画・台本段階のスキルに準じる。
