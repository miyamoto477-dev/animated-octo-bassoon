# Instagramフィード自動投稿 セットアップ手順

対象スクリプト：`scripts/instagram_post.py`
対象フォルダ：`feed-auto/`（置き方は `feed-auto/README.md` を参照）

この機能は以下の3段階で使います。

1. **ローカルで動作確認**（このドキュメントのSTEP1〜5）
2. **テスト投稿を1件、承認した上で実行**（STEP6）
3. **（後日）毎日09:00 JSTの定期実行を有効化**（STEP7、今回は実施しません）

---

## 事前に必要なもの

- あなたが管理者権限を持つ Instagram アカウント（ビジネス or クリエイターアカウント）
- そのInstagramアカウントにリンク済みのFacebookページ（すでにお持ちとのことです）
- Facebookページの管理者権限

---

## STEP1｜Metaアプリを作成する

1. https://developers.facebook.com/apps/ にアクセスし、Facebookアカウントでログインします。
2. 「アプリを作成」→ 種類は「ビジネス」を選択します。
3. アプリ名を入力して作成します（例：「〇〇 Instagram自動投稿」）。
4. 作成したアプリのダッシュボードで「製品を追加」から **Instagram** を追加します。

## STEP2｜Instagram Graph API のアクセストークンを取得する

1. https://developers.facebook.com/tools/explorer/ を開きます。
2. 右上でSTEP1で作ったアプリを選択します。
3. 「User or Page」で自分のユーザーを選び、以下の権限にチェックを入れます。
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
4. 「Generate Access Token」を押し、Facebookログイン画面で権限を許可します。
5. 発行された **短期トークン** をコピーします（これはこのあとSTEP3で長期トークンに変換します）。

### 短期トークンを長期トークン（60日）に変換する

ブラウザまたはターミナルで以下のURLにアクセスします（`{app-id}` `{app-secret}` はMetaアプリのダッシュボード「設定 > ベーシック」から取得、`{short-lived-token}` はSTEP2-5で取得したもの）。

```text
https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id={app-id}&client_secret={app-secret}&fb_exchange_token={short-lived-token}
```

返ってきた `access_token` が **長期アクセストークン**（有効期限約60日）です。これを `IG_ACCESS_TOKEN` として使います。

> ⚠️ 60日ごとに期限が切れます。期限が切れるとエラーになるので、定期的に再発行してください（同じ手順で再取得できます）。

## STEP3｜投稿先の Instagram ビジネスアカウントID（IG_USER_ID）を確認する

1. まず自分のFacebookページIDを確認します。Graph API Explorerで以下を実行します（アクセストークンはSTEP2のもの）。

   ```text
   GET /me/accounts
   ```

   レスポンスの `data[].id` が Facebookページ ID です。運用したいアカウントのページを探します。

2. 次に、そのページIDに紐づく Instagram ビジネスアカウントIDを確認します。

   ```text
   GET /{page-id}?fields=instagram_business_account
   ```

   レスポンスの `instagram_business_account.id` が **`IG_USER_ID`** です。

3. 念のため、そのIDが正しいアカウントか確認します。

   ```text
   GET /{ig-user-id}?fields=username,name
   ```

   `username` が投稿したいInstagramアカウントと一致することを必ず確認してください。

## STEP4｜Imgurの Client ID を取得する（画像の公開URL用）

Instagram Graph APIはローカル画像を直接アップロードできず、「インターネット上の公開URL」を要求します。
このスクリプトでは、投稿のたびに画像を一時的にImgurへアップロードし、そのURLをInstagramに渡します。

1. https://api.imgur.com/oauth2/addclient にアクセスします（Imgurアカウントが必要。なければ無料で作成）。
2. Application name を入力（例：「feed-auto-uploader」）。
3. Authorization type は **「Anonymous usage without user authorization」** を選択します。
4. Email 等を入力して送信すると **Client ID** が発行されます。これが `IMGUR_CLIENT_ID` です。

> 補足：Imgurへアップロードした画像は、リンクを知っている人なら誰でも閲覧できる状態になります（Imgur上で検索には出ません）。この点に問題がなければこの方法で進めます。気になる場合は自前の画像ホスティング（S3等）への切り替えも可能なので、その際は教えてください。

## STEP5｜ローカルで設定・動作確認する

