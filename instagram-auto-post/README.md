# instagram-auto-post

Instagram Graph APIを使って「画像1枚 + 投稿文」をInstagramへ自動投稿するツールです。
プログラミング初心者・Windowsユーザー向けに、コマンドはすべてPowerShellを想定しています。

> ⚠️ アクセストークンは絶対に人に見せたり、GitHubなどへアップロードしたりしないでください。

---

## 1. 必要なもの

投稿を試す前に、以下がすべて揃っている必要があります。

1. **Node.js**（このプロジェクトを動かすための実行環境）
2. **Facebookページ** と、そのページに連携された **Instagramプロアカウント**（ビジネス or クリエイターアカウント）
3. **Meta for Developers** ( https://developers.facebook.com/ ) で作成した「アプリ」
4. アプリに対して発行した **長期アクセストークン**（`instagram_business_basic` と `instagram_business_content_publish` などの権限が必要です）
5. 投稿したい画像の **公開HTTPS URL**（Cloudinaryなど。パソコン内のファイル（`C:\Users\...`）は使えません）

### Node.jsが入っているか確認する

PowerShellを開いて、以下を入力してください。

```powershell
node --version
npm --version
```

バージョン番号（例: `v22.22.2`）が表示されればOKです。
「認識されていません」のようなエラーが出た場合は、Node.jsが入っていません。
[https://nodejs.org/](https://nodejs.org/) から **LTS版** をダウンロードしてインストールしてから、
PowerShellを一度閉じて開き直してください。

---

## 2. インストール方法

PowerShellで、このフォルダ（`instagram-auto-post`）に移動してから、以下を実行します。

```powershell
cd instagram-auto-post
npm install
```

`node_modules` フォルダが作成されれば成功です。

---

## 3. .env の設定

`.env` は、アクセストークンなど「他人に見せてはいけない情報」を保存するファイルです。
このプロジェクトにはサンプルとして `.env.example` が入っています。

```powershell
Copy-Item .env.example .env
```

作成された `.env` をメモ帳などで開き、以下を埋めてください。

```env
INSTAGRAM_ACCESS_TOKEN=（Meta for Developersで発行した長期アクセストークン）
INSTAGRAM_USER_ID=（数字のみのInstagramビジネスアカウントID）
IMAGE_URL=（投稿したい画像の公開HTTPS URL）
CAPTION=（投稿文）
GRAPH_API_VERSION=v26.0
ANTHROPIC_API_KEY=（キャプション自動生成を使う場合のみ。使わないなら空でOK）
CLAUDE_MODEL=claude-opus-5
```

`ANTHROPIC_API_KEY` は、後述の「AIキャプション自動生成」機能を使わない場合は空欄のままで構いません。

### INSTAGRAM_USER_ID の確認方法

Instagramの「ユーザーネーム」（@から始まる名前）ではなく、**数字だけのID**が必要です。
Meta for Developersの「Instagram API セットアップ」画面、または
Graph API Explorerで `me/accounts` → 該当ページ → `instagram_business_account` を辿ると確認できます。

### GRAPH_API_VERSION について

2026年8月時点の最新版は `v26.0` です。Meta のAPIバージョンは数ヶ月ごとに更新され、
古いバージョンは順次利用できなくなります。エラーが出る場合は下記ページで
最新バージョンを確認し、`.env` の値を書き換えてください（英語ページです）。

https://developers.facebook.com/docs/graph-api/changelog

`.env` は `.gitignore` に登録されているため、Gitには保存されません。

---

## 4. dry-run（お試し確認・実際には投稿されません）

いきなり本番投稿する前に、設定内容を確認できます。**この操作ではInstagramに投稿されません。**

```powershell
node instagram-post.js --dry-run
```

または

```powershell
npm run dry-run
```

以下が表示されます。

- Instagram User ID
- IMAGE_URL
- CAPTION
- API Version
- アクセストークン（先頭6文字以外はマスクされます）
- 画像URLへアクセスできるかどうかの確認結果

`.env` の値が未設定の項目は「(未設定)」と表示されます。すべて埋めてから本番投稿に進んでください。

---

## 4.5 AIキャプション自動生成（任意機能）

投稿文（キャプション）を自分で考える代わりに、Claude（Anthropic AI）に自動生成させることもできます。

### 事前準備

1. https://console.anthropic.com/ でアカウントを作成し、APIキーを発行する
2. `.env` の `ANTHROPIC_API_KEY` に、発行したAPIキーを貼り付ける（`CLAUDE_MODEL` は変更不要です）

### 使い方

```powershell
node instagram-post.js --generate-caption "今日のダイエット豆知識"
```

`"..."` の部分に、投稿のテーマ・伝えたいことを日本語で入力してください。実行すると、

1. Claudeが投稿テーマに合ったキャプション文（絵文字・ハッシュタグ付き）を生成
2. 生成結果をターミナルに表示
3. `.env` の `CAPTION` を自動的に上書き保存

まで行われます。**この時点ではまだInstagramには投稿されません。** 生成された文章を確認し、気に入らなければ表現を変えてもう一度実行できます。問題なければ、いつも通り次のステップに進んでください。

```powershell
node instagram-post.js --dry-run
node instagram-post.js
```

`memory/account-profile.md`（アカウントのジャンル・トンマナ等を記録するファイル）がプロジェクトの一つ上の階層に存在する場合、その内容も参考情報としてClaudeに渡されます。

---

## 5. 本番投稿

`.env` の内容とdry-runの結果を確認したら、以下を実行すると実際にInstagramへ投稿されます。

```powershell
node instagram-post.js
```

成功すると、以下がターミナルに表示されます。

- 投稿成功のメッセージ
- Media ID
- Permalink（投稿URL）
- 実行日時

---

## 6. よくあるエラー

エラー時は「Instagram投稿に失敗しました」だけでなく、HTTPステータス・エラーコード・原因・対処方法が
まとめて表示されます。代表的なパターンは以下の通りです。

| 症状 | 主な原因 | 対処方法 |
| --- | --- | --- |
| `error_subcode: 463` | アクセストークンの期限切れ | Meta for Developersで長期トークンを再発行し、`.env`を更新する |
| `code: 190`（上記以外） | アクセストークンが無効・コピーミス | トークンをコピーし直して`.env`を確認する |
| `code: 100` または `803` | Instagram User IDの間違い | ユーザーネームではなく数字のIDを使っているか確認する |
| `code: 10` / 権限系メッセージ | 必要な権限が付与されていない | Meta for Developersのアプリ設定で権限（パーミッション）を確認する |
| `code: 2207026` | Meta側からIMAGE_URLへアクセスできない | 画像URLがブラウザの別ウィンドウ（シークレットモード等）から誰でも開けるか確認する |
| `code: 2207001 / 2207003 / 2207020` | 画像の形式・アスペクト比の問題 | JPEG形式・アスペクト比 4:5〜1.91:1 の画像を使う |
| `code: 2500` やAPIバージョン関連メッセージ | GRAPH_API_VERSIONが古い・無効 | `.env`のバージョンを最新（例: v26.0）に更新する |
| dry-runで「画像URLの確認に失敗しました」 | URLが間違っている／非公開 | URLをブラウザで直接開いて画像が表示されるか確認する |

原因が分からないエラーが出た場合は、表示された `エラーメッセージ` と `code` / `error_subcode` の内容を
そのまま共有してください。次のステップを一緒に確認します。

---

## 今後の拡張予定

このツールは「画像1枚 + 投稿文」の投稿を確実に成功させることを目的とした最初のバージョンです。
投稿文のAI自動生成（`--generate-caption`）は実装済みです。今後、以下の機能を追加予定です。

- 複数画像の順番切り替え
- Google Sheetsから投稿情報を取得
- 指定日時での自動投稿
- 投稿済み管理
