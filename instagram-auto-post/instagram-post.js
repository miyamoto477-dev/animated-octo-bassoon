/**
 * instagram-post.js
 *
 * Instagram Graph APIを使って「画像1枚 + 投稿文」をInstagramへ投稿するスクリプト。
 *
 * 使い方:
 *   node instagram-post.js --dry-run   ... 実際には投稿せず、設定内容だけ確認する
 *   node instagram-post.js             ... 実際にInstagramへ投稿する
 */

require('dotenv').config();
const axios = require('axios');

const IS_DRY_RUN = process.argv.includes('--dry-run');
const GRAPH_API_BASE = 'https://graph.facebook.com';

// -----------------------------------------------------------------------
// 設定の読み込み
// -----------------------------------------------------------------------

function loadConfig() {
  const config = {
    accessToken: process.env.INSTAGRAM_ACCESS_TOKEN || '',
    userId: process.env.INSTAGRAM_USER_ID || '',
    imageUrl: process.env.IMAGE_URL || '',
    caption: process.env.CAPTION || '',
    apiVersion: process.env.GRAPH_API_VERSION || '',
  };

  const missing = Object.entries({
    INSTAGRAM_ACCESS_TOKEN: config.accessToken,
    INSTAGRAM_USER_ID: config.userId,
    IMAGE_URL: config.imageUrl,
    GRAPH_API_VERSION: config.apiVersion,
  })
    .filter(([, value]) => !value)
    .map(([key]) => key);

  return { config, missing };
}

// アクセストークンは先頭6文字だけ表示し、残りはマスクする
function maskToken(token) {
  if (!token) return '(未設定)';
  if (token.length <= 6) return '*'.repeat(token.length);
  return `${token.slice(0, 6)}${'*'.repeat(Math.min(token.length - 6, 20))}(先頭6文字のみ表示)`;
}

// -----------------------------------------------------------------------
// 画像URLの事前アクセス確認
// -----------------------------------------------------------------------

async function checkImageUrlAccessible(imageUrl) {
  if (!imageUrl) {
    return { ok: false, message: 'IMAGE_URLが設定されていません。' };
  }

  try {
    const url = new URL(imageUrl);
    if (url.protocol !== 'https:') {
      return {
        ok: false,
        message: `IMAGE_URLは https:// で始まる公開URLにしてください（現在: ${url.protocol}）。ローカルファイルパス（C:\\... など）は使えません。`,
      };
    }
  } catch {
    return { ok: false, message: `IMAGE_URLの形式が正しいURLではありません: ${imageUrl}` };
  }

  try {
    const res = await axios.get(imageUrl, {
      timeout: 10000,
      responseType: 'stream',
      validateStatus: () => true,
    });
    res.data.destroy(); // ボディ全体は不要なので接続を閉じる

    const contentType = res.headers['content-type'] || '';

    if (res.status < 200 || res.status >= 300) {
      return {
        ok: false,
        statusCode: res.status,
        message: `画像URLへアクセスしたところ、HTTP ${res.status} が返されました。URLが正しいか、画像が公開設定になっているか確認してください。`,
      };
    }

    if (!contentType.startsWith('image/')) {
      return {
        ok: false,
        statusCode: res.status,
        contentType,
        message: `URLにはアクセスできましたが、Content-Typeが画像ではありません（${contentType || '不明'}）。画像ファイルへの直接リンクになっているか確認してください。`,
      };
    }

    return { ok: true, statusCode: res.status, contentType };
  } catch (err) {
    return {
      ok: false,
      message: `画像URLへ接続できませんでした（${err.code || err.message}）。URLが正しいか、インターネットから誰でもアクセスできる状態か確認してください。`,
    };
  }
}

// -----------------------------------------------------------------------
// Meta APIのエラーを分かりやすく変換する
// -----------------------------------------------------------------------

