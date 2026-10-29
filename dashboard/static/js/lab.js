// Lab (Phase 8): Knowledge and Research (sources, verified/assumed/unknown evidence, business-scoped search) and the Prompt Lab
// (versions, compare, scores). All DOM via createElement/textContent. Nothing here calls a model.
(function () {
  const { el, add, pill, btn, card, nice } = Z;
  const TABS = [["knowledge", "Knowledge"], ["prompts", "Prompts"]];
  const LABEL_KIND = { verified: "ok", assumed: "warn", unknown: "bad", unsourced: "warn", mixed: "warn" };
  const post = (path, body) => Z.api(path, "POST", body || {});
  let tab = Z.store.get("z2r_lab_tab") || "knowledge", slug = Z.store.get("z2r_lab_biz") || "buildflow", K = null, found = null;
  const SRC_KINDS = [["web", "Web page"], ["document", "Document"], ["interview", "Interview"], ["dataset", "Dataset"], ["internal", "Internal record"], ["other", "Other"]];
  const REL = [["unknown", "Unknown"], ["high", "High"], ["medium", "Medium"], ["low", "Low"]];

  const counts = c => ["verified", "assumed", "unknown"].map(l => c[l] ? pill(l + ": " + c[l], LABEL_KIND[l]) : null);

  function evidenceItem(e) {
    const it = el("div", "item");
    add(it, Z.add(el("div", "meta"), pill(e.label, LABEL_KIND[e.label]), e.source_title ? pill("source: " + e.source_title + (e.source_reliability ? " (" + e.source_reliability + ")" : "")) : pill("no source", "warn"),
      e.weak_source ? pill("verified on a weak source", "bad") : null), el("p", null, e.claim), e.quote ? el("p", "sub", "“" + e.quote + "”") : null);
    const row = el("div", "row");
    if (e.label !== "verified") row.append(btn("Verify with a source", "ghost small", () => verify(e)));
    if (e.label !== "unknown") row.append(btn("Mark unknown", "ghost small", async () => { try { await post("/api/founder/evidence/" + e.id, { label: "unknown" }); await Z.rerender(); } catch (x) { Z.toast(x.message, "bad"); } }));
    it.append(row);
    return it;
  }

  function verify(e) {
    const opts = K.sources.map(s => [s.id, s.title + " (" + s.reliability + ")"]);
    if (!opts.length) { Z.toast("Add a source first", "bad"); return; }
    Z.formDialog("Verify claim (needs a source)", [["source_id", "Source that supports it", "select", opts, true], ["quote", "Supporting quote (optional)", "text"]],
      b => post("/api/founder/evidence/" + e.id, { ...b, label: "verified" }));
  }

  function addEvidence(parentKey, parentId) {
    Z.formDialog("Add a claim", [["claim", "Claim", "text", null, true], ["label", "How sure are you?", "select", [["unknown", "Unknown"], ["assumed", "Assumed (my belief, no proof)"], ["verified", "Verified (needs a source below)"]]],
      ["source_id", "Source (required if verified)", "select", [["", "None"], ...K.sources.map(s => [s.id, s.title])]], ["quote", "Supporting quote (optional)", "text"]],
      b => post("/api/founder/businesses/" + slug + "/evidence", { ...b, [parentKey]: parentId }), { label: "unknown" });
  }

  function entry(root, r, parentKey, kind) {
    const c = card(r.title, kind === "research" ? [r.question, r.summary].filter(Boolean).join(" · ") : r.body);
    c.append(Z.add(el("div", "meta"), pill(kind), pill("trust: " + r.trust, LABEL_KIND[r.trust]), ...counts(r.evidence_counts), r.source_url ? pill("link: " + r.source_url) : null));
    if (r.trust === "unsourced") c.append(el("p", "sub", "No evidence attached: treat this as an unchecked note, not a fact."));
    K.evidence.filter(e => e[parentKey] === r.id).forEach(e => c.append(evidenceItem(e)));
    c.append(Z.add(el("div", "row"), btn("Add claim", "gold small", () => addEvidence(parentKey, r.id))));
    root.append(c);
  }

  async function knowledge(root) {
    K = await Z.api("/api/knowledge/" + slug);
    const top = card("Knowledge for one business", "Everything here and every search is limited to the business you pick. Nothing is shared across businesses.");
    const sel = el("select"); sel.setAttribute("aria-label", "Business");
    [["buildflow", "BuildFlow"], ["agriloop", "Agriloop"], ["fashion", "Fashion"], ["trading", "Trading"]].forEach(([v, l]) => { const o = el("option", null, l); o.value = v; o.selected = v === slug; sel.append(o); });
    sel.onchange = () => { slug = sel.value; Z.store.set("z2r_lab_biz", slug); found = null; Z.rerender(); };
    const g = K.gaps, ec = K.evidence_counts;
    add(top, sel, Z.add(el("div", "meta"), pill("verified: " + ec.verified, "ok"), pill("assumed: " + ec.assumed, "warn"), pill("unknown: " + ec.unknown, "bad"),
      pill("unsourced notes: " + (g.unsourced_knowledge.length + g.unsourced_research.length), g.unsourced_knowledge.length + g.unsourced_research.length ? "warn" : "ok"),
      g.verified_on_weak_source.length ? pill("verified on weak source: " + g.verified_on_weak_source.length, "bad") : null));
    const form = el("form", "row"), q = el("input"); q.type = "search"; q.placeholder = "Search this business"; q.maxLength = 200; q.setAttribute("aria-label", "Search"); q.required = true;
    const glob = el("label", "f"); const cb = el("input"); cb.type = "checkbox"; cb.style.width = "auto"; cb.style.minHeight = "0"; add(glob, cb, document.createTextNode(" include notes shared by all businesses"));
    const go = el("button", "btn small", "Search"); go.type = "submit";
    form.onsubmit = async e => { e.preventDefault(); try { found = await post("/api/knowledge/" + slug + "/search", { q: q.value, include_global: cb.checked }); } catch (x) { found = { error: x.message }; } await Z.rerender(); };
    add(form, q, go); top.append(form, glob);
    top.append(Z.add(el("div", "row"),
      btn("Add research", "gold small", () => Z.formDialog("Add research", [["title", "Title", "text", null, true], ["question", "Question", "text"], ["summary", "Summary", "text"], ["source_url", "Main link", "text"]], b => post("/api/founder/businesses/" + slug + "/research", b))),
      btn("Add note", "gold small", () => Z.formDialog("Add knowledge note", [["title", "Title", "text", null, true], ["body", "Note", "text", null, true], ["tags", "Tags", "text"]], b => post("/api/founder/businesses/" + slug + "/knowledge", b))),
      btn("Add source", "gold small", () => Z.formDialog("Add source", [["title", "Title", "text", null, true], ["url", "Link", "text"], ["kind", "Kind", "select", SRC_KINDS], ["publisher", "Publisher", "text"], ["reliability", "How reliable?", "select", REL]], b => post("/api/founder/businesses/" + slug + "/sources", b)))));
    root.append(top);
    if (found) {
      const c = card("Search results", found.error || (found.scope + " · words: " + (found.query_terms || []).join(", ")));
      if (!found.error && !found.results.length) c.append(Z.none("Nothing matched"));
      (found.results || []).forEach(r => { const it = el("div", "item"); add(it, Z.add(el("div", "meta"), pill(r.kind), pill(r.scope), r.trust ? pill("trust: " + r.trust, LABEL_KIND[r.trust]) : null, r.label ? pill(r.label, LABEL_KIND[r.label]) : null, pill(r.source)), el("p", null, r.title), el("p", "sub", r.excerpt)); c.append(it); });
      if (found.note) c.append(el("p", "sub", found.note));
      root.append(c);
    }
    if (!K.research.length && !K.knowledge.length) root.append(Z.none("No research or notes yet", "Add research or a note, then attach claims labelled verified, assumed or unknown."));
    K.research.forEach(r => entry(root, r, "research_id", "research"));
    K.knowledge.forEach(r => entry(root, r, "knowledge_id", "knowledge"));
    const sc = card("Sources", "Where claims come from. Reliability is your judgement.");
    if (!K.sources.length) sc.append(Z.none("No sources yet"));
    K.sources.forEach(s => { const it = el("div", "item"); add(it, Z.add(el("div", "meta"), pill(nice(s.kind)), pill("reliability: " + s.reliability, s.reliability === "high" ? "ok" : s.reliability === "medium" ? "" : "warn")), el("p", null, s.title + (s.publisher ? " · " + s.publisher : "")), s.url ? el("p", "sub", s.url) : null); sc.append(it); });
    root.append(sc);
  }

  // ---- Prompt Lab ----
  function textarea(label, max) { const w = el("label", "f"); const t = el("textarea"); t.rows = 8; t.maxLength = max; t.required = true; add(w, document.createTextNode(label + " *"), t); return [w, t]; }

  function newVersion(name, body) {
    const f = el("form", "list"), n = el("input"); n.type = "text"; n.value = name || ""; n.required = true; n.pattern = "[a-z0-9][a-z0-9-]+"; n.readOnly = !!name; n.setAttribute("aria-label", "Prompt name");
    const [bw, bt] = textarea("Prompt text", 20000); bt.value = body || ""; bt.rows = 14;
    const note = el("input"); note.type = "text"; note.maxLength = 400; note.placeholder = "What changed and why";
    const err = el("p", "err"), go = el("button", "btn gold", "Save as new version"); go.type = "submit";
    f.onsubmit = async e => { e.preventDefault(); err.textContent = ""; go.disabled = true; try { await post("/api/lab/prompts", { name: n.value, body: bt.value, change_note: note.value || undefined }); Z.$("drawer").close(); Z.toast("New version saved (inactive)", "ok"); await Z.rerender(); } catch (x) { err.textContent = x.message; go.disabled = false; } };
    add(f, n, bw, note, err, go); Z.openDrawer(name ? "New version of " + name : "New prompt", f);
  }

  async function view(v) {
    const p = await Z.api("/api/lab/prompts/" + v.id), box = el("div", "list"), pre = el("pre"); pre.textContent = p.body; pre.style.whiteSpace = "pre-wrap";
    add(box, Z.add(el("div", "meta"), pill("v" + p.version), pill(p.active ? "active" : "inactive", p.active ? "ok" : ""), pill(p.source)), pre);
    p.evals.forEach(e => add(box, Z.add(el("div", "item"), pill("score " + e.score), el("p", "sub", "Input: " + e.input), el("p", "sub", "Output: " + e.output), e.notes ? el("p", "sub", e.notes) : null)));
    Z.openDrawer(p.name + " v" + p.version, box);
  }

  async function compare(a, b) {
    const d = await post("/api/lab/compare", { a: a.id, b: b.id }), box = el("div", "list"), pre = el("pre");
    pre.style.whiteSpace = "pre-wrap"; pre.textContent = d.diff.join("\n") || "(no text difference)";
    add(box, Z.add(el("div", "meta"), pill("+" + d.added + " lines", "ok"), pill("-" + d.removed + " lines", "warn")), el("p", null, d.verdict), pre, d.diff_truncated ? el("p", "sub", "Diff truncated at 400 lines.") : null);
    Z.openDrawer("v" + d.a.version + " → v" + d.b.version, box);
  }

  async function prompts(root) {
    const { prompts: groups } = await Z.api("/api/lab/prompts");
    const top = card("Prompt Lab", "Prompts are versioned and never edited: a change is a new version. Scores are your own marks on real outputs. Nothing here runs a model.");
    top.append(Z.add(el("div", "row"), btn("New prompt", "gold small", () => newVersion()),
      btn("Register prompts/ai files", "ghost small", async () => { try { const r = await post("/api/lab/prompts/sync"); Z.toast(r.registered.length + " registered, " + r.drift.length + " drift", r.drift.length ? "bad" : "ok"); await Z.rerender(); } catch (x) { Z.toast(x.message, "bad"); } })));
    root.append(top);
    if (!groups.length) root.append(Z.none("No prompts registered", "Register the Command Center prompt file to bring it under version control."));
    groups.forEach(g => {
      const c = card(g.name, g.versions[0].purpose || "");
      g.versions.forEach((v, i) => {
        const it = el("div", "item"), prev = g.versions[i + 1];
        add(it, Z.add(el("div", "meta"), pill("v" + v.version), pill(v.active ? "active" : "inactive", v.active ? "ok" : ""), pill(v.source), pill(v.evals ? "avg " + v.avg_score + " (" + v.evals + " scored)" : "not scored")), v.change_note ? el("p", "sub", v.change_note) : null);
        const row = el("div", "row");
        row.append(btn("View", "ghost small", () => view(v)), btn("Add score", "ghost small", () => Z.formDialog("Score an output of v" + v.version, [["input", "Input you tried", "text", null, true], ["output", "Output you got", "text", null, true], ["score", "Score 1 (bad) to 5 (great)", "int", null, true], ["notes", "Notes", "text"]], b => post("/api/lab/prompts/" + v.id + "/evals", b))),
          btn("New version from this", "ghost small", async () => newVersion(g.name, (await Z.api("/api/lab/prompts/" + v.id)).body)));
        if (prev) row.append(btn("Compare with v" + prev.version, "ghost small", () => compare(prev, v)));
        if (!v.active) row.append(btn("Activate", "gold small", async () => { if (!confirm("Make v" + v.version + " the active " + g.name + " prompt?")) return; try { await post("/api/lab/prompts/" + v.id + "/activate"); await Z.rerender(); } catch (x) { Z.toast(x.message, "bad"); } }));
        it.append(row); c.append(it);
      });
      root.append(c);
    });
  }

  Z.pages.lab = {
    title: "Lab", sub: "Research, knowledge and prompt versions", icon: "plan",
    async render(root) {
      const wrap = el("div", "list"), tabs = el("div", "tabs"); tabs.setAttribute("role", "tablist");
      TABS.forEach(([k, label]) => { const b = el("button", null, label); b.type = "button"; b.setAttribute("role", "tab"); b.setAttribute("aria-selected", String(k === tab)); b.onclick = () => { tab = k; Z.store.set("z2r_lab_tab", k); Z.rerender(); }; tabs.append(b); });
      wrap.append(tabs);
      await (tab === "prompts" ? prompts : knowledge)(wrap);
      root.append(wrap);
    },
  };
})();
