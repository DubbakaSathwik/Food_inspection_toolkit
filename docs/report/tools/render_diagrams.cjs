// Renders every SVG in ../assets/diagrams to PNG at 2x (run: node render_diagrams.cjs from this folder).
const { chromium } = require("playwright");
const { readdirSync, readFileSync } = require("node:fs");
const { join } = require("node:path");
(async () => {
  const dir = join(__dirname, "..", "assets", "diagrams");
  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: 2 });
  for (const f of readdirSync(dir).filter((n) => n.endsWith(".svg"))) {
    const svg = readFileSync(join(dir, f), "utf8");
    const [, w, h] = svg.match(/width="(\d+)" height="(\d+)"/);
    await page.setViewportSize({ width: +w, height: +h });
    await page.setContent(`<body style="margin:0">${svg}</body>`);
    await page.screenshot({ path: join(dir, f.replace(".svg", ".png")), clip: { x: 0, y: 0, width: +w, height: +h } });
    console.log("rendered", f);
  }
  await browser.close();
})();
