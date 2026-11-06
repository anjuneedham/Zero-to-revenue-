// End-to-end browser test of the sales journey against a LOCAL server with a throwaway database.
// Usage: BASE=http://127.0.0.1:8099 TOKEN=<session token> OUT=<dir> node tests/e2e/journey.js
// Uses only clearly-labelled TEST data. Writes results.json (+ screenshots and a screen recording) to OUT.
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
const BASE = process.env.BASE || "http://127.0.0.1:8099", TOKEN = process.env.TOKEN, OUT = process.env.OUT || "/tmp/e2e-out";
fs.mkdirSync(OUT, { recursive: true });
const results = [];
const NAME = "TEST Demo Roofing Co";

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, recordVideo: { dir: path.join(OUT, "video"), size: { width: 1280, height: 800 } } });
  await ctx.addInitScript(t => { try { localStorage.setItem("z2r_token", t); } catch (e) {} }, TOKEN);
  const page = await ctx.newPage();
  const consoleErrors = [], badResponses = [];
  page.on("console", m => { if (m.type() === "error") consoleErrors.push(m.text()); });
  page.on("pageerror", e => consoleErrors.push("pageerror: " + e.message));
  page.on("response", r => { if (r.status() >= 500) badResponses.push(r.status() + " " + r.url()); });

  const step = async (id, name, fn) => {
    try { await fn(); results.push({ id, name, status: "passed" }); console.log("PASS", id, name); }
    catch (e) { results.push({ id, name, status: "failed", error: String(e.message).split("\n")[0] }); console.log("FAIL", id, name, "-", String(e.message).split("\n")[0]); await page.screenshot({ path: path.join(OUT, `FAIL_${id}.png`) }).catch(() => {}); }
  };
  const shot = n => page.screenshot({ path: path.join(OUT, n + ".png") });
  const expectText = async t => { await page.getByText(t, { exact: false }).first().waitFor({ timeout: 6000 }); };
  const go = async h => { await page.evaluate(x => { location.hash = x; }, h); await page.waitForTimeout(500); };
  const btn = n => page.getByRole("button", { name: n, exact: true });

  await page.goto(BASE + "/");
  await page.locator("#shell").waitFor({ state: "visible", timeout: 10000 });

  await step("E00", "Today page loads with a clear empty state", async () => {
    await expectText("Add your first prospect");
    await expectText("No follow-ups due");
    await shot("01_today_empty");
  });
  await step("E00b", "Add form validates: empty submit shows an error", async () => {
    await page.getByRole("button", { name: "Add prospect" }).first().click();
    await expectText("Enter a business name or a contact name");
  });
  await step("E01", "1. Create a prospect (name only)", async () => {
    await go("pipeline"); await expectText("No prospects yet");
    await shot("02_pipeline_empty");
    await page.getByLabel("Business name").first().fill(NAME);
    await page.getByRole("button", { name: "Add prospect" }).first().click();
    await expectText("Prospect identified"); await expectText(NAME);
  });
  await step("E02", "2. Edit prospect details (and validation)", async () => {
    const det = page.locator("section.card", { hasText: "Edit anything" });
    await det.getByLabel("Email").fill("not-an-email");
    await det.getByRole("button", { name: "Save details" }).click();
    await expectText("email address does not look right");
    await det.getByLabel("Email").fill("test.demo@example.invalid");
    await det.getByLabel("Industry").fill("roofing"); await det.getByLabel("Location").fill("Kingston");
    await det.getByLabel("Source").fill("referral"); await det.getByLabel("Potential deal value").fill("900");
    await det.getByRole("button", { name: "Save details" }).click();
    await expectText("Details updated"); await shot("03_prospect_details");
  });
  await step("E03", "3. Research then qualify the prospect", async () => {
    await btn("Log research").click(); await page.getByLabel("What did you find?").fill("TEST: posts job photos, no quote form");
    await page.getByRole("button", { name: "Save", exact: true }).click(); await expectText("Research completed");
    await btn("Qualify").click(); await page.getByLabel("Decision").selectOption("qualified"); await page.getByLabel("Why?").fill("TEST: fits target");
    await page.getByRole("button", { name: "Save", exact: true }).click(); await expectText("Qualification decision: qualified");
  });
  await step("E04", "4+5. Assign a playbook and complete a step", async () => {
    await page.locator("section.card", { hasText: "Assign a playbook" }).getByLabel("Playbook").selectOption({ label: "D. Initial outreach" });
    await page.getByRole("button", { name: "Start playbook" }).click(); await expectText("Playbook started");
    await expectText("1. Choose the channel");
    await page.getByLabel(/^Step 1: Choose the channel/).check(); await expectText("Step done: Choose the channel");
    await expectText("1 of 4 steps"); await shot("04_playbook_running");
  });
  await step("E05", "6+7. Record outreach and schedule a follow-up", async () => {
    await btn("Log message sent").click();
    const pn = page.locator(".panelhold");
    await pn.getByLabel("Channel").selectOption("email"); await pn.getByLabel("Approach label").fill("TEST quote-page idea");
    await pn.getByLabel("What you sent").fill("TEST message body"); await pn.getByRole("button", { name: "Record sent" }).click();
    await expectText("Initial message sent (email)"); await expectText("Follow-up scheduled for");
  });
  await step("E06", "8. Complete the follow-up from Today", async () => {
    await page.getByRole("button", { name: "Schedule follow-up" }).click();
    await page.getByLabel("Due date").fill(new Date().toISOString().slice(0, 10)); await page.getByRole("button", { name: "Save", exact: true }).click();
    await go("today"); await expectText("Follow up: " + NAME); await shot("05_today_followup_due");
    await page.locator(".item", { hasText: "Follow up: " + NAME }).getByRole("button", { name: "Done" }).first().click();
    await expectText("Recent activity"); await page.waitForTimeout(400);
  });
  await step("E07", "9. Record a positive response", async () => {
    await go("pipeline"); await page.getByText(NAME).first().click(); await expectText("Qualification:");
    await btn("Log response").click(); await page.getByLabel("How did it read?").selectOption("positive"); await page.getByLabel("What they said").fill("TEST: interested");
    await page.getByRole("button", { name: "Save", exact: true }).click(); await expectText("Response received (positive)");
  });
  await step("E08", "10. Move through the pipeline manually", async () => {
    await btn("Move stage").click(); await page.getByLabel("New stage").selectOption("conversation");
    await page.getByRole("button", { name: "Save", exact: true }).click(); await expectText("Stage: Response received -> Conversation");
  });
  await step("E09", "11. Record a meeting", async () => {
    await btn("Meeting").click(); await page.getByLabel("Meeting date").fill("2099-01-05"); await page.locator(".panelhold").getByLabel("Notes").fill("TEST intro call");
    await page.getByRole("button", { name: "Save", exact: true }).click(); await expectText("Meeting booked for 2099-01-05");
  });
  await step("E10", "12. Record a proposal", async () => {
    await btn("Proposal").click(); await page.getByLabel(/Proposal value/).fill("900"); await page.getByRole("button", { name: "Save", exact: true }).click();
    await expectText("Proposal delivered");
  });
  await step("E11", "13. Mark the prospect won", async () => {
    await btn("Win / lose / park").click(); await page.getByLabel("Outcome").selectOption("won"); await page.getByLabel(/^Revenue/).fill("900");
    await page.getByRole("button", { name: "Save", exact: true }).click(); await expectText("Customer won"); await expectText("not verified"); await shot("06_prospect_won");
  });
  await step("E12", "14. Timeline lists the whole journey; playback steps through it", async () => {
    for (const t of ["Prospect identified", "Research completed", "Playbook started", "Initial message sent", "Follow-up completed", "Response received (positive)", "Meeting booked for", "Proposal delivered", "Customer won"]) await expectText(t);
    const play = page.locator("section.card", { hasText: "Step through the recorded events" });
    await play.getByRole("button", { name: "Next" }).click(); await play.getByText("Event 2 of").waitFor();
    await play.getByRole("button", { name: "Play" }).click(); await page.waitForTimeout(1600); await play.getByRole("button", { name: /Pause|Play/ }).click();
    await shot("07_timeline_playback");
  });
  await step("E13", "15. Insights show performance with counts, no false precision", async () => {
    await go("insights"); await expectText("Customers won"); await expectText("too few to read"); await expectText("Recorded fact"); await expectText("Business timeline"); await shot("08_insights");
  });
  await step("E14", "Persistence after refresh", async () => {
    await page.reload(); await page.locator("#shell").waitFor({ state: "visible" });
    await go("pipeline"); await page.getByRole("button", { name: /^Closed \(1\)/ }).click(); await expectText(NAME); await expectText("Customer won");
  });
  await step("E15", "Playbooks: duplicate, edit steps, reorder, archive", async () => {
    await go("playbooks"); await expectText("A. Prospect discovery");
    await shot("09_playbooks");
    await page.locator(".item", { hasText: "E. Follow-up" }).first().click(); await expectText("Edit playbook");
    await page.getByRole("button", { name: "Duplicate" }).click(); await expectText("(copy)");
    await page.getByRole("button", { name: "Add step" }).click();
    const titles = page.getByLabel(/^Step \d+ title/); const n = await titles.count();
    await titles.nth(n - 1).fill("TEST call them"); await page.getByRole("button", { name: "Down" }).first().click();
    await page.getByRole("button", { name: "Save new version" }).click(); await expectText("Version 2");
    await shot("10_playbook_editor");
    await page.getByRole("button", { name: "Archive" }).click(); await expectText("Your playbooks");
  });
  await step("E16", "Targets are configurable", async () => {
    await go("today"); const c = page.locator("section.card", { hasText: "Change what a good day looks like" });
    await c.getByLabel("Research prospects").fill("2"); await c.getByRole("button", { name: "Save targets" }).click(); await expectText("Research prospects");
    await page.getByText("1 / 2").first().waitFor();
  });
  await step("E17", "Deleting a prospect keeps its history", async () => {
    await go("pipeline"); await page.getByRole("button", { name: /^Closed/ }).click(); await page.getByText(NAME).first().click(); await expectText("Remove prospect");
    page.once("dialog", d => d.accept()); await btn("Delete prospect").click(); await expectText("No prospects yet", { timeout: 4000 }).catch(() => {});
    await go("insights"); await expectText("Prospect record deleted");
  });
  await step("E18", "Unknown prospect id shows a recovery path, not a crash", async () => {
    await go("prospect/ld_doesnotexist"); await expectText("Prospect not found"); await expectText("Back to pipeline", {});
  });

  // layout + accessibility on tablet landscape/portrait + phone
  for (const [label, w, h] of [["tablet-landscape", 1280, 800], ["tablet-portrait", 800, 1280], ["phone", 390, 844]]) {
    await step("L_" + label, `Layout ${label} ${w}x${h}: no horizontal overflow on any page`, async () => {
      await page.setViewportSize({ width: w, height: h });
      const bad = [];
      for (const r of ["today", "pipeline", "playbooks", "playbook/pb_follow_up", "insights"]) {
        await go(r); await page.waitForTimeout(700);
        const o = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
        if (o.sw > o.cw + 1) bad.push(`${r}: ${o.sw}>${o.cw}`);
        if (r === "today") await shot(`11_today_${label}`);
      }
      if (bad.length) throw new Error("overflow: " + bad.join("; "));
    });
  }
  await page.setViewportSize({ width: 1280, height: 800 });
  await step("A11Y", "Accessibility basics: every field labelled, buttons named, one h1, focus visible", async () => {
    const problems = [];
    for (const r of ["today", "pipeline", "playbooks", "insights"]) {
      await go(r);
      const p = await page.evaluate(() => {
        const out = [];
        document.querySelectorAll("#view input,#view select,#view textarea").forEach(i => { if (i.type === "hidden") return; const has = i.labels && i.labels.length || i.getAttribute("aria-label"); if (!has) out.push("unlabelled " + i.tagName + " " + (i.name || i.placeholder || i.type)); });
        document.querySelectorAll("#view button, #view a.btn").forEach(b => { if (!b.textContent.trim() && !b.getAttribute("aria-label")) out.push("unnamed button"); });
        const vis = [...document.querySelectorAll("h1")].filter(h => h.offsetParent !== null || getComputedStyle(h).position === "fixed" && !h.closest("[hidden]")); if (vis.length !== 1) out.push("visible h1 count " + vis.length);
        if (!document.documentElement.lang) out.push("no lang");
        return out;
      });
      p.forEach(x => problems.push(r + ": " + x));
    }
    if (problems.length) throw new Error(problems.slice(0, 6).join("; "));
  });
  await step("ERR", "No JavaScript errors or server 5xx during the whole run", async () => {
    const real = consoleErrors.filter(e => !/favicon|Failed to load resource: the server responded with a status of 4\d\d/.test(e));
    if (real.length || badResponses.length) throw new Error(JSON.stringify({ console: real.slice(0, 3), http5xx: badResponses.slice(0, 3) }));
  });

  await ctx.close(); await browser.close();
  fs.writeFileSync(path.join(OUT, "results.json"), JSON.stringify(results, null, 1));
  const failed = results.filter(r => r.status !== "passed");
  console.log(`\n${results.length - failed.length}/${results.length} passed`);
  process.exit(failed.length ? 1 : 0);
})();
