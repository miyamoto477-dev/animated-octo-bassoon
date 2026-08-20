# references（未取得ファイルについて）

このスキルは、配布元zip（Googleドライブ「🎁江戸飯ショート」内の `theme-to-short-video 2.zip`）から取り込みました。
取り込み時に、以下2ファイルだけがバイナリ転送の都合で取得できていません。

| 未取得ファイル | 役割 | SKILL.md での参照箇所 |
| --- | --- | --- |
| `references/production-workflow.md` | 制作フロー本体（工程・既定値・成果物チェックリスト・Imagegen→Higgsfield→Remotion手順） | 「Required First Step」で必読と指定 |
| `scripts/compose_voicevox_telop.py` | Higgsfield mp4 + VOICEVOX wav + 字幕を FFmpeg で合成する1クリップ検証／フォールバック用スクリプト | 「Core Behavior」「Required First Step」 |

## 取得方法

zip をこのチャットに直接添付してください。展開して不足分を配置します。
それまでの間、このスキルを起動した場合は次のように扱ってください。

- `production-workflow.md` は存在しない前提で、`SKILL.md` の「One-Shot Defaults」に従って進行する
- 1クリップ検証・フォールバック合成は `compose_voicevox_telop.py` を使わず、FFmpeg を直接呼ぶ

## 取り込み済みファイル（CRC照合済み）

- `SKILL.md`
- `agents/openai.yaml`
- `scripts/create_project.py`
- `scripts/generate_voicevox_audio.py`
- `scripts/start_voicevox_engine.py`
