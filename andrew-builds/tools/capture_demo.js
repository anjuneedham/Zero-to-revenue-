// Captures the "A" shots: screen recordings of the REAL Zero-to-Revenue app, driven by Playwright, on clearly fictional DEMO data.
// A "DEMO DATA" label is burned into every frame so these clips can never be mistaken for real outreach.
//   Needs: a local app server on a throwaway database, a session token, and RESET_CMD that resets the DB, restarts the server and
//   writes a fresh token to TOKEN_FILE.  See andrew-builds/episode-001/scripts/README_CAPTURE.md.
//   BASE=http://127.0.0.1:8099 TOKEN_FILE=/tmp/e2e_token RESET_CMD=/tmp/reset_e2e.sh OUT=<screen-recordings/product-demo> node capture_demo.js
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path"), { execSync } = require("child_process");
const BASE = process.env.BASE || "http://127.0.0.1:8099", TOKEN_FILE = process.env.TOKEN_FILE, RESET = process.env.RESET_CMD, OUT = process.env.OUT;
const ONLY = process.env.ONLY ? new Set(process.env.ONLY.split(",")) : null; // e.g. ONLY=A13,A14 re-records just those
const TEST_VIDEO = process.env.TEST_VIDEO; // optional: the journey.js recording to register as A11
if (!OUT || !TOKEN_FILE || !RESET) { console.error("set OUT, TOKEN_FILE, RESET_CMD"); process.exit(2); }
fs.mkdirSync(OUT, { recursive: true });
const manifestPath = path.join(OUT, "manifest.json");
const manifest = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath)) : {};
const token = () => fs.readFileSync(TOKEN_FILE, "utf8").trim();
const reset = () => { execSync(RESET, { stdio: "ignore" }); };
const day = n => { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const post = async (p, body) => { const r = await fetch(`${BASE}/api/sales/${p}`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer " + token() }, body: JSON.stringify(body || {}) }); const j = await r.json(); if (!r.ok) throw new Error(p + ": " + j.error); return j; };
const get = async p => (await (await fetch(`${BASE}/api/sales/${p}`, { headers: { Authorization: "Bearer " + token() } })).json());

const INIT = tok => { try { localStorage.setItem("z2r_token", tok); } catch (e) {}
  const add = () => {
    const c = document.createElement("div");
    c.style.cssText = "position:fixed;z-index:99999;width:24px;height:24px;border-radius:50%;background:rgba(219,161,17,.6);border:2px solid #fff;pointer-events:none;left:-60px;top:-60px;transform:translate(-50%,-50%);box-shadow:0 0 0 2px rgba(0,0,0,.35)";
    const l = document.createElement("div"); l.textContent = "DEMO DATA · fictional businesses";
    l.style.cssText = "position:fixed;z-index:99998;left:12px;bottom:12px;padding:6px 12px;border-radius:99px;background:rgba(10,15,26,.88);color:#F2B01E;font:700 13px/1 Inter,system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;pointer-events:none";
    document.body.append(c, l);
    addEventListener("mousemove", e => { c.style.left = e.clientX + "px"; c.style.top = e.clientY + "px"; }, true);
    addEventListener("mousedown", () => { c.style.transform = "translate(-50%,-50%) scale(.6)"; }, true); addEventListener("mouseup", () => { c.style.transform = "translate(-50%,-50%) scale(1)"; }, true);
  };
  if (document.body) add(); else document.addEventListener("DOMContentLoaded", add);
};

async function clip(id, slug, vp, fn) {
  if (ONLY && !ONLY.has(id)) return;
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: vp, recordVideo: { dir: path.join(OUT, "_raw"), size: vp } });
  await ctx.addInitScript(INIT, token());
  const page = await ctx.newPage(); const t0 = Date.now(); let offset = null;
  const H = {
    page, pause: ms => page.waitForTimeout(ms), mark: () => { if (offset === null) offset = (Date.now() - t0) / 1000; },
    async move(loc) { await loc.scrollIntoViewIfNeeded(); const b = await loc.boundingBox(); await page.mouse.move(b.x + Math.min(b.width / 2, 120), b.y + b.height / 2, { steps: 28 }); },
    async click(loc) { await H.move(loc); await H.pause(380); await loc.click(); await H.pause(700); },
    async type(loc, t) { await H.move(loc); await loc.click(); await page.keyboard.type(t, { delay: 60 }); await H.pause(450); },
    async scroll(total, steps = 10, gap = 280) { for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, total / steps); await H.pause(gap); } },
    async go(h) { await page.evaluate(x => { location.hash = x; }, h); await H.pause(900); },
    btn: n => page.getByRole("button", { name: n, exact: true }),
  };
  await page.goto(BASE + "/"); await page.locator("#shell").waitFor({ state: "visible", timeout: 10000 }); await H.pause(1400);
  try { await fn(H); } finally {
    const dur = (Date.now() - t0) / 1000; const video = page.video(); await ctx.close(); const raw = await video.path(); await browser.close();
    const name = `EP001_${id}_${slug}_v01.webm`; fs.renameSync(raw, path.join(OUT, name));
    manifest[id] = { file: name, start_offset_s: Math.round((offset ?? 1.5) * 10) / 10, duration_s: Math.round(dur * 10) / 10, viewport: `${vp.width}x${vp.height}`, data: "DEMO", burned_label: true, captured: new Date().toISOString() };
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 1)); console.log("captured", id, name, manifest[id].duration_s + "s");
  }
}
const L = { width: 1600, height: 1000 }, P = { width: 810, height: 1440 };

