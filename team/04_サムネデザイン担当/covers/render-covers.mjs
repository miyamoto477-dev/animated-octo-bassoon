// Instagram表紙画像ジェネレーター
//   covers.config.json を読み、1080×1350（4:5）のPNGを out/ に書き出す。
//   使い方:  node render-covers.mjs
//   前提:    npm i playwright  ＋ Chromium（PLAYWRIGHT_BROWSERS_PATH 経由でも可）
import { chromium } from 'playwright';
import { readFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const cfg = JSON.parse(readFileSync(resolve(HERE, 'covers.config.json'), 'utf8'));
const OUT = resolve(HERE, 'out');
mkdirSync(OUT, { recursive: true });

const esc = s => s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
// [[…]] で囲んだ部分にマーカー（蛍光ペン）を引く
const mark = s => esc(s).replace(/\[\[(.+?)\]\]/g, '<span class="hl">$1</span>');

const artboard = p => {
  const setup = p.setup.map(esc).join('<br>');
  const body = p.layout === 'number'
    ? `<div class="numwrap"><div class="num">${esc(p.number)}</div>
         <div class="t1">${mark(p.numberTail)}</div></div>`
    : `<div class="head">${p.headline.map(l => `<span class="ln">${mark(l)}</span>`).join('')}</div>`;
  return `<div class="art ${p.format === 'story' ? 'story' : ''}" id="${p.id}">
    ${p.badge ? `<div class="qbadge">${esc(p.badge)}</div>` : ''}
    <span class="kicker"><span class="dot"></span>${esc(p.kicker)}</span>
    <div class="mid">
      <div class="setup">${setup}</div>
      ${body}
      <div class="sub"><span class="bar"></span>${esc(p.sub)}</div>
    </div>
    <div class="foot"><span class="handle">${esc(cfg.brand.handle)}</span><span class="rule"></span></div>
  </div>`;
};

const b = cfg.brand;
const html = `<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&family=Barlow+Condensed:wght@700&display=swap" rel="stylesheet">
<style>
:root{--base:${b.base};--ink:${b.ink};--muted:${b.muted};--accent:${b.accent};--accent-soft:${b.accentSoft};--line:${b.line}}
*{margin:0;padding:0;box-sizing:border-box}
body{background:#555;display:flex;flex-direction:column;gap:40px;padding:40px;align-items:flex-start}
.art{width:1080px;height:1350px;background:var(--base);position:relative;overflow:hidden;
  font-family:"Noto Sans JP",sans-serif;color:var(--ink);display:flex;flex-direction:column;padding:86px 84px 74px}
/* ストーリーズ(9:16)。上下はInstagramのUIに隠れるため余白を厚くとる */
.art.story{height:1920px;padding:330px 84px 320px}
.art::before{content:"";position:absolute;width:820px;height:820px;border-radius:50%;
  background:var(--accent-soft);opacity:.5;right:-300px;top:-280px}
.art.story::before{top:-180px}
.art.story::after{bottom:-120px}
.art.story .qbadge{top:420px}
.art::after{content:"";position:absolute;width:460px;height:460px;border-radius:50%;
  background:var(--accent-soft);opacity:.38;left:-210px;bottom:-170px}
.art > *{position:relative;z-index:1}
.kicker{display:inline-flex;align-items:center;gap:14px;align-self:flex-start;background:var(--accent);
  color:#fff;font-weight:700;font-size:31px;letter-spacing:.15em;padding:14px 30px;border-radius:100px}
.kicker .dot{width:10px;height:10px;border-radius:50%;background:#fff;opacity:.9}
.mid{flex:1;display:flex;flex-direction:column;justify-content:center;padding-bottom:26px}
.setup{font-size:44px;font-weight:500;line-height:1.6;color:var(--muted)}
.head{margin-top:40px;font-weight:900;letter-spacing:-.04em}
.head .ln{font-size:128px;line-height:1.2;white-space:nowrap;display:block;width:max-content}
.hl{position:relative;display:inline-block}
.hl::before{content:"";position:absolute;left:-8px;right:-8px;bottom:.18em;height:.30em;
  background:var(--accent-soft);z-index:-1;border-radius:3px}
.sub{margin-top:38px;display:flex;align-items:center;gap:20px;font-size:38px;font-weight:700;color:var(--accent)}
.sub .bar{width:62px;height:5px;background:var(--accent);border-radius:4px;flex:none}
.foot{display:flex;align-items:center;gap:26px}
.foot .rule{height:2px;background:var(--line);flex:1}
.foot .handle{font-size:28px;font-weight:700;letter-spacing:.09em;color:var(--muted)}
.numwrap{display:flex;align-items:baseline;gap:26px;margin-top:30px}
.num{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:300px;line-height:.72;
  color:var(--accent);letter-spacing:-.04em}
.t1{font-size:128px;font-weight:900;line-height:1.05;letter-spacing:-.04em;white-space:nowrap}
.qbadge{position:absolute;right:70px;top:210px;font-family:"Barlow Condensed",sans-serif;font-weight:700;
  font-size:290px;line-height:.8;color:var(--accent);opacity:.14;z-index:0}
</style>
${cfg.posts.map(artboard).join('\n')}`;

const browser = await chromium.launch(
  process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}
);
const page = await browser.newPage({ viewport: { width: 1300, height: 1500 } });
await page.setContent(html, { waitUntil: 'networkidle' });
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(1200);

// 品質チェック: 見出しがセーフエリア(912px)をはみ出していないか
const over = await page.evaluate(() =>
  [...document.querySelectorAll('.ln,.t1,.sub,.setup')]
    .filter(e => e.getBoundingClientRect().width > 912)
    .map(e => e.textContent.trim()));
if (over.length) console.warn('⚠ 文字が長すぎて枠からはみ出しています:', over);

for (const p of cfg.posts) {
  await page.locator('#' + p.id).screenshot({ path: `${OUT}/${p.id}.png` });
  console.log(`✓ out/${p.id}.png  — ${p.theme}`);
}
await browser.close();
