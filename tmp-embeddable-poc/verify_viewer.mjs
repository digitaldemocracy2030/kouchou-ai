import { chromium } from "playwright";

const BASE = "http://127.0.0.1:8140";
const SLUG = "66517e7a-72ab-45f2-8481-aec4669ff846";
const OUT = "C:/Users/shinta/Documents/GitHub/kouchou-ai/tmp-embeddable-poc";

const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", (e) => errors.push(String(e)));

// 1) List page
await page.goto(`${BASE}/viewer/`, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);
const listText = await page.locator("body").innerText();
const hasListHeading = listText.includes("レポート一覧");
const hasSeededTitle = listText.includes("あああ");
await page.screenshot({ path: `${OUT}/viewer-list.png`, fullPage: false });

// find a link to the report
const reportLink = await page.locator(`a[href*="/report?slug="]`).first().getAttribute("href").catch(() => null);

// 2) Report page (direct)
await page.goto(`${BASE}/viewer/report?slug=${SLUG}`, { waitUntil: "networkidle" });
await page.waitForTimeout(2500);
const reportText = await page.locator("body").innerText();
const looksLikeReport =
  !reportText.includes("レポートが見つかりませんでした") &&
  !reportText.includes("API") &&
  reportText.length > 200;
await page.screenshot({ path: `${OUT}/viewer-report.png`, fullPage: false });

console.log(JSON.stringify({
  list: { httpOk: true, hasListHeading, hasSeededTitle, reportLink },
  report: { textLen: reportText.length, looksLikeReport, sample: reportText.slice(0, 160).replace(/\n/g, " ") },
  consoleErrors: errors.slice(0, 8),
}, null, 2));

await browser.close();
