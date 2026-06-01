import { chromium } from "playwright";
const b = await chromium.launch(); const p = await b.newPage();
const f404 = [];
p.on("response", r => { if (r.status() === 404) f404.push(r.url()); });
await p.goto("http://127.0.0.1:8141/viewer/", { waitUntil: "networkidle" });
await p.waitForTimeout(1500);
const hrefs = await p.locator("a").evaluateAll(els => els.map(e => e.getAttribute("href")).filter(h => h && h.includes("report")));
console.log("report links:", JSON.stringify(hrefs));
// click the card and see if it navigates to a rendered report
const card = p.locator('a[href*="report"]').first();
if (await card.count()) {
  await card.click();
  await p.waitForTimeout(2500);
  console.log("after click URL:", p.url());
  const t = await p.locator("body").innerText();
  console.log("after click has '424件':", t.includes("424件"), "| has overview:", t.includes("AI技術"));
}
console.log("404s:", JSON.stringify(f404));
await b.close();
