import { chromium } from "playwright";
const OUT = "C:/Users/shinta/Documents/GitHub/kouchou-ai/tmp-embeddable-poc";
const b = await chromium.launch();
const p = await b.newPage();
const errs = [];
p.on("pageerror", e => errs.push(e.message.split(";")[0]));
await p.goto("http://127.0.0.1:8140/viewer/", { waitUntil: "networkidle" });
await p.waitForTimeout(4000);
const listText = (await p.locator("body").innerText());
const links = await p.locator('a[href*="/report?slug="]').count();
await p.screenshot({ path: `${OUT}/list-final.png`, fullPage: true });
console.log("LIST hasHeading:", listText.includes("レポート一覧"));
console.log("LIST has seeded title あああ:", listText.includes("あああ"));
console.log("LIST report links:", links);
console.log("LIST text (first 300):", listText.slice(0,300).replace(/\n/g," "));
console.log("pageerrors:", [...new Set(errs)]);
// click first report link if present
if (links > 0) {
  await p.locator('a[href*="/report?slug="]').first().click();
  await p.waitForTimeout(3500);
  const rt = await p.locator("body").innerText();
  await p.screenshot({ path: `${OUT}/report-final.png`, fullPage: false });
  console.log("AFTER CLICK report textLen:", rt.length, "hasChart/overview:", rt.includes("424件") || rt.includes("クラスタ"));
}
await b.close();