function describeMetaError(code, subcode, message) {
  // 参考: https://developers.facebook.com/docs/graph-api/guides/error-handling
  // コードやサブコードはMeta側の仕様変更で追加・変更されることがあります。
  if (code === 190) {
    if (subcode === 463) {
      return {
        判別結果: 'アクセストークンの期限切れ',
        対処方法:
          'Meta for Developersのツールで新しい長期アクセストークンを再発行し、.envのINSTAGRAM_ACCESS_TOKENを更新してください。',
      };
    }
    if (subcode === 467) {
      return {
        判別結果: 'アクセストークンが無効（形式不正・失効済み）',
        対処方法:
          'トークンをコピーする際に文字が欠けていないか確認してください。改めてMeta for Developersでトークンを発行し直してください。',
      };
    }
    if (subcode === 460 || subcode === 461) {
      return {
        判別結果: 'Facebook/Instagramアカウントのパスワード変更等によりトークンが無効化されました',
        対処方法: 'Meta for Developersで新しいアクセストークンを発行し直してください。',
      };
    }
    return {
      判別結果: 'アクセストークンが無効です',
      対処方法:
        'INSTAGRAM_ACCESS_TOKENが正しくコピーされているか確認し、必要であれば新しいトークンを発行してください。',
    };
  }

  if (code === 10 || (code === 200 && /permission/i.test(message || ''))) {
    return {
      判別結果: '必要な権限（パーミッション）が不足しています',
      対処方法:
        'Meta for Developersのアプリ設定で instagram_business_basic / instagram_business_content_publish 等の権限が許可されているか確認してください。',
    };
  }

  if (code === 100) {
    return {
      判別結果: 'パラメーターが不正です（Instagram User IDや画像URLの形式間違いの可能性）',
      対処方法:
        'INSTAGRAM_USER_IDが数字のみのID（ユーザーネームではない）か、IMAGE_URLの形式が正しいか確認してください。',
    };
  }

  if (code === 803) {
    return {
      判別結果: 'Instagram User IDが間違っている可能性があります',
      対処方法:
        'Meta for Developersの「Instagram API セットアップ」画面などで正しいInstagramビジネスアカウントIDを確認してください。',
    };
  }

  if (code === 2207026) {
    return {
      判別結果: 'MetaのサーバーからIMAGE_URLへアクセスできませんでした',
      対処方法:
        '画像URLが誰でもインターネットからアクセスできる公開URLか確認してください。パスワード保護や社内ネットワーク限定のURLは使えません。',
    };
  }

  if (code === 2207003 || code === 2207001 || code === 2207020) {
    return {
      判別結果: '画像の形式・サイズがInstagramの仕様に合っていません',
      対処方法:
        'JPEG形式で、アスペクト比 4:5〜1.91:1 の範囲の画像か確認してください（PNGや極端に細長い画像は失敗しやすいです）。',
    };
  }

  if (code === 9007) {
    return {
      判別結果: 'メディアコンテナがまだ公開できる状態になっていません（処理中またはポリシー違反）',
      対処方法:
        '少し時間を置いてから再実行してください。繰り返し失敗する場合は画像の内容がInstagramの利用規約に違反していないか確認してください。',
    };
  }

  if (code === 2500 || /Unsupported (get|post) request|Unknown path components/i.test(message || '')) {
    return {
      判別結果: 'APIバージョンやエンドポイントの指定に問題がある可能性があります',
      対処方法:
        '.envのGRAPH_API_VERSIONが有効なバージョン（例: v26.0）になっているか確認してください。古いバージョンは廃止されている場合があります。',
    };
  }

  if (code === 4 || code === 17 || code === 32 || code === 613) {
    return {
      判別結果: 'APIの呼び出し回数の上限（レート制限）に達した可能性があります',
      対処方法: 'しばらく時間を置いてから再実行してください。',
    };
  }

  return {
    判別結果: '上記に当てはまらないエラーです',
    対処方法:
      'メッセージの内容を確認し、Meta for Developersのエラーリファレンスで code / error_subcode を検索してください。',
  };
}

