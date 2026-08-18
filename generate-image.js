#!/usr/bin/env node
/**
 * Gemini でInstagram投稿向けの画像を生成し、PNGとして images/ に保存する。
 *
 * 使い方:
 *   GEMINI_API_KEY=xxx node generate-image.js "白背景で湯気の立つラテのミニマルな写真"
 *   node generate-image.js --prompt "..." --count 3
 *
 * 仕様（デフォルト）:
 *   - モデル : gemini-3.1-flash-image
 *   - 比率   : 4:5（Instagramフィードの縦長）
 *   - 解像度 : 1K
 *   - 保存先 : images/（ファイル名は自動生成）
 */

import { GoogleGenAI } from '@google/genai';
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const DEFAULTS = {
  model: process.env.GEMINI_IMAGE_MODEL || 'gemini-3.1-flash-image',
  aspectRatio: '4:5',
  imageSize: '1K',
  outputDir: 'images',
  count: 1,
};

/** Instagramフィード向けの共通指示。ユーザーのプロンプトに毎回付与する。 */
const INSTAGRAM_STYLE_GUIDE = [
  'Instagramのフィード投稿用の1枚画像として構図してください。',
  '縦長4:5のフレームいっぱいに主題を配置し、上下端は文字入れ用に少し余白を残す。',
  'スマートフォンの小さい画面でも一目で伝わる、コントラストのはっきりした構図。',
  '画像内に文字・ロゴ・透かしは入れない。',
].join(' ');

function printUsage() {
  console.log(`
使い方:
  node generate-image.js "<プロンプト>" [オプション]

オプション:
  -p, --prompt <text>   生成プロンプト（位置引数でも指定可）
  -n, --count <num>     生成枚数（デフォルト: ${DEFAULTS.count}）
  -o, --out <dir>       出力フォルダ（デフォルト: ${DEFAULTS.outputDir}）
  -m, --model <name>    使用モデル（デフォルト: ${DEFAULTS.model}）
      --aspect <ratio>  アスペクト比（デフォルト: ${DEFAULTS.aspectRatio}）
      --size <1K|2K|4K> 解像度（デフォルト: ${DEFAULTS.imageSize}）
      --raw             Instagram向けの共通指示を付けず、プロンプトをそのまま使う
  -h, --help            このヘルプを表示

環境変数:
  GEMINI_API_KEY        Google AI Studio のAPIキー（必須）
  GEMINI_IMAGE_MODEL    使用モデルの上書き（任意）
`);
}

function parseArgs(argv) {
  const options = { ...DEFAULTS, raw: false, help: false };
  const positional = [];

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    const next = () => {
      const value = argv[++i];
      if (value === undefined) throw new Error(`${arg} には値が必要です`);
      return value;
    };

    switch (arg) {
      case '-p': case '--prompt': options.prompt = next(); break;
      case '-n': case '--count': options.count = Number(next()); break;
      case '-o': case '--out': options.outputDir = next(); break;
      case '-m': case '--model': options.model = next(); break;
      case '--aspect': options.aspectRatio = next(); break;
      case '--size': options.imageSize = next(); break;
      case '--raw': options.raw = true; break;
      case '-h': case '--help': options.help = true; break;
      default:
        if (arg.startsWith('-')) throw new Error(`不明なオプション: ${arg}`);
        positional.push(arg);
    }
  }

  if (!options.prompt && positional.length > 0) options.prompt = positional.join(' ');
  if (!Number.isInteger(options.count) || options.count < 1) {
    throw new Error('--count には1以上の整数を指定してください');
  }
  return options;
}

