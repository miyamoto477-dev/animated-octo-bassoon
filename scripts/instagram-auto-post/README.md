# Instagram自動投稿ツール（cron連携）

`feed-auto/` フォルダに置いた画像＋キャプションを、毎日決まった時間に1件ずつInstagramフィードへ自動投稿する仕組みです。パソコンの `cron` を使って、Claude Codeを開いていないときも自動実行されます。

## できること

- `feed-auto/` の中で最も古い（ファイル名順で先頭の）画像＋同名キャプションを1件選ぶ
- Instagramフィードに投稿する
- 投稿できたら画像・キャプションを `feed-auto/posted/` に移動する（二重投稿防止）
- 投稿待ちが0件のときは何もせず終了する
- 失敗したときはファイルを残したまま終了し、次回実行時に再試行する

## 事前に必要なもの（Instagram側の制約）

Instagramへプログラムから投稿できるのは、公式の **Instagram Graph API** 経由のみです。これには以下がすべて必要です（個人アカウントのままでは投稿できません）。

1. **Instagramアカウントを「プロアカウント（ビジネス or クリエイター）」にする**
   Instagramアプリ →設定→アカウントの種類の切り替え
2. **そのInstagramアカウントを、あなたが管理者権限を持つFacebookページに連携する**
3. **Meta for Developers（[developers.facebook.com](https://developers.facebook.com)）でアプリを作成し、以下を取得する**
   - `IG_BUSINESS_ACCOUNT_ID`：連携したInstagramアカウントのユーザーID
   - `IG_ACCESS_TOKEN`：`instagram_basic` と `instagram_content_publish` 権限を持つ長期アクセストークン（有効期限は約60日。切れたら再発行してこのあとの `.env` を更新してください）

   取得手順の詳細はMetaの公式ドキュメント「Instagram Platform > Content Publishing」を参照してください。ここは頻繁に画面が変わるため、本READMEでは項目名のみ案内します。

4. **Cloudinary（[cloudinary.com](https://cloudinary.com)）の無料アカウント**
   Instagram Graph APIは「画像ファイル」ではなく「画像の公開URL」を渡す仕様のため、投稿の直前に画像を一時的にアップロードして公開URLを作るために使います。
   - 無料登録後、ダッシュボードから `Cloud Name` を控える → `CLOUDINARY_CLOUD_NAME`
   - 「Settings → Upload → Upload presets」で新規プリセットを作成し、**Signing Mode を Unsigned** にする → そのプリセット名が `CLOUDINARY_UPLOAD_PRESET`

## セットアップ手順

### STEP1｜.env を作成する

このフォルダ（`scripts/instagram-auto-post/`）にある `.env.example` を `.env` という名前でコピーし、上記で取得した4つの値を埋めてください。

```bash
cd scripts/instagram-auto-post
cp .env.example .env
```

`.env` はgitにコミットされません（認証情報のため）。

### STEP2｜手動で1回試す

cronに登録する前に、必ず手動で1回動作確認してください。`feed-auto/` に画像＋同名キャプションのペアを1つ置いてから実行します。

```bash
# リポジトリのルートフォルダで
node scripts/instagram-auto-post/post-to-instagram.js
```

成功すると、実行ログが表示され、`feed-auto/posted/` にファイルが移動しています。Instagram側の投稿も確認してください。

Node.js のバージョンは18以上が必要です（`node --version` で確認）。

### STEP3｜cronに登録する（Mac / Linux）

ターミナルで以下を実行し、cronの編集画面を開きます。

```bash
crontab -e
```

以下の1行を追加します（`/絶対パス/このフォルダ` の部分は、実際にこのリポジトリを置いている絶対パスに書き換えてください。`pwd` コマンドで確認できます）。

```cron
0 9 * * * cd /絶対パス/このフォルダ && /usr/local/bin/node scripts/instagram-auto-post/post-to-instagram.js >> logs/instagram-auto-post.log 2>&1
```

- `0 9 * * *` は「毎日9:00」の意味です。時間を変えたい場合はこの部分を変更してください（例：`0 20 * * *` で毎日20:00）
- `/usr/local/bin/node` の部分は、ターミナルで `which node` を実行して出てきたパスに置き換えてください（Node.jsのインストール方法によってパスが異なります）
- 保存すると自動的にcronに登録されます

登録できているかは `crontab -l` で確認できます。

#### Windowsをお使いの場合

Windowsにはcronがないため、代わりに「タスクスケジューラ」を使います。「タスクの作成」→トリガーを「毎日9:00」→操作を「プログラムの開始」で `node.exe` を指定し、引数に `scripts/instagram-auto-post/post-to-instagram.js` のフルパスを指定してください。

### STEP4｜運用を始める

`feed-auto/` に画像＋キャプションのペアをどんどん置いていくだけです。ファイル名の並び順（古い順）に、1日1件ずつ自動で投稿されていきます。詳しい置き方は `feed-auto/README.md` を参照してください。

## ログの確認方法

```bash
tail -n 50 logs/instagram-auto-post.log
```

投稿の成功・失敗・スキップ理由がすべてここに記録されます。

## 制限・注意事項

- 1回のcron実行につき投稿は1件だけです（複数投稿予約ではありません）
- アクセストークン（`IG_ACCESS_TOKEN`）は約60日で失効します。失効した場合はMeta for Developersで再発行し、`.env` を更新してください
- 投稿に失敗したファイルは自動削除されません。`feed-auto/` に残り続けるので、原因をログで確認してから対応してください（キャプション内容の問題、トークン失効、画像形式などが主な原因です）
- カルーセル（複数枚投稿）・ストーリーズ・リールへの自動投稿には対応していません（フィードへの単一画像投稿のみ）
