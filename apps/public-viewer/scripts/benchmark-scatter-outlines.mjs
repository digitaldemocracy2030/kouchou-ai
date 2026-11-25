import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "@playwright/test";

const baseUrl = process.env.SCATTER_OUTLINE_URL ?? "http://127.0.0.1:41261";
const executablePath = process.env.SCATTER_OUTLINE_CHROME;
const output = resolve(process.argv[2] ?? "outline-benchmark");
const rate = Number(process.env.SCATTER_OUTLINE_CPU_RATE ?? 1);
const repeats = Number(process.env.SCATTER_OUTLINE_REPEATS ?? 20);
const viewport = rate === 1 ? { width: 1440, height: 900 } : { width: 390, height: 844 };
const modes = ["convex", "clip"];
assert(Number.isInteger(repeats) && repeats >= 2);
assert(Number.isFinite(rate) && rate >= 1);

function distribution(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const n = sorted.length;
  const middle = (sorted[Math.floor((n - 1) / 2)] + sorted[Math.floor(n / 2)]) / 2;
  return { median: middle, p90: sorted[Math.ceil(n * 0.9) - 1] };
}

async function compare(browser, dataset) {
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  try {
    if (rate > 1) {
      const cdp = await context.newCDPSession(page);
      await cdp.send("Emulation.setCPUThrottlingRate", { rate });
    }
    const url = new URL("/dev/scatter-outlines/", baseUrl);
    url.searchParams.set("data", dataset);
    url.searchParams.set("measure", "1");
    const response = await page.goto(url.href, { timeout: 120000 });
    assert.equal(response.status(), 200);
    await page.waitForLoadState("networkidle", { timeout: 90000 });
    await page.waitForFunction(() => Boolean(window.scatterOutlineBenchmark), null, { timeout: 30000 });

    const plot = page.locator(".js-plotly-plot");
    await page.waitForFunction(
      () => {
        const plot = document.querySelector(".js-plotly-plot");
        return plot?.data?.some((trace) => trace.type === "scattergl") && plot.querySelector(".gl-canvas");
      },
      null,
      { timeout: 90000 },
    );
    await plot.screenshot({ path: resolve(output, `${dataset}-convex.png`) });
    const base = await page.evaluate(() => window.scatterOutlineBenchmark.capture("convex"));
    assert.equal(base.shapes, 0);

    await page.getByRole("radio", { name: "重なりを切り抜く" }).check();
    await page.waitForFunction(() => {
      const plot = document.querySelector(".js-plotly-plot");
      return plot?.layout?.shapes?.length > 0 && plot.querySelector(".shapelayer path");
    });
    await plot.screenshot({ path: resolve(output, `${dataset}-clip.png`) });
    const clip = await page.evaluate(() => window.scatterOutlineBenchmark.capture("clip"));
    assert.deepEqual(clip.markerCoordinates, base.markerCoordinates);
    assert.deepEqual([clip.width, clip.height], [base.width, base.height]);
    assert.equal(base.points, 9568);
    assert.equal(clip.points, base.points);
    const markers = base.markerCoordinates.reduce((count, trace) => count + trace.x.length, 0);

    const result = await page.evaluate(
      async ({ repeats, modes }) => {
        const bench = window.scatterOutlineBenchmark;
        const canvas = document.createElement("canvas");
        const gl = canvas.getContext("webgl2") ?? canvas.getContext("webgl");
        const debug = gl?.getExtension("WEBGL_debug_renderer_info");
        const renderer = debug && gl?.getParameter(debug.UNMASKED_RENDERER_WEBGL);
        gl?.getExtension("WEBGL_lose_context")?.loseContext();
        const samples = { convex: [], clip: [] };
        const geometry = { convex: [], clip: [] };
        let stats;

        for (let index = -4; index < repeats; index++) {
          const order = index % 2 === 0 ? modes : [...modes].reverse();
          for (const mode of order) {
            const measured = bench.geometry(mode);
            stats = measured.stats ?? stats;
            const drawing = await bench.draw(mode);
            if (index >= 0) {
              geometry[mode].push(measured.ms);
              samples[mode].push(drawing);
            }
          }
        }
        return { geometry, samples, stats, renderer, userAgent: navigator.userAgent };
      },
      { repeats, modes },
    );

    const summary = {
      dataset,
      points: base.points,
      markerEntries: markers,
      plotSize: [clip.width, clip.height],
      cpuThrottle: rate,
      repeats,
      shapes: clip.shapes,
      stats: result.stats,
      renderer: result.renderer,
      userAgent: result.userAgent,
      timings: Object.fromEntries(
        modes.map((mode) => [
          mode,
          {
            geometry: distribution(result.geometry[mode]),
            draw: distribution(result.samples[mode].map(({ drawMs }) => drawMs)),
            geometryAndDraw: distribution(
              result.samples[mode].map(({ drawMs }, i) => drawMs + result.geometry[mode][i]),
            ),
            zoom: distribution(result.samples[mode].map(({ zoomMs }) => zoomMs)),
          },
        ]),
      ),
    };
    assert.deepEqual(errors, []);
    await writeFile(resolve(output, `${dataset}.json`), `${JSON.stringify({ summary, ...result }, null, 2)}\n`);
    console.log(JSON.stringify(summary, null, 2));
  } finally {
    await context.close();
  }
}

await mkdir(output, { recursive: true });
const browser = await chromium.launch({ executablePath, args: ["--enable-unsafe-swiftshader"] });
try {
  for (const dataset of ["example", "polis"]) await compare(browser, dataset);
} finally {
  await browser.close();
}
