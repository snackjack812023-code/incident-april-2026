// Renders every text item (work/items.json) to a transparent PNG; each item is auto-fitted to one line within maxw.
// usage: node render.js <items.json> <outdir>   -> <id>.png + meta.json {id: {w, h, margin, box_w, box_h, size}}
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const [itemsPath, outDir] = process.argv.slice(2);
  const items = JSON.parse(fs.readFileSync(itemsPath, 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 400 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'overlay.html'));
  await page.evaluate(() => document.fonts.ready);
  const M = 24, meta = {};
  for (const it of items) {
    const r = await page.evaluate((x) => window.renderItem(x), it);
    const clip = { x: Math.max(0, r.x - M), y: Math.max(0, r.y - M), width: Math.ceil(r.w + 2 * M), height: Math.ceil(r.h + 2 * M) };
    await page.screenshot({ path: path.join(outDir, it.id + '.png'), clip, omitBackground: true });
    meta[it.id] = { w: clip.width, h: clip.height, margin: M, box_w: r.w, box_h: r.h, size: r.size };
  }
  fs.writeFileSync(path.join(outDir, 'meta.json'), JSON.stringify(meta, null, 1));
  await browser.close(); console.log('rendered', items.length, 'text items');
})();
