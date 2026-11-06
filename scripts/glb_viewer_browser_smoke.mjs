/* Real Chromium smoke test of GLB-020 viewer, with CBDK-only synthetic data. */
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright";

async function run() {
  assert.equal(process.argv.length, 3, "Pass one synthetic HTML fixture path");
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
    const errors = [];
    const network = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("request", (req) => {
      if (/^https?:/i.test(req.url())) network.push(req.url());
    });
    await page.goto(pathToFileURL(resolve(process.argv[2])).href, { waitUntil: "load" });
    await page.waitForFunction(() => document.getElementById("status")?.textContent.includes("連動視点を使用中"));
    assert.equal(await page.locator("#part-reference option").count(), 3);
    assert.equal(await page.locator("#part-candidate option").count(), 3);
    assert.match(await page.locator("#part-reference option").nth(1).innerText(), /境界辺3/);
    assert.equal(await page.locator("#jump-candidate").isDisabled(), true);

    const images = async () => await page.evaluate(() => [
      document.querySelector("#canvas-reference").toDataURL(),
      document.querySelector("#canvas-candidate").toDataURL(),
    ]);
    const initial = await images();
    assert(initial.every((s) => s.length > 300), "Both canvases must render");

    // Keyboard orbit must redraw both canvases from a single camera state.
    await page.locator("#canvas-reference").focus();
    await page.keyboard.press("ArrowRight");
    const rotated = await images();
    assert.notEqual(rotated[0], initial[0], "Reference canvas did not rotate");
    assert.notEqual(rotated[1], initial[1], "Candidate canvas did not rotate");

    // Shared wheel zoom changes both canvases.
    await page.locator("#canvas-candidate").hover({ position: { x: 240, y: 190 } });
    await page.mouse.wheel(0, -350);
    const zoomed = await images();
    assert.notEqual(zoomed[0], rotated[0], "Reference canvas did not zoom");
    assert.notEqual(zoomed[1], rotated[1], "Candidate canvas did not zoom");

    // A match recommendation must *not* select a candidate automatically.
    await page.locator("#part-reference").selectOption("1");
    assert.equal(await page.locator("#part-candidate").inputValue(), "all");
    assert.equal(await page.locator("#jump-candidate").isEnabled(), true);
    assert.match(await page.locator("#match-hint").innerText(), /推定候補/);
    assert.match(await page.locator("#match-hint").innerText(), /part_002/);
    await page.locator("#jump-candidate").click();
    assert.equal(await page.locator("#part-candidate").inputValue(), "2");

    // Real Chromium must visibly draw local-only open boundary segments,
    // allow the overlay to be hidden, and preserve anonymous part filters.
    await page.locator("#part-reference").selectOption("all");
    const boundariesOn = await images();
    await page.locator("#show-boundaries").uncheck();
    const boundariesOff = await images();
    assert.notEqual(boundariesOn[0], boundariesOff[0],
                    "Observed boundary line overlay did not toggle on reference");
    assert.notEqual(boundariesOn[1], boundariesOff[1],
                    "Observed boundary line overlay did not toggle on candidate");
    await page.locator("#show-boundaries").check();
    assert.match(await page.locator(".note").innerText(), /境界ゼロでも穴や内壁/);

    // Confirm a flagged synthetic face really toggles its purple outline.
    await page.locator("#part-reference").selectOption("all");
    const sensitivityOn = await images();
    await page.locator("#show-sensitive").uncheck();
    const sensitivityOff = await images();
    assert.notEqual(sensitivityOn[0], sensitivityOff[0], "Sensitivity outline did not toggle");
    await page.locator("#show-sensitive").check();

    // Red/grey filtering and reset must work without console exceptions.
    const countBefore = await page.locator("#count-reference").innerText();
    await page.locator("#hide-low").check();
    const countAfter = await page.locator("#count-reference").innerText();
    assert.notEqual(countBefore, countAfter);
    await page.locator("#hide-low").uncheck();
    await page.locator("#reset").click();
    assert.equal(await page.locator("#part-candidate").inputValue(), "2");
    assert.deepEqual(errors, [], "Browser runtime errors found");
    assert.deepEqual(network, [], "Private local HTML attempted HTTP networking");
    console.log("CBDK_BROWSER_GUI_SMOKE_PASS");
  } finally {
    await browser.close();
  }
}

run().catch((e) => { console.error(e); process.exitCode = 1; });
