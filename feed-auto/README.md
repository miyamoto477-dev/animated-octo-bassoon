# feed-auto フォルダの使い方

Instagramフィード自動投稿の対象素材を置く場所です。
`scripts/instagram_post.py` がこのフォルダを読み取り、投稿候補を判定します。

## ファイルの置き方

1件の投稿につき、**同じ名前で拡張子違いの2ファイル**を1組として置きます。

```text
feed-auto/
  post-001.jpg   ← 投稿する画像（JPEG必須。PNG等は不可 / Instagram Graph APIの仕様）
  post-001.txt   ← キャプション本文（UTF-8テキスト。ハッシュタグも含めてそのまま使われます）
  post-002.jpg
  post-002.txt
```

- ファイル名（`post-001` の部分）が「投稿ID」になります。ID は自由に決めてよいですが、**一度使ったIDは変更しないでください**（投稿済み管理と紐づいているため）。
- 画像は1枚のみ対応（カルーセル・複数枚投稿は今回のスコープ外）。
- 画像は JPEG（`.jpg` / `.jpeg`）のみ対応です。
- キャプションファイルが無い、または空の場合はエラーとして扱われ、投稿対象になりません。

## 投稿済み管理

投稿に成功すると、このフォルダの `posted.json` に投稿IDと結果が記録されます。
**このファイルは削除しないでください。** 削除すると同じ素材が再投稿される可能性があります。

`posted.json` の中身の例：

```json
{
  "post-001": {
    "status": "posted",
    "posted_at": "2026-08-10T09:00:12+09:00",
    "media_id": "1789...",
    "permalink": "https://www.instagram.com/p/xxxxxxxxx/"
  }
}
```

## コマンド

詳しい使い方は `docs/instagram-feed-auto-setup.md` を参照してください。概要は以下の通りです。

```bash
# 投稿候補の一覧と、投稿済み/未投稿ステータスを確認する（投稿は行わない）
python scripts/instagram_post.py list

# 特定の1件について、対象画像・キャプション・投稿先アカウント・予定時刻を表示する（投稿は行わない）
python scripts/instagram_post.py show --file post-001

# 実際に投稿する（内容確認 → "Accept" と入力した場合のみ実行）
python scripts/instagram_post.py post --file post-001
```
