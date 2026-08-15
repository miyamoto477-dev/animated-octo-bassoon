#!/usr/bin/env node
'use strict';

/**
 * feed-auto フォルダにある「画像＋キャプション」のペアを1件だけ選び、
 * Instagram Graph API 経由でフィードに投稿するスクリプト。
 * 投稿に成功したファイルは feed-auto/posted/ に移動し、二重投稿を防ぐ。
 *
 * 実行方法: node post-to-instagram.js
 * 設定方法: README.md を参照（.env の作成が必要）
 */

const fs = require('fs/promises');
const fssync = require('fs');
const path = require('path');

const SCRIPT_DIR = __dirname;
const ROOT_DIR = path.resolve(SCRIPT_DIR, '..', '..');

loadEnvFile(path.join(SCRIPT_DIR, '.env'));

const FEED_DIR = path.resolve(ROOT_DIR, process.env.FEED_AUTO_DIR || 'feed-auto');
const POSTED_DIR = path.resolve(ROOT_DIR, process.env.POSTED_DIR || path.join(FEED_DIR, 'posted'));
const LOG_DIR = path.resolve(ROOT_DIR, 'logs');
const LOCK_FILE = path.join(SCRIPT_DIR, '.post.lock');
const LOCK_STALE_MS = 30 * 60 * 1000; // 30分以上残っているロックは前回異常終了とみなす

const IMAGE_EXTS = ['.jpg', '.jpeg', '.png'];
const GRAPH_API_VERSION = process.env.GRAPH_API_VERSION || 'v21.0';
const REQUIRED_ENV = [
  'IG_BUSINESS_ACCOUNT_ID',
  'IG_ACCESS_TOKEN',
  'CLOUDINARY_CLOUD_NAME',
  'CLOUDINARY_UPLOAD_PRESET',
];

main().catch((err) => {
  log(`予期しないエラーで停止しました: ${err.stack || err.message}`);
  process.exitCode = 1;
});

async function main() {
  await fs.mkdir(FEED_DIR, { recursive: true });
  await fs.mkdir(LOG_DIR, { recursive: true });

  await acquireLock();
  try {
    const missing = REQUIRED_ENV.filter((key) => !process.env[key]);
    if (missing.length > 0) {
      throw new Error(
        `.env に未設定の項目があります: ${missing.join(', ')}（README.md の手順を確認してください）`
      );
    }

    const post = await findNextPost();
    if (!post) {
      log('投稿待ちの画像はありませんでした（処理をスキップします）。');
      return;
    }

    log(`投稿処理を開始します: ${post.imageName}`);

    const imageUrl = await uploadToCloudinary(post.imagePath);
    log(`画像を一時アップロードしました: ${imageUrl}`);

    const creationId = await createMediaContainer(imageUrl, post.caption);
    log(`メディアコンテナを作成しました: ${creationId}`);

    await waitUntilReady(creationId);

    const mediaId = await publishMedia(creationId);
    log(`Instagramへの投稿が完了しました（media_id=${mediaId}）: ${post.imageName}`);

    const moved = await movePostedFiles(post);
    log(`ファイルを posted フォルダへ移動しました: ${moved.image} / ${moved.caption}`);
  } catch (err) {
    log(`エラーが発生しました: ${err.message}`);
    log('※投稿待ちのファイルは feed-auto に残したままなので、次回の実行時に自動で再試行されます。');
    process.exitCode = 1;
  } finally {
    await releaseLock();
  }
}

async function findNextPost() {
  const entries = await fs.readdir(FEED_DIR, { withFileTypes: true });
  const images = entries
    .filter((e) => e.isFile() && IMAGE_EXTS.includes(path.extname(e.name).toLowerCase()))
    .map((e) => e.name)
    .sort((a, b) => a.localeCompare(b, 'ja'));

  for (const imageName of images) {
    const base = imageName.slice(0, imageName.length - path.extname(imageName).length);
    const captionName = `${base}.txt`;
    const captionPath = path.join(FEED_DIR, captionName);

    if (!fssync.existsSync(captionPath)) {
      log(`キャプションファイルが見つからないためスキップします: ${captionName} を用意してください`);
      continue;
    }

    const caption = (await fs.readFile(captionPath, 'utf-8')).trim();
    return {
      imageName,
      captionName,
      imagePath: path.join(FEED_DIR, imageName),
      captionPath,
      caption,
    };
  }

  return null;
}

