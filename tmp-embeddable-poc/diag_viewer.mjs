import { chromium } from "playwright";
const BASE = "http://127.0.0.1:8140";
const browser = await chromium.launch();
const page = await browser.newPage();
const logs = [];
page.on("console", (m) => logs.push(`[${m.type()}] ${m.text()}`));
page.on("pageerror", (e) => logs.push(`[PAGEERROR] ${e.message}\n${e.stack || ""}`));

await page.goto(`${BASE}/viewer/`, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(3000);
const body = await page.locator("body").innerText().catch(() => "(no body)");
// Next error overlay text if any
const overlay = await page.locator("[data-nextjs-dialog-body], nextjs-portal").allInnerTexts().catch(() => []);
console.log("=== BODY TEXT ===\n" + body.slice(0, 400));
console.log("\n=== OVERLAY ===\n" + JSON.stringify(overlay).slice(0, 600));
console.log("\n=== LOGS ===\n" + logs.join("\n").slice(0, 3000));
await browser.close();
