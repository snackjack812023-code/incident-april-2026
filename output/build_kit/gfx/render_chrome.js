const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  for (const [m, w, h, bg] of [['shadow', 1080, 1920, true], ['border', 1080, 1920, true], ['mask', 1000, 700, false], ['urlmask', 1920, 1080, false]]) {
    const p = await b.newPage({ viewport: { width: w, height: h } });
    await p.goto('file://' + process.cwd() + '/chrome.html?m=' + m);
    await p.screenshot({ path: `chrome_${m}.png`, omitBackground: bg });
    await p.close();
  }
  await b.close();
})();