function printMetaError(context, err) {
  console.error('');
  console.error(`Instagram投稿に失敗しました（${context}）`);
  console.error('---------------------------------------------');

  if (err.response) {
    const status = err.response.status;
    const apiError = (err.response.data && err.response.data.error) || {};
    const { message, type, code, error_subcode: errorSubcode, fbtrace_id: fbTraceId } = apiError;

    console.error(`HTTPステータス      : ${status}`);
    console.error(`Meta APIエラーコード : ${code !== undefined ? code : '(なし)'}`);
    console.error(`error_subcode       : ${errorSubcode !== undefined ? errorSubcode : '(なし)'}`);
    console.error(`エラー種別 (type)    : ${type || '(なし)'}`);
    console.error(`エラーメッセージ     : ${message || '(メッセージなし)'}`);
    if (fbTraceId) console.error(`fbtrace_id          : ${fbTraceId}`);

    const { 判別結果: verdict, 対処方法: fix } = describeMetaError(code, errorSubcode, message);
    console.error('');
    console.error(`判別結果: ${verdict}`);
    console.error(`対処方法: ${fix}`);
  } else if (err.request) {
    console.error('Meta APIサーバーへ接続できませんでした（ネットワーク・タイムアウトの可能性）。');
    console.error(`詳細: ${err.message}`);
    console.error('対処方法: インターネット接続を確認し、しばらくしてから再実行してください。');
  } else {
    console.error(`予期しないエラー: ${err.message}`);
  }
  console.error('---------------------------------------------');
}

// -----------------------------------------------------------------------
// Instagram Graph API 呼び出し
// -----------------------------------------------------------------------

async function createMediaContainer(config) {
  const url = `${GRAPH_API_BASE}/${config.apiVersion}/${config.userId}/media`;
  const res = await axios.post(url, null, {
    params: {
      image_url: config.imageUrl,
      caption: config.caption,
      access_token: config.accessToken,
    },
  });
  return res.data.id; // creation_id
}

// 画像コンテナが公開可能な状態になるまで少し待つ（通常は数秒以内に完了する）
async function waitForContainerReady(config, creationId, maxAttempts = 5) {
  const url = `${GRAPH_API_BASE}/${config.apiVersion}/${creationId}`;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const res = await axios.get(url, {
      params: { fields: 'status_code', access_token: config.accessToken },
    });
    const statusCode = res.data.status_code;

    if (statusCode === 'FINISHED') return;
    if (statusCode === 'ERROR' || statusCode === 'EXPIRED') {
      throw new Error(`メディアコンテナの処理に失敗しました（status_code: ${statusCode}）`);
    }
    // IN_PROGRESS の場合は少し待って再確認
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  // 画像投稿は通常すぐ終わるため、ここに到達しても致命的ではなくそのまま公開を試みる
}

async function publishMedia(config, creationId) {
  const url = `${GRAPH_API_BASE}/${config.apiVersion}/${config.userId}/media_publish`;
  const res = await axios.post(url, null, {
    params: {
      creation_id: creationId,
      access_token: config.accessToken,
    },
  });
  return res.data.id; // media_id
}

async function getMediaDetails(config, mediaId) {
  const url = `${GRAPH_API_BASE}/${config.apiVersion}/${mediaId}`;
  const res = await axios.get(url, {
    params: { fields: 'id,permalink,timestamp', access_token: config.accessToken },
  });
  return res.data;
}

// -----------------------------------------------------------------------
// メイン処理
// -----------------------------------------------------------------------