/** ファイル名に使えない文字を落とし、プロンプト先頭から短いスラッグを作る。 */
function slugify(text) {
  const slug = text
    .replace(/[\p{Cc}\p{Cf}\\/:*?"<>|.]+/gu, '')
    .replace(/\s+/gu, '-')
    .replace(/^-+|-+$/gu, '')
    .slice(0, 24);
  return slug || 'image';
}

function timestamp(date = new Date()) {
  const p = (n, len = 2) => String(n).padStart(len, '0');
  return (
    `${date.getFullYear()}${p(date.getMonth() + 1)}${p(date.getDate())}` +
    `-${p(date.getHours())}${p(date.getMinutes())}${p(date.getSeconds())}`
  );
}

/** 既存ファイルと衝突しないファイル名を決める。 */
async function uniquePath(dir, baseName) {
  for (let suffix = 0; ; suffix++) {
    const name = suffix === 0 ? `${baseName}.png` : `${baseName}-${suffix}.png`;
    const filePath = path.join(dir, name);
    try {
      await fs.access(filePath);
    } catch {
      return filePath;
    }
  }
}

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

/** レスポンスから画像パートを取り出す。画像が無ければ理由を添えて投げる。 */
function extractImageParts(response) {
  const blockReason = response.promptFeedback?.blockReason;
  if (blockReason) {
    throw new Error(`プロンプトがブロックされました (${blockReason})`);
  }

  const candidate = response.candidates?.[0];
  const parts = candidate?.content?.parts ?? [];
  const images = parts.filter((part) => part.inlineData?.data);

  if (images.length === 0) {
    const text = parts.map((part) => part.text).filter(Boolean).join('\n').trim();
    const reason = candidate?.finishReason ? ` (finishReason: ${candidate.finishReason})` : '';
    throw new Error(`画像が返りませんでした${reason}${text ? `\nモデルの応答: ${text}` : ''}`);
  }
  return images;
}

/** 一時的なエラー（429 / 5xx）は指数バックオフで再試行する。 */
async function withRetry(fn, { attempts = 4 } = {}) {
  for (let attempt = 1; ; attempt++) {
    try {
      return await fn();
    } catch (error) {
      const status = error?.status ?? error?.code;
      const retryable = status === 429 || (typeof status === 'number' && status >= 500);
      if (!retryable || attempt >= attempts) throw error;
      const waitMs = 2000 * 2 ** (attempt - 1);
      console.warn(`  一時的なエラー (${status})。${waitMs / 1000}秒後に再試行します…`);
      await new Promise((resolve) => setTimeout(resolve, waitMs));
    }
  }
}

async function main() {
  // .env があれば読み込む（無ければ環境変数だけを使う）
  try {
    process.loadEnvFile(path.join(process.cwd(), '.env'));
  } catch {
    // .env は任意
  }

  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(`エラー: ${error.message}`);
    printUsage();
    process.exitCode = 1;
    return;
  }

  if (options.help || !options.prompt) {
    if (!options.help) console.error('エラー: プロンプトを指定してください。\n');
    printUsage();
    process.exitCode = options.help ? 0 : 1;
    return;
  }

  const apiKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (!apiKey) {
    console.error('エラー: 環境変数 GEMINI_API_KEY が設定されていません（.env.example を参照）。');
    process.exitCode = 1;
    return;
  }

  const outputDir = path.resolve(options.outputDir);
  await fs.mkdir(outputDir, { recursive: true });

  const ai = new GoogleGenAI({ apiKey });
  const prompt = options.raw
    ? options.prompt
    : `${options.prompt}\n\n${INSTAGRAM_STYLE_GUIDE}`;

  console.log(`モデル: ${options.model} / 比率: ${options.aspectRatio} / 解像度: ${options.imageSize}`);
  console.log(`プロンプト: ${options.prompt}`);
  console.log(`出力先: ${outputDir}\n`);

  const savedPaths = [];
  const slug = slugify(options.prompt);

  for (let i = 1; i <= options.count; i++) {
    console.log(`[${i}/${options.count}] 生成中…`);

    const response = await withRetry(() =>
      ai.models.generateContent({
        model: options.model,
        contents: prompt,
        config: {
          responseModalities: ['IMAGE'],
          imageConfig: {
            aspectRatio: options.aspectRatio,
            imageSize: options.imageSize,
          },
        },
      }),
    );

    const images = extractImageParts(response);

    for (const [index, part] of images.entries()) {
      const buffer = Buffer.from(part.inlineData.data, 'base64');
      if (!buffer.subarray(0, 8).equals(PNG_SIGNATURE)) {
        console.warn(
          `  警告: PNG以外の形式が返りました (${part.inlineData.mimeType ?? '不明'})。そのまま .png として保存します。`,
        );
      }

      const seq = String(i).padStart(2, '0') + (images.length > 1 ? `-${index + 1}` : '');
      const baseName = `ig-4x5-${timestamp()}-${slug}-${seq}`;
      const filePath = await uniquePath(outputDir, baseName);
      await fs.writeFile(filePath, buffer);
      savedPaths.push(filePath);
      console.log(`  保存: ${path.relative(process.cwd(), filePath)} (${(buffer.length / 1024).toFixed(0)} KB)`);
    }
  }

  console.log(`\n完了: ${savedPaths.length}枚を保存しました。`);
}

main().catch((error) => {
  console.error(`\n失敗: ${error.message}`);
  process.exitCode = 1;
});
