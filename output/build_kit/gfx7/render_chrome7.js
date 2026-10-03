const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  for (const [m, w, h, transparent] of [['bgfx', 1080, 1920, true], ['ashadow', 1080, 1920, true], ['aborder', 1080, 1920, true], ['pshadow', 1080, 1920, true], ['pborder', 1080, 1920, true], ['amask', 1000, 700, false], ['pmask', 760, 817, false]]) {
    const p = await b.newPage({ viewport: { width: w, height: h } });
    await p.goto('file://' + process.cwd() + '/chrome7.html?m=' + m);
    await p.screenshot({ path: `c7_${m}.png`, omitBackground: transparent });
    await p.close();
  }
  await b.close(); console.log('chrome7 assets done');
})();