(async () => {
  // A12: portrait, empty database
  reset();
  await clip("A12", "portrait-empty-then-add", P, async h => {
    h.mark(); await h.pause(2500);
    await h.scroll(500, 4, 400); await h.pause(800); await h.scroll(-500, 4, 300); await h.pause(500);
    await h.go("pipeline"); await h.pause(800);
    await h.type(h.page.getByLabel("Business name").first(), "DEMO Palm Electric");
    await h.click(h.page.getByRole("button", { name: "Add prospect" }).first()); await h.pause(2500);
  });
  // A01 + A02 + A03 + A04: landscape, empty database, one prospect created live
  reset();
  await clip("A01", "today-empty", L, async h => {
    h.mark(); await h.pause(3000); await h.scroll(450, 5, 450); await h.pause(1200);
    await h.type(h.page.getByLabel("Business name").first(), "DEMO Sample Roofing Co");
    await h.click(h.page.getByRole("button", { name: "Add prospect" }).first()); await h.pause(2500);
  });
  const lead = (await get("prospects")).prospects[0];
  await clip("A02", "prospect-create-edit", L, async h => {
    await h.go("pipeline"); h.mark(); await h.pause(1800);
    await h.type(h.page.getByLabel("Business name").first(), "DEMO Harbour Tiling");
    await h.click(h.page.getByRole("button", { name: "Add prospect" }).first()); await h.pause(2200);
    const det = h.page.locator("section.card", { hasText: "Edit anything" });
    await h.type(det.getByLabel("Industry"), "tiling"); await h.type(det.getByLabel("Location"), "Kingston"); await h.type(det.getByLabel("Source"), "referral");
    await h.type(det.getByLabel("Potential deal value"), "800"); await h.click(det.getByRole("button", { name: "Save details" })); await h.pause(2200);
    await h.scroll(900, 6, 450); await h.pause(2500);
  });
  await clip("A03", "playbook-run", L, async h => {
    await h.go("prospect/" + lead.id); h.mark(); await h.pause(2000);
    await h.page.locator("section.card", { hasText: "Assign a playbook" }).getByLabel("Playbook").selectOption({ label: "D. Initial outreach" }); await h.pause(900);
    await h.click(h.page.getByRole("button", { name: "Start playbook" })); await h.pause(1800);
    await h.click(h.page.getByLabel(/^Step 1:/)); await h.pause(1600);
    await h.type(h.page.getByLabel(/^Note for Write the message/), "Used the quote-form observation"); await h.click(h.page.getByLabel(/^Step 2:/)); await h.pause(1600);
    await h.click(h.page.locator("details.guide summary")); await h.pause(1500); await h.scroll(500, 5, 500); await h.pause(2500);
  });
  await clip("A04", "log-outreach-followup", L, async h => {
    await h.go("prospect/" + lead.id); h.mark(); await h.pause(1600);
    await h.click(h.btn("Log message sent")); const pn = h.page.locator(".panelhold");
    await pn.getByLabel("Channel").selectOption("email"); await h.pause(700);
    await h.type(pn.getByLabel("Approach label"), "quote-page idea");
    await h.type(pn.getByLabel("What you sent"), "Hi, I noticed your site has photos but no way to request a quote. Would a simple quote form help?");
    await h.pause(800); await h.click(pn.getByRole("button", { name: "Record sent" })); await h.pause(2200);
    await h.scroll(800, 6, 450); await h.pause(2500);
  });

  // ---- seed a believable, clearly fictional, backdated data set, then capture the populated screens ----
  const mk = async (b, extra) => (await post("prospects", { business: b, ...extra, occurred_at: extra.created || day(-10) })).prospect.id;
  const a = await mk("DEMO Island Roofing", { industry: "roofing", location: "Kingston", source_channel: "referral", deal_value: "900", created: day(-9) });
  await post(`prospects/${a}/research`, { notes: "Posts job photos weekly. No quote form on the site.", occurred_at: day(-8) });
  await post(`prospects/${a}/qualify`, { decision: "qualified", reasons: "Active, owner-run, reachable.", occurred_at: day(-8) });
  await post(`prospects/${a}/outreach`, { channel: "email", angle: "quote-page idea", text: "Hi, noticed your photos but no quote form...", occurred_at: day(-7) });
  await post(`prospects/${a}/response`, { sentiment: "positive", text: "Interested, can we talk Thursday?", channel: "email", occurred_at: day(-5) });
  await post(`prospects/${a}/meeting`, { when: day(-3), notes: "Intro call", occurred_at: day(-5) });
  await post(`prospects/${a}/meeting`, { when: day(-3), notes: "Held. Needs a way to capture leads.", held: true, occurred_at: day(-3) });
  await post(`prospects/${a}/proposal`, { value: "900", notes: "One page", occurred_at: day(-1) });
  await post(`prospects/${a}/followup`, { due_date: day(1), note: "Ask for a decision" });
  const b = await mk("DEMO Blue Mountain Plumbing", { industry: "plumbing", location: "St Andrew", source_channel: "instagram", created: day(-7) });
  await post(`prospects/${b}/research`, { notes: "Busy Instagram, phone only.", occurred_at: day(-7) });
  await post(`prospects/${b}/qualify`, { decision: "qualified", occurred_at: day(-6) });
  await post(`prospects/${b}/outreach`, { channel: "whatsapp", angle: "quote-page idea", text: "Hi...", occurred_at: day(-6) });
  await post(`prospects/${b}/followup`, { due_date: day(-3), note: "No reply yet" });
  const c = await mk("DEMO Palm Electric", { industry: "electrical", location: "Spanish Town", source_channel: "referral", created: day(-3) });
  await post(`prospects/${c}/research`, { notes: "Small crew, website is a one-page.", occurred_at: day(-2) });
  await post(`prospects/${c}/qualify`, { decision: "qualified", occurred_at: day(-2) });
  await post(`prospects/${c}/prepare`, { channel: "email", angle: "quote-page idea", text: "Draft...", occurred_at: day(-1) });
  await mk("DEMO Harbour Tiling 2", { industry: "tiling", source_channel: "walk-in", created: day(-1) });
  const e = await mk("DEMO Sunrise Painting", { industry: "painting", location: "Portmore", source_channel: "instagram", created: day(-5) });
  await post(`prospects/${e}/outreach`, { channel: "instagram", angle: "cold DM", text: "Hi...", occurred_at: day(-4) });
  await post(`prospects/${e}/followup`, { due_date: day(0), note: "First nudge" });
  const f = await mk("DEMO Cedar Carpentry", { industry: "carpentry", source_channel: "directory", created: day(-10) });
  await post(`prospects/${f}/outreach`, { channel: "email", angle: "cold DM", text: "Hi...", occurred_at: day(-9) });
  await post(`prospects/${f}/response`, { sentiment: "negative", text: "Too expensive for us right now.", occurred_at: day(-8) });
  await post(`prospects/${f}/close`, { outcome: "lost", reason: "price", occurred_at: day(-8) });
  const g = await mk("DEMO Kingston Landscaping", { industry: "landscaping", location: "Kingston", source_channel: "referral", created: day(-6) });
  await post(`prospects/${g}/research`, { notes: "Established, uses WhatsApp for jobs.", occurred_at: day(-5) });
  await post(`prospects/${g}/qualify`, { decision: "qualified", occurred_at: day(-5) });
  await post(`prospects/${g}/outreach`, { channel: "whatsapp", angle: "quote-page idea", text: "Hi...", occurred_at: day(-4) });
  await post(`prospects/${g}/response`, { sentiment: "positive", text: "Sure, call me.", occurred_at: day(-3) });
  await post(`prospects/${g}/meeting`, { when: day(2), notes: "Discovery call", occurred_at: day(-2) });
  const run = await post(`playbooks/pb_discovery_call/start`, { lead_id: g });

  await clip("A05", "today-populated", L, async h => {
    h.mark(); await h.pause(3500); await h.scroll(1100, 8, 600); await h.pause(2500); await h.scroll(1200, 8, 600); await h.pause(2500);
  });
  await clip("A09", "pipeline-populated", L, async h => {
    await h.go("pipeline"); h.mark(); await h.pause(3000);
    await h.click(h.page.getByRole("button", { name: /^Contacted \(/ })); await h.pause(2200);
    await h.click(h.page.getByRole("button", { name: /^Closed \(/ })); await h.pause(2200);
    await h.click(h.page.getByRole("button", { name: /^Active \(/ })); await h.pause(1800);
    await h.click(h.page.getByText("DEMO Island Roofing").first()); await h.pause(3000);
  });
  await clip("A06", "timeline-playback", L, async h => {
    await h.go("prospect/" + a); h.mark(); await h.pause(2200);
    const play = h.page.locator("section.card", { hasText: "Step through the recorded events" }); await play.scrollIntoViewIfNeeded(); await h.pause(1500);
    for (let i = 0; i < 4; i++) { await h.click(play.getByRole("button", { name: "Next" })); await h.pause(1400); }
    await h.click(play.getByRole("button", { name: "Play" })); await h.pause(9000);
    await h.scroll(700, 5, 500); await h.pause(2500);
  });
  await clip("A07", "insights", L, async h => {
    await h.go("insights"); h.mark(); await h.pause(3500); await h.scroll(700, 6, 600); await h.pause(3000); await h.scroll(900, 6, 600); await h.pause(3000);
  });
  await clip("A08", "playbook-editor", L, async h => {
    await h.go("playbooks"); h.mark(); await h.pause(2500); await h.scroll(500, 4, 500);
    await h.click(h.page.locator(".item", { hasText: "E. Follow-up" }).first()); await h.pause(2500);
    await h.click(h.page.getByRole("button", { name: "Duplicate" })); await h.pause(2500);
    await h.click(h.page.getByRole("button", { name: "Add step" }));
    const t = h.page.getByLabel(/^Step \d+ title/); const n = await t.count(); await h.type(t.nth(n - 1), "Call them instead"); await h.pause(800);
    await h.click(h.page.getByRole("button", { name: "Down" }).first()); await h.pause(1200);
    await h.click(h.page.getByRole("button", { name: "Save new version" })); await h.pause(3000);
  });
  await clip("A10", "tablet-portrait-today", P, async h => {
    h.mark(); await h.pause(3000); await h.scroll(1000, 8, 600); await h.pause(2500); await h.scroll(900, 8, 600); await h.pause(2500);
  });
  // ---- portrait versions (phone/tablet-portrait layout) so vertical videos stay legible ----
  await clip("A13", "portrait-pipeline", P, async h => {
    await h.go("pipeline"); h.mark(); await h.pause(2800); await h.scroll(450, 4, 450); await h.pause(1200);
    await h.click(h.page.getByRole("button", { name: /^Contacted \(/ })); await h.pause(2200);
    await h.click(h.page.getByRole("button", { name: /^Closed \(/ })); await h.pause(2200);
    await h.click(h.page.getByRole("button", { name: /^Active \(/ })); await h.pause(1800);
    await h.click(h.page.getByText("DEMO Island Roofing").first()); await h.pause(3000);
  });
  await clip("A14", "portrait-timeline-playback", P, async h => {
    await h.go("prospect/" + a); h.mark(); await h.pause(2200);
    const play = h.page.locator("section.card", { hasText: "Step through the recorded events" }); await play.scrollIntoViewIfNeeded(); await h.pause(1500);
    for (let i = 0; i < 3; i++) { await h.click(play.getByRole("button", { name: "Next" })); await h.pause(1500); }
    await h.click(play.getByRole("button", { name: "Play" })); await h.pause(8000);
  });
  await clip("A15", "portrait-insights", P, async h => {
    await h.go("insights"); h.mark(); await h.pause(3000); await h.scroll(900, 7, 550); await h.pause(2800); await h.scroll(900, 7, 550); await h.pause(2800);
  });
  await clip("A16", "portrait-playbook-editor", P, async h => {
    await h.go("playbooks"); h.mark(); await h.pause(2500); await h.scroll(500, 4, 500);
    await h.click(h.page.locator(".item", { hasText: "E. Follow-up" }).first()); await h.pause(2500);
    await h.click(h.page.getByRole("button", { name: "Duplicate" })); await h.pause(2500);
    await h.click(h.page.getByRole("button", { name: "Add step" }));
    const t = h.page.getByLabel(/^Step \d+ title/); const n = await t.count(); await h.type(t.nth(n - 1), "Call them instead"); await h.pause(800);
    await h.click(h.page.getByRole("button", { name: "Save new version" })); await h.pause(3000);
  });
  await clip("A17", "portrait-log-outreach", P, async h => {
    await h.go("prospect/" + c); h.mark(); await h.pause(2000);
    await h.click(h.btn("Log message sent")); const pn = h.page.locator(".panelhold");
    await pn.getByLabel("Channel").selectOption("email"); await h.pause(700);
    await h.type(pn.getByLabel("Approach label"), "quote-page idea");
    await h.type(pn.getByLabel("What you sent"), "Hi, noticed your site has photos but no quote form. Would a simple one help?");
    await h.pause(700); await h.click(pn.getByRole("button", { name: "Record sent" })); await h.pause(2500); await h.scroll(900, 6, 450); await h.pause(2200);
  });
  await clip("A18", "portrait-prospect-create-edit", P, async h => {
    await h.go("pipeline"); h.mark(); await h.pause(1800);
    await h.type(h.page.getByLabel("Business name").first(), "DEMO Harbour Tiling 3");
    await h.click(h.page.getByRole("button", { name: "Add prospect" }).first()); await h.pause(2200);
    const det = h.page.locator("section.card", { hasText: "Edit anything" });
    await h.type(det.getByLabel("Industry"), "tiling"); await h.type(det.getByLabel("Location"), "Kingston"); await h.type(det.getByLabel("Source"), "referral");
    await h.click(det.getByRole("button", { name: "Save details" })); await h.pause(2500);
  });
  if (TEST_VIDEO && fs.existsSync(TEST_VIDEO)) {
    const name = "EP001_A11_e2e-test-run_v01.webm"; fs.copyFileSync(TEST_VIDEO, path.join(OUT, name));
    manifest.A11 = { file: name, start_offset_s: 0, duration_s: null, viewport: "1280x800", data: "TEST", burned_label: false, label: "AUTOMATED TEST RUN · made-up data", captured: new Date().toISOString() };
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 1)); console.log("registered A11");
  }
  fs.rmSync(path.join(OUT, "_raw"), { recursive: true, force: true });
  console.log("done");
})().catch(e => { console.error("CAPTURE FAILED:", e.message); process.exit(1); });
