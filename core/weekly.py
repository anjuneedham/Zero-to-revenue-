"""Weekly learning report: messages -> replies -> onboardings booked -> paid, by channel and by plan, plus what to do
next week. Pure counting over lead_touches and deals; the actions are fixed rules, never model output, and no number
here is estimated. Paid = a deal whose payment was verified. Deals carry no channel, so paid-by-channel uses the
channel the lead was first reached on (leads.channel); sent/replied/booked use the channel of each touch."""

from datetime import date, datetime, timedelta, timezone

from core import challenge

MIN_SAMPLE = 5  # messages on a channel before its reply rate means anything


def _since(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _by_channel(conn, since: str) -> list[dict]:
    rows = {}
    for r in conn.execute(
            "SELECT channel, count(*) FILTER (WHERE direction='out' AND outcome IN ('sent','no_reply')) AS sent, "
            "count(DISTINCT lead_id) FILTER (WHERE outcome='replied') AS replies, "
            "count(DISTINCT lead_id) FILTER (WHERE outcome='booked') AS booked "
            "FROM lead_touches WHERE created_at >= ? GROUP BY channel", (since,)):
        rows[r["channel"]] = {"channel": r["channel"], "sent": r["sent"], "replies": r["replies"], "booked": r["booked"], "paid": 0, "paid_usd": 0.0}
    for r in conn.execute(
            "SELECT COALESCE(l.channel,'other') AS channel, count(*) n, COALESCE(sum(d.amount_usd),0) s FROM deals d "
            "JOIN leads l ON l.id=d.lead_id WHERE d.status='paid' AND d.paid_at >= ? GROUP BY 1", (since,)):
        row = rows.setdefault(r["channel"], {"channel": r["channel"], "sent": 0, "replies": 0, "booked": 0, "paid": 0, "paid_usd": 0.0})
        row["paid"], row["paid_usd"] = r["n"], float(r["s"])
    for row in rows.values():
        row["reply_rate"] = round(row["replies"] / row["sent"], 3) if row["sent"] else None
    return sorted(rows.values(), key=lambda x: (-x["paid"], -x["replies"], -x["sent"]))


def _by_plan(conn, since: str, labels: dict) -> list[dict]:
    out = {}
    for r in conn.execute("SELECT venture, plan, count(*) FILTER (WHERE created_at >= ?) AS sold, "
                          "count(*) FILTER (WHERE status='paid' AND paid_at >= ?) AS paid, "
                          "COALESCE(sum(amount_usd) FILTER (WHERE status='paid' AND paid_at >= ?),0) AS paid_usd "
                          "FROM deals GROUP BY venture, plan", (since, since, since)):
        out[(r["venture"], r["plan"])] = {"venture": r["venture"], "plan": r["plan"], "label": labels.get((r["venture"], r["plan"]), r["plan"]),
                                          "deals_created": r["sold"], "paid": r["paid"], "paid_usd": float(r["paid_usd"])}
    for (v, k), label in labels.items():
        out.setdefault((v, k), {"venture": v, "plan": k, "label": label, "deals_created": 0, "paid": 0, "paid_usd": 0.0})
    return sorted(out.values(), key=lambda x: (x["venture"], x["plan"]))


def _next_actions(conn, ch: dict, week: list[dict]) -> list[str]:
    acts = []
    waiting = conn.execute("SELECT count(*) FROM leads WHERE stage='replied'").fetchone()[0]
    if waiting:
        acts.append(f"Answer the {waiting} lead(s) who replied and have not booked yet: replies are the scarcest thing you have.")
    unpaid = conn.execute("SELECT count(*) FROM deals WHERE status='open' AND created_at < ?", (_since(3),)).fetchone()[0]
    if unpaid:
        acts.append(f"Chase {unpaid} deal(s) open for more than 3 days: copy the PayPal message again and ask if anything is blocking them.")
    booked = conn.execute("SELECT count(*) FROM leads WHERE stage='onboarding_booked'").fetchone()[0]
    if booked:
        acts.append(f"Run the {booked} booked onboarding(s) and ask for the annual payment at the end of each.")
    due = len(ch["due"])
    if due:
        acts.append(f"Work the {due} lead(s) due today on the Challenge page (follow-ups and first messages).")
    sized = [c for c in week if c["sent"] >= MIN_SAMPLE and c["reply_rate"] is not None]
    if sized:
        best = max(sized, key=lambda c: c["reply_rate"])
        if best["replies"]:
            acts.append(f"Send more on {challenge_label(best['channel'])}: {best['replies']} replies from {best['sent']} messages "
                        f"({best['reply_rate']:.0%}) is your best channel this week.")
        for c in sized:
            if c["sent"] >= 2 * MIN_SAMPLE and c["replies"] == 0:
                acts.append(f"Change or drop {challenge_label(c['channel'])}: {c['sent']} messages, no replies. Rewrite the first line before sending more.")
    if ch["touches_week"] == 0:
        acts.append("No messages were logged this week. Log every message you send so this report can show what works.")
    if ch["state"] == "running" and ch["ahead_by_usd"] < 0 and ch["per_week_needed"]:
        acts.append(f"You are ${-ch['ahead_by_usd']:,.0f} behind pace: about {ch['per_week_needed']} paid deal(s) a week at ${ch['avg_deal_usd']:,.0f} closes the gap.")
    return acts or ["Nothing is stuck. Add new leads and keep logging messages."]


def challenge_label(channel: str) -> str:
    return (channel or "other").replace("_", " ")


def report(conn, days: int = 7) -> dict:
    ch = challenge.summary(conn)
    cfg = ch["config"]
    labels = {(v, p["key"]): p["label"] for v in challenge.VENTURES for p in challenge.plans(cfg, v)}
    week_since, start_since = _since(days), cfg["start"]
    week = _by_channel(conn, week_since)
    funnel_week = {k: sum(c[k] for c in week) for k in ("sent", "replies", "booked", "paid")}
    return {
        "days": days, "generated": datetime.now(timezone.utc).isoformat(),
        "cash_usd": ch["cash_usd"], "target_usd": ch["target_usd"], "state": ch["state"], "day": ch["day"], "total_days": ch["total_days"],
        "ahead_by_usd": ch["ahead_by_usd"], "funnel": funnel_week,
        "by_channel": week, "by_channel_to_date": _by_channel(conn, start_since),
        "by_plan": _by_plan(conn, week_since, labels), "by_plan_to_date": _by_plan(conn, start_since, labels),
        "next_week": _next_actions(conn, ch, week),
    }


def render_text(r: dict) -> str:
    f = r["funnel"]
    lines = [f"WEEKLY REPORT (last {r['days']} days)",
             f"Verified cash ${r['cash_usd']:,.0f} of ${r['target_usd']:,.0f}"
             + (f", day {r['day']}/{r['total_days']}, {'ahead of' if r['ahead_by_usd'] >= 0 else 'behind'} pace by ${abs(r['ahead_by_usd']):,.0f}" if r["state"] == "running" else f" ({r['state']})"),
             f"Funnel: {f['sent']} messages -> {f['replies']} replies -> {f['booked']} onboardings booked -> {f['paid']} paid", "", "BY CHANNEL (this week)"]
    lines += [f"- {challenge_label(c['channel'])}: {c['sent']} sent, {c['replies']} replied, {c['booked']} booked, {c['paid']} paid (${c['paid_usd']:,.0f})" for c in r["by_channel"]] or ["- no activity logged"]
    lines += ["", "BY PLAN (this week)"]
    lines += [f"- {p['venture']} {p['label']}: {p['deals_created']} deals created, {p['paid']} paid (${p['paid_usd']:,.0f})" for p in r["by_plan"]]
    lines += ["", "NEXT WEEK"] + [f"{i}. {a}" for i, a in enumerate(r["next_week"], 1)]
    return "\n".join(lines)


def iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"
