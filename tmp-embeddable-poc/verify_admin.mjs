import { chromium } from "playwright";
const BASE = "http://127.0.0.1:8160";
const OUT = "C:/Users/shinta/Documents/GitHub/kouchou-ai/tmp-embeddable-poc";
const b = await chromium.launch(); const p = await b.newPage();
const errs = [];
p.on("pageerror", e => errs.push(String(e.message||e)));
const f404 = [];
p.on("response", r => { if (r.status() >= 400) f404.push(`${r.status()} ${r.url()}`); });

// list page
await p.goto(`${BASE}/admin-ui/`, { waitUntil: "networkidle" });
await p.waitForTimeout(2000);
const listText = await p.locator("body").innerText();
await p.screenshot({ path: `${OUT}/admin-list.png` });

// create page
await p.goto(`${BASE}/admin-ui/create/`, { waitUntil: "networkidle" });
await p.waitForTimeout(2500);
const createText = await p.locator("body").innerText();
await p.screenshot({ path: `${OUT}/admin-create.png` });

const crash = s => s.includes("Application error") || s.includes("client-side exception");
console.log(JSON.stringify({
  list: { len: listText.length, crash: crash(listText), sample: listText.replace(/\n/g," ").slice(0,160) },
  create: { len: createText.length, crash: crash(createText), sample: createText.replace(/\n/g," ").slice(0,200) },
  pageErrors: errs.slice(0,6),
  http4xx5xx: f404.slice(0,10),
}, null, 2));
await b.close();