```bash
cd scripts
pip install -r requirements.txt
cd ..
cp .env.example .env
```

`.env` を開き、STEP2〜4で取得した値を入力します。

```text
IG_ACCESS_TOKEN=（STEP2で取得した長期トークン）
IG_USER_ID=（STEP3で取得したID）
IMGUR_CLIENT_ID=（STEP4で取得したClient ID）
EXPECTED_IG_USERNAME=（投稿したいアカウントのユーザーネーム。任意だが設定推奨）
```

投稿対象の画像・キャプションを `feed-auto/` に置きます（`feed-auto/README.md` 参照）。

まずは投稿せずに確認します。

```bash
# 候補一覧と投稿済みステータスを確認
python scripts/instagram_post.py list

# 特定の1件の内容・投稿先アカウントを確認（投稿はしない）
python scripts/instagram_post.py show --file post-001

# 投稿処理の流れだけ確認する（実際のアップロード・投稿はしない）
python scripts/instagram_post.py post --file post-001 --dry-run
```

`show` の出力で「投稿先アカウント」に表示される `@username` が、想定しているアカウントと一致するかを必ず確認してください。

## STEP6｜テスト投稿を1件、承認のうえ実行する

内容に問題がなければ、以下を実行します。

```bash
python scripts/instagram_post.py post --file post-001
```

対象画像・キャプション・投稿先アカウントが表示された後、確認プロンプトが出ます。
問題なければ `Accept` と入力してください（それ以外を入力した場合は投稿されません）。

成功すると `feed-auto/posted.json` に記録され、以降 `post-001` は投稿対象から自動的に除外されます。
失敗した場合は、原因と次に必要な対応が日本語で表示されます。

---

## STEP7｜（後日）毎日09:00 JSTの定期実行を有効化する手順

**今回はここまで実施しません。** テスト投稿が成功し、本番運用を開始する準備ができたら、以下の手順で有効化してください。

### 7-1. GitHub Secretsを設定する

リポジトリの `Settings > Secrets and variables > Actions` で以下を登録します。

- `IG_ACCESS_TOKEN`
- `IG_USER_ID`
- `IMGUR_CLIENT_ID`
- `EXPECTED_IG_USERNAME`（任意）

### 7-2. ワークフローの実行権限を確認する

`Settings > Actions > General > Workflow permissions` で
**「Read and write permissions」** が選択されていることを確認してください
（`posted.json` の更新をワークフローがコミット・pushするために必要です）。

### 7-3. 承認ゲート（Environment）を作成する

`Settings > Environments > New environment` で `instagram-posting` という名前の Environment を作成し、
**Required reviewers** に自分自身（またはレビューしてほしい人）を追加します。

これにより、9:00になってジョブが起動しても、承認するまで実際の投稿は実行されません（スマホからでも承認できます）。
**この設定をしないまま定期実行を有効化すると、無承認で自動投稿されてしまうため、必ず先に設定してください。**

### 7-4. 定期実行を有効にする

`.github/workflows/instagram-feed-post.yml` の以下の部分のコメントを外します。

```yaml
  schedule:
    - cron: "0 0 * * *"   # 毎日 00:00 UTC = 09:00 JST
```

これで、毎日09:00 JSTにジョブが起動し（未投稿の中から最も古い1件を自動選択）、承認ゲートで一時停止し、承認後に投稿されるようになります。

### 7-5. 手動でテスト実行したい場合

`Actions` タブ → `Instagram Feed Post` → `Run workflow` から、いつでも手動実行できます（`post_id` を空欄にすると自動選択、`dry_run` を `true` にすると投稿せず内容確認のみ行います）。

---

## トラブルシューティング

- **`アクセストークンが無効です` と出る**：60日の有効期限切れの可能性が高いです。STEP2の手順で再発行し、`.env` / GitHub Secrets を更新してください。
- **`投稿権限が不足しています` と出る**：Metaアプリの権限設定（`instagram_content_publish` 等）を確認し、トークンを再発行してください。
- **`画像を取得できませんでした` と出る**：Imgurへのアップロードが失敗している可能性があります。`IMGUR_CLIENT_ID` を確認してください。
- **同じ素材が再投稿されるか心配**：`feed-auto/posted.json` に記録済みの投稿IDは自動的に対象外になります。このファイルは削除しないでください。
