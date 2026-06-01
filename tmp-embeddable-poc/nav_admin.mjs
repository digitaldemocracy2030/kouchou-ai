import { chromium } from "playwright";
const B = "http://127.0.0.1:8000";
const b = await chromium.launch(); const p = await b.newPage();
const errs=[], net=[];
p.on("pageerror", e=>errs.push(String(e.message||e)));
p.on("response", r=>{ const u=r.url(); if(r.status()>=400) net.push(`${r.status()} ${u.replace(B,'')}`); });

await p.goto(`${B}/admin-ui/`, {waitUntil:"networkidle"});
await p.waitForTimeout(1500);
const links = await p.locator("a").evaluateAll(els=>els.map(e=>({text:(e.textContent||'').trim().slice(0,20), href:e.getAttribute("href")})));
console.log("LINKS on /admin-ui/:", JSON.stringify(links,null,1));

// click 新規作成
const create = p.locator('a:has-text("新規作成"), a[href*="create"]').first();
const has = await create.count();
console.log("create link count:", has);
if (has) {
  await create.click().catch(e=>console.log("click err",String(e)));
  await p.waitForTimeout(2500);
  console.log("after click URL:", p.url());
  const t = await p.locator("body").innerText().catch(()=> "(none)");
  console.log("create rendered (has 新しいレポートを作成):", t.includes("新しいレポートを作成"));
  console.log("body sample:", t.replace(/\n/g,' ').slice(0,120));
}
console.log("pageErrors:", JSON.stringify(errs.slice(0,5)));
console.log("http>=400 during nav:", JSON.stringify(net.slice(0,12)));
await b.close();
