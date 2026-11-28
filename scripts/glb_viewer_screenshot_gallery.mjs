/* Actual Chromium screenshots of the CBDK-authored synthetic GLB viewer.
 * Never use this public CI artifact workflow with private GLB-derived HTML.
 */
import assert from "node:assert/strict";
import { mkdir, writeFile, stat } from "node:fs/promises";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright";

const shots = [
  ["01-overview.png", "左右比較ビューア・初期表示"],
  ["02-orbit-zoom.png", "連動回転・ズーム後"],
  ["03-part-suggestion.png", "部品候補の確認"],
  ["04-color-filter.png", "差分フィルターを有効にした表示"],
];

async function main() {
  assert.equal(process.argv.length, 4,
    "Usage: node scripts/glb_viewer_screenshot_gallery.mjs synthetic.html new-gallery-dir");
  const fixture = resolve(process.argv[2]);
  const output = resolve(process.argv[3]);
  await stat(fixture);
  await mkdir(output, { recursive: false }); // Never overwrite old gallery.
  const browser = await chromium.launch({ headless: true });
  const errors = [], network = [];
  try {
    const page = await browser.newPage({
      viewport: { width: 1400, height: 950 },
      deviceScaleFactor: 1,
      reducedMotion: "reduce",
    });
    page.on("pageerror", error => errors.push(error.message));
    page.on("request", req => {
      if (/^https?:/i.test(req.url())) network.push(req.url());
    });
    await page.goto(pathToFileURL(fixture).href, { waitUntil: "load" });
    await page.waitForFunction(() =>
      document.querySelector("#status")?.textContent?.includes("連動視点を使用中"));
    for (const id of ["#canvas-reference", "#canvas-candidate"]) {
      assert((await page.locator(id).evaluate(el => el.toDataURL())).length > 300,
        "Actual Chromium canvas should contain rendered pixels");
    }
    await page.screenshot({ path: join(output, shots[0][0]), fullPage: true });

    await page.locator("#canvas-reference").focus();
    await page.keyboard.press("ArrowRight");
    await page.locator("#canvas-candidate").hover({ position: { x: 240, y: 190 } });
    await page.mouse.wheel(0, -350);
    await page.screenshot({ path: join(output, shots[1][0]), fullPage: true });

    await page.locator("#part-reference").selectOption("1");
    assert.equal(await page.locator("#jump-candidate").isEnabled(), true);
    await page.locator("#jump-candidate").click();
    assert.equal(await page.locator("#part-candidate").inputValue(), "2");
    await page.screenshot({ path: join(output, shots[2][0]), fullPage: true });

    await page.locator("#part-reference").selectOption("all");
    await page.locator("#part-candidate").selectOption("all");
    await page.locator("#hide-low").check();
    await page.screenshot({ path: join(output, shots[3][0]), fullPage: true });

    assert.deepEqual(errors, [], "Chromium JavaScript errors");
    assert.deepEqual(network, [], "Offline fixture attempted network access");
    const files = await Promise.all(shots.map(async ([name]) => {
      const size = (await stat(join(output, name))).size;
      assert(size > 500, "Screenshot appears empty: " + name);
      return { file: name, bytes: size };
    }));
    const manifest = {
      schema_version: 1,
      kind: "cbdk_synthetic_real_chromium_screenshot_gallery",
      synthetic_fixture_only: true,
      contains_private_user_geometry: false,
      source: "CBDK-authored local synthetic fixture",
      renderer: "actual Chromium and Canvas UI",
      network_requests: 0,
      page_errors: 0,
      screenshots: files,
    };
    await writeFile(join(output, "manifest.json"),
      JSON.stringify(manifest, null, 2) + "\n", "utf8");

    const cards = shots.map(([filename, label]) =>
      '<figure><img alt="' + label + '" loading="lazy" src="' + filename +
      '"><figcaption>' + label + '</figcaption></figure>').join("\n");
    const gallery = `<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'unsafe-inline'">
<title>CBDK / Actual Chromium UI screenshot gallery</title>
<style>body{max-width:1250px;margin:0 auto;padding:24px;background:#0d1420;color:#f3f6fb;font:16px system-ui,sans-serif}
p{color:#b9c7da;line-height:1.6}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(450px,1fr));gap:16px}
figure{margin:0;border:1px solid #344255;border-radius:12px;overflow:hidden;background:#1b2738}
img{width:100%;display:block}figcaption{padding:13px}</style></head>
<body><h1>CBDK / 実Chromiumスクリーンショット集</h1>
<p>CBDK自作の合成3Dデータを表示したオフラインGLB比較ビューアを、
CIの実Chromiumで操作・撮影したPNGです。Blender GUIのスクリーンショットではありません。
実ユーザーのGLBやアドオンの動作を証明するものではありません。</p>
<section class="grid">${cards}</section></body></html>`;
    await writeFile(join(output, "index.html"), gallery, "utf8");
    console.log("CBDK_CHROMIUM_SCREENSHOT_GALLERY_PASS " + shots.length);
  } finally {
    await browser.close();
  }
}
main().catch(err => { console.error(err); process.exitCode = 1; });