async function uploadToCloudinary(imagePath) {
  const buffer = await fs.readFile(imagePath);
  const ext = path.extname(imagePath).toLowerCase();
  const mime = ext === '.png' ? 'image/png' : 'image/jpeg';

  const form = new FormData();
  form.append('file', new Blob([buffer], { type: mime }), path.basename(imagePath));
  form.append('upload_preset', process.env.CLOUDINARY_UPLOAD_PRESET);

  const cloudName = process.env.CLOUDINARY_CLOUD_NAME;
  const res = await fetch(`https://api.cloudinary.com/v1_1/${cloudName}/image/upload`, {
    method: 'POST',
    body: form,
  });
  const data = await parseJsonResponse(res);

  if (!res.ok) {
    throw new Error(`Cloudinaryへの画像アップロードに失敗しました: ${data.error?.message || res.statusText}`);
  }
  return data.secure_url;
}

async function createMediaContainer(imageUrl, caption) {
  const igUserId = process.env.IG_BUSINESS_ACCOUNT_ID;
  const accessToken = process.env.IG_ACCESS_TOKEN;
  const url = `https://graph.facebook.com/${GRAPH_API_VERSION}/${igUserId}/media`;
  const params = new URLSearchParams({ image_url: imageUrl, caption, access_token: accessToken });

  const res = await fetch(url, { method: 'POST', body: params });
  const data = await parseJsonResponse(res);

  if (!res.ok || data.error) {
    throw new Error(`Instagramメディアコンテナの作成に失敗しました: ${data.error?.message || res.statusText}`);
  }
  return data.id;
}

async function waitUntilReady(creationId) {
  const accessToken = process.env.IG_ACCESS_TOKEN;
  const url = `https://graph.facebook.com/${GRAPH_API_VERSION}/${creationId}?fields=status_code&access_token=${accessToken}`;

  for (let i = 0; i < 15; i++) {
    const res = await fetch(url);
    const data = await parseJsonResponse(res);

    if (data.status_code === 'FINISHED') return;
    if (data.status_code === 'ERROR') {
      throw new Error('Instagram側でメディアの処理に失敗しました（status_code=ERROR）');
    }
    await sleep(2000);
  }

  throw new Error('Instagram側のメディア処理が時間内に完了しませんでした（時間を置いて再実行してください）');
}

async function publishMedia(creationId) {
  const igUserId = process.env.IG_BUSINESS_ACCOUNT_ID;
  const accessToken = process.env.IG_ACCESS_TOKEN;
  const url = `https://graph.facebook.com/${GRAPH_API_VERSION}/${igUserId}/media_publish`;
  const params = new URLSearchParams({ creation_id: creationId, access_token: accessToken });

  const res = await fetch(url, { method: 'POST', body: params });
  const data = await parseJsonResponse(res);

  if (!res.ok || data.error) {
    throw new Error(`Instagramへの公開に失敗しました: ${data.error?.message || res.statusText}`);
  }
  return data.id;
}

async function parseJsonResponse(res) {
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`想定外の応答が返ってきました（HTTP ${res.status}）: ${text.slice(0, 200)}`);
  }
}

async function movePostedFiles(post) {
  await fs.mkdir(POSTED_DIR, { recursive: true });
  const destImage = await uniqueDestPath(POSTED_DIR, post.imageName);
  const destCaption = await uniqueDestPath(POSTED_DIR, post.captionName);
  await fs.rename(post.imagePath, destImage);
  await fs.rename(post.captionPath, destCaption);
  return { image: path.basename(destImage), caption: path.basename(destCaption) };
}

async function uniqueDestPath(dir, fileName) {
  let dest = path.join(dir, fileName);
  if (!fssync.existsSync(dest)) return dest;

  const ext = path.extname(fileName);
  const base = fileName.slice(0, fileName.length - ext.length);
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  dest = path.join(dir, `${base}_${stamp}${ext}`);
  return dest;
}

async function acquireLock() {
  if (fssync.existsSync(LOCK_FILE)) {
    const stat = fssync.statSync(LOCK_FILE);
    const ageMs = Date.now() - stat.mtimeMs;
    if (ageMs < LOCK_STALE_MS) {
      throw new Error(
        '前回の投稿処理がまだ実行中の可能性があります（.post.lock が残っています）。時間を置いて再実行してください。'
      );
    }
    log('古いロックファイルを検出したため削除して続行します。');
  }
  await fs.writeFile(LOCK_FILE, String(process.pid));
}

async function releaseLock() {
  await fs.rm(LOCK_FILE, { force: true });
}

function loadEnvFile(envPath) {
  if (!fssync.existsSync(envPath)) return;
  const content = fssync.readFileSync(envPath, 'utf-8');

  for (const rawLine of content.split('\n')) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;

    const idx = line.indexOf('=');
    if (idx === -1) continue;

    const key = line.slice(0, idx).trim();
    let value = line.slice(idx + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    if (!(key in process.env)) process.env[key] = value;
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function log(message) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${message}`);
}
