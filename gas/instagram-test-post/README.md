# GAS → Instagram Graph API テスト投稿

`Code.gs` は、Google Apps Script（GAS）から Instagram Graph API を叩いて、指定アカウントのフィードに画像を1枚投稿するスクリプトです。
対象: `@manami01052025`

## このスクリプトでできないこと

- **Claude（このリポジトリのAIアシスタント）は、このスクリプトを代わりに実行できません。**
  GASの実行にはユーザー自身のGoogleアカウント、Metaアクセストークンが必要で、実際に投稿すると `@manami01052025` のフィードに公開されます。実行は必ずユーザー自身が行ってください。
- Instagram Graph APIは画像を直接アップロードできません。`image_url` に**インターネット上から直接フェッチ可能な公開URL**を指定する必要があります（ローカルファイルの直接投稿は不可）。

## 事前準備

### 1. Instagramアカウントの要件

- `@manami01052025` が **Instagramビジネス/クリエイターアカウント** であること
- そのアカウントが **Facebookページに連携**されていること（Graph APIはFacebookページ経由でのみアクセス可能）

### 2. Meta側の設定

1. [Meta for Developers](https://developers.facebook.com/) でアプリを作成
2. 製品として「Instagram Graph API」を追加
3. 以下の権限を持つアクセストークンを取得（Graph API Explorer、または System User トークン推奨）
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
4. 短期トークンは [長期トークンに交換](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived) しておく（有効期限が短いとGASの定期実行で失敗する）

### 3. IG_USER_ID の取得

```
GET https://graph.facebook.com/v21.0/me/accounts?access_token={ACCESS_TOKEN}
```

で連携しているFacebookページIDを確認し、

```
GET https://graph.facebook.com/v21.0/{PAGE_ID}?fields=instagram_business_account&access_token={ACCESS_TOKEN}
```

で `instagram_business_account.id` を取得する。これが `IG_USER_ID`。

### 4. テスト画像の公開URLを用意

Google Driveの共有リンクはリダイレクトの都合で失敗することがあるため、以下のいずれかを推奨:
- GitHub（publicリポジトリのraw URL）
- Cloudinary / imgur などの画像ホスティング
- Google Cloud Storage の公開バケット

## GASへの設置手順

1. [script.google.com](https://script.google.com/) で新規プロジェクトを作成
2. `Code.gs` の中身をエディタに貼り付け
3. 「プロジェクトの設定」→「スクリプト プロパティ」で以下を追加
   - `IG_USER_ID`
   - `ACCESS_TOKEN`
   - `TEST_IMAGE_URL`
4. 関数 `postTestImageToInstagram` を選択して実行
5. 初回実行時はGASの外部アクセス許可（`UrlFetchApp` の利用）を承認する
6. 実行ログ（表示 → ログ）で `投稿完了: mediaId=...` が出れば成功

## 実行時の挙動

1. `IG_USER_ID` のアカウント名を取得し、`manami01052025` と一致するか確認（不一致なら投稿せず中断）
2. メディアコンテナを作成（`POST /{ig-user-id}/media`）
3. コンテナを公開投稿（`POST /{ig-user-id}/media_publish`）

いずれかのステップでエラーが出た場合、Graph APIからのエラーメッセージがそのまま例外として表示されます。
