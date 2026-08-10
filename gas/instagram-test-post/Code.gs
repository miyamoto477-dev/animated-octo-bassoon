/**
 * GAS → Instagram Graph API テスト投稿スクリプト
 * 対象アカウント: @manami01052025
 *
 * 事前準備（スクリプトエディタ →「プロジェクトの設定」→「スクリプト プロパティ」に設定）:
 *   IG_USER_ID     : 投稿先InstagramビジネスアカウントのユーザーID（数字）
 *   ACCESS_TOKEN   : instagram_content_publish 権限を持つMetaの長期アクセストークン
 *   TEST_IMAGE_URL : 投稿するテスト画像の公開URL（Instagram側から直接フェッチできる必要あり）
 *
 * 使い方:
 *   1. Google Apps Scriptの新規プロジェクトにこのファイルを貼り付ける
 *   2. 上記3つのスクリプトプロパティを設定する
 *   3. postTestImageToInstagram を実行する
 *
 * 注意:
 *   実行すると実際に @manami01052025 のフィードに公開投稿されます。
 *   テスト用画像・キャプションであることを確認してから実行してください。
 */

const GRAPH_API_VERSION = 'v21.0';

function postTestImageToInstagram() {
  const props = PropertiesService.getScriptProperties();
  const igUserId = props.getProperty('IG_USER_ID');
  const accessToken = props.getProperty('ACCESS_TOKEN');
  const imageUrl = props.getProperty('TEST_IMAGE_URL');

  if (!igUserId || !accessToken || !imageUrl) {
    throw new Error('スクリプトプロパティ IG_USER_ID / ACCESS_TOKEN / TEST_IMAGE_URL を設定してください。');
  }

  verifyAccount_(igUserId, accessToken);

  const creationId = createMediaContainer_(igUserId, accessToken, imageUrl);
  Logger.log('メディアコンテナ作成完了: creationId=%s', creationId);

  const mediaId = publishMedia_(igUserId, accessToken, creationId);
  Logger.log('投稿完了: mediaId=%s', mediaId);

  return mediaId;
}

/** 投稿先アカウントが @manami01052025 であることを確認してから進める */
function verifyAccount_(igUserId, accessToken) {
  const url = `https://graph.facebook.com/${GRAPH_API_VERSION}/${igUserId}?fields=username&access_token=${encodeURIComponent(accessToken)}`;
  const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  const body = JSON.parse(res.getContentText());

  if (res.getResponseCode() !== 200) {
    throw new Error(`アカウント確認に失敗しました: ${res.getContentText()}`);
  }
  Logger.log('投稿先アカウント: @%s (ID: %s)', body.username, igUserId);

  if (body.username !== 'manami01052025') {
    throw new Error(
      `想定外のアカウントです。期待値: manami01052025 / 実際: ${body.username}。IG_USER_ID を確認してください。`
    );
  }
}

/** Step1: メディアコンテナを作成（この時点ではまだ公開されない） */
function createMediaContainer_(igUserId, accessToken, imageUrl) {
  const url = `https://graph.facebook.com/${GRAPH_API_VERSION}/${igUserId}/media`;
  const payload = {
    image_url: imageUrl,
    caption: 'テスト投稿（GAS連携確認用）',
    access_token: accessToken
  };
  const res = UrlFetchApp.fetch(url, {
    method: 'post',
    payload: payload,
    muteHttpExceptions: true
  });
  const body = JSON.parse(res.getContentText());

  if (res.getResponseCode() !== 200 || !body.id) {
    throw new Error(`メディアコンテナの作成に失敗しました: ${res.getContentText()}`);
  }
  return body.id;
}

/** Step2: 作成したコンテナを公開投稿する */
function publishMedia_(igUserId, accessToken, creationId) {
  const url = `https://graph.facebook.com/${GRAPH_API_VERSION}/${igUserId}/media_publish`;
  const payload = {
    creation_id: creationId,
    access_token: accessToken
  };
  const res = UrlFetchApp.fetch(url, {
    method: 'post',
    payload: payload,
    muteHttpExceptions: true
  });
  const body = JSON.parse(res.getContentText());

  if (res.getResponseCode() !== 200 || !body.id) {
    throw new Error(`投稿の公開に失敗しました: ${res.getContentText()}`);
  }
  return body.id;
}
