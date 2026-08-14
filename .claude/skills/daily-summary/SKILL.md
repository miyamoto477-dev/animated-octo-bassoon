---
name: daily-summary
description: 今日のtodos・各部署の動きをまとめて、明日への引き継ぎを作るスキル。「今日のまとめ作って」「1日まとめ」などのトリガーで発動。夜の振り返りで使う想定。
---

# 1日まとめスキル

## 概要

夜の振り返りで使うスキル。今日の運用結果をまとめて、明日への引き継ぎを作る。

## 実行手順

### STEP1｜todosを確認

`todos/YYYY-MM-DD.md`（今日の日付）があれば、完了タスクと未完了タスクを抽出する。ファイルが無ければ、今日の会話履歴から拾う。

### STEP2｜リサーチ部の動き

`employees/research/daily/YYYY-MM-DD.md` があれば要約する。

### STEP3｜クリエイティブ部の動き

`employees/creative/feed/` `employees/creative/stories/` `employees/creative/logs/` の今日更新分を整理する。

### STEP4｜コミュニティ部の動き

`employees/community/comments/YYYY-MM-DD.md` `employees/community/dm/YYYY-MM-DD.md` があれば件数を集計する。

### STEP5｜マーケティング部の動き

`employees/marketing/` 配下の今日更新分（あれば）を確認する。

### STEP6｜まとめを作成

以下の形式でまとめる。

```text
# YYYY-MM-DD 1日まとめ
## 完了タスク
## 未完了タスク（明日に持ち越し）
## 各部署の動き
## 明日の優先事項
```

### STEP7｜保存

`reviews/YYYY-MM-DD.md` に保存する。

## 注意点

- 情報が無い部署は「動きなし」と正直に書く。無理に埋めない