async function runDryRun(config, missing) {
  console.log('=== dry-run モード（Instagramへは投稿しません） ===');
  console.log('');
  console.log(`Instagram User ID : ${config.userId || '(未設定)'}`);
  console.log(`IMAGE_URL         : ${config.imageUrl || '(未設定)'}`);
  console.log(`CAPTION           : ${config.caption || '(未設定・空でも投稿は可能です)'}`);
  console.log(`API Version       : ${config.apiVersion || '(未設定)'}`);
  console.log(`ACCESS_TOKEN      : ${maskToken(config.accessToken)}`);
  console.log('');

  if (missing.length > 0) {
    console.log('⚠ 以下の環境変数が未設定です。本番投稿の前に .env に設定してください:');
    missing.forEach((key) => console.log(`  - ${key}`));
    console.log('');
  }

  if (config.imageUrl) {
    console.log('画像URLへのアクセス確認を行っています...');
    const result = await checkImageUrlAccessible(config.imageUrl);
    if (result.ok) {
      console.log(`✔ 画像URLにアクセスできました（Content-Type: ${result.contentType}）`);
    } else {
      console.log(`✘ 画像URLの確認に失敗しました: ${result.message}`);
    }
    console.log('');
  }

  console.log('dry-runはここまでです。実際の投稿は行われていません。');
}

async function runPublish(config, missing) {
  if (missing.length > 0) {
    console.error('以下の環境変数が未設定のため、投稿を中止しました:');
    missing.forEach((key) => console.error(`  - ${key}`));
    console.error('');
    console.error('.env ファイルに値を設定してから、もう一度実行してください。');
    process.exitCode = 1;
    return;
  }

  console.log('画像URLへのアクセス確認を行っています...');
  const accessCheck = await checkImageUrlAccessible(config.imageUrl);
  if (!accessCheck.ok) {
    console.error(`✘ 画像URLの事前確認に失敗しました: ${accessCheck.message}`);
    console.error('投稿を中止しました。IMAGE_URLを確認してください。');
    process.exitCode = 1;
    return;
  }
  console.log('✔ 画像URLは正常にアクセスできます。');

  let creationId;
  try {
    console.log('STEP1: メディアコンテナを作成しています...');
    creationId = await createMediaContainer(config);
    console.log(`✔ メディアコンテナを作成しました（creation_id: ${creationId}）`);
  } catch (err) {
    printMetaError('STEP1: メディアコンテナ作成', err);
    process.exitCode = 1;
    return;
  }

  try {
    console.log('コンテナの処理状況を確認しています...');
    await waitForContainerReady(config, creationId);
  } catch (err) {
    printMetaError('コンテナ状態確認', err);
    process.exitCode = 1;
    return;
  }

  let mediaId;
  try {
    console.log('STEP2: media_publishを実行しています...');
    mediaId = await publishMedia(config, creationId);
    console.log(`✔ 投稿を公開しました（media_id: ${mediaId}）`);
  } catch (err) {
    printMetaError('STEP2: media_publish', err);
    process.exitCode = 1;
    return;
  }

  try {
    console.log('STEP3: 投稿内容を確認しています...');
    const details = await getMediaDetails(config, mediaId);
    console.log('');
    console.log('=== 投稿成功 ===');
    console.log(`Media ID   : ${details.id}`);
    console.log(`Permalink  : ${details.permalink || '(取得できませんでした)'}`);
    console.log(`実行日時   : ${new Date().toLocaleString('ja-JP')}`);
  } catch (err) {
    // 公開自体は成功しているため、詳細取得の失敗は警告に留める
    console.log('');
    console.log('=== 投稿成功 ===');
    console.log(`Media ID   : ${mediaId}`);
    console.log(`実行日時   : ${new Date().toLocaleString('ja-JP')}`);
    console.log('（投稿詳細の追加取得には失敗しましたが、投稿自体は成功しています）');
  }
}

async function main() {
  const { config, missing } = loadConfig();

  if (IS_DRY_RUN) {
    await runDryRun(config, missing);
  } else {
    await runPublish(config, missing);
  }
}

main().catch((err) => {
  console.error('予期しないエラーが発生しました:', err.message);
  process.exitCode = 1;
});
