# LINE FAQボット（AIチャットボット構築代行の案件テンプレート）

企業のLINE公式アカウントに、Claudeで動くFAQ一次対応ボットを付けるためのテンプレート。
そのままポートフォリオのデモとして動かせるし、クライアント案件のたびに
`knowledge/` の2ファイルを差し替えるだけで別業種に転用できる。

## 何をするボットか

1. ユーザーがLINEに質問を送る
2. `knowledge/faq.md` の範囲で答えられるなら答える
3. 答えられない質問（個別見積もり、クレーム、契約の相談など）は**勝手に答えず**、
   「担当者より改めてご連絡します」と返し、運用者のLINEに通知を飛ばす

3番が案件として売れる理由そのもの。「AIが適当を言って炎上する」が発注側の最大の不安なので、
答えない設計を先に作ってある。

## セットアップ

### 1. LINE側

1. [LINE Developers](https://developers.line.biz/) でプロバイダーを作る
2. **Messaging API** チャネルを作成
3. 「チャネル基本設定」から **チャネルシークレット** を控える
4. 「Messaging API設定」から **チャネルアクセストークン（長期）** を発行して控える
5. 同じ画面で「応答メッセージ」を**オフ**、「Webhook」を**オン**にする
   （応答メッセージがオンだと定型文とボットの返信が二重に飛ぶ）

### 2. Anthropic側

[Anthropic Console](https://console.anthropic.com/) でAPIキーを発行する。

### 3. ローカルで起動

```bash
cd projects/line-faq-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # 控えた値を書き込む
uvicorn app.main:app --reload --port 8000
```

別ターミナルで外部から届くURLを作る（開発時のみ）:

```bash
ngrok http 8000
```

出てきた `https://xxxx.ngrok-free.app/webhook` を、
LINE Developers の「Webhook URL」に登録して「検証」を押す。成功すればつながっている。

### 4. 動作確認

チャネルのQRコードから自分で友だち追加して、`knowledge/faq.md` にある質問を送ってみる。
次に、FAQにない質問（「うちの場合いくらですか」など）を送って、
担当者に引き継ぐ文言が返ってくるか確認する。ここが一番のデモポイント。

## テスト

```bash
python3 -m pytest tests/ -q
```

署名検証・会話履歴・応答パース・webhookの受け口を、外部APIを叩かずに検証する。
Claude APIとLINE APIへの実通信は含まないので、APIキーなしで走る。

## クライアント案件への転用

差し替えるのは基本この2ファイルだけ:

| ファイル | 中身 |
| --- | --- |
| `knowledge/faq.md` | 回答範囲そのもの。ここに無いことは答えない |
| `knowledge/persona.md` | 口調・一人称・禁止表現 |

ヒアリングでは「よくある問い合わせを30件出してください」と依頼するのが早い。
それを `faq.md` の形式に整えるところまでが実質の作業で、単価の根拠になる部分。

## 設計メモ（読まなくても動くが、触る前に読むと事故らない）

- **署名検証は消さない。** `X-Line-Signature` を検証しないと、URLを知られた時点で
  誰でも偽イベントを投げ込める。`app/line_client.py:verify_signature`
- **webhookは即200を返す。** Claudeの応答を待ってから返すとLINE側がタイムアウトし、
  リトライや配信停止の対象になる。処理はバックグラウンドに逃がしてある。
- **システムプロンプトは毎回同じバイト列にする。** FAQをキャッシュさせて入力コストを下げているので、
  ここに時刻やユーザー名など毎回変わる値を混ぜるとキャッシュが丸ごと無効になる。
  ログの `cache_read` が常に0なら、それを疑う。
- **返答は構造化出力で固定。** `{reply, needs_human, reason}` を強制することで、
  「答えられないのに答えてしまう」経路を塞いでいる。
- **モデルは `.env` の `CLAUDE_MODEL` で変えられる。** 既定は `claude-opus-5`。
  問い合わせ量が多くコストを抑えたいクライアントには `claude-sonnet-5` や
  `claude-haiku-4-5` に落とす選択肢がある（回答品質は必ず実際のFAQで比較してから決める）。
- **会話履歴はプロセス内メモリ。** 再起動で消える。インスタンスを増やすなら
  `app/store.py` の `ConversationStore` と同じインターフェースでRedis実装に差し替える。

## デプロイ

常時起動のサーバーが要る。Render / Railway / Cloud Run あたりが手軽。

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

環境変数（`.env` の中身）をデプロイ先の設定画面に登録し、
払い出されたURL + `/webhook` をLINEのWebhook URLに再登録する。
`/healthz` を死活監視に使える。

**APIキーは絶対にリポジトリに入れない。** `.env` はコミットしないこと。
