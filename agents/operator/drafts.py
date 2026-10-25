"""Deterministic plans and drafts. Never invents experience, results or testimonials:
anything only the owner knows is left as an explicit [OWNER TO FILL] placeholder."""

FILL = "[OWNER TO FILL]"


def plan(opp: dict) -> list[str]:
    steps = [
        f"Re-read the source page and confirm it is still open: {opp['source_url']}",
        "Confirm eligibility, deadline and payment terms on the source itself (not on third-party copies).",
        "Reproduce or scope the problem locally; note anything that needs access you do not have.",
        "Prepare the deliverable and its tests in a sandbox; nothing is published or submitted automatically.",
        "Owner reviews the draft, signs in to the platform and submits.",
        "Record proof of submission; Treasury then watches for payment.",
    ]
    if opp.get("missing_information"):
        steps.insert(1, f"Resolve missing information first: {opp['missing_information']}")
    return steps


def draft(opp: dict) -> str:
    pay = f"{opp['expected_payment']} {opp.get('payment_asset') or ''}".strip() if opp.get("expected_payment") else "not stated"
    lines = [
        f"# DRAFT submission: {opp['title']}",
        "",
        "Status: DRAFT prepared by the Operator agent. Not submitted. Requires owner review.",
        "",
        "## Opportunity",
        f"- Source: {opp['source_url']}",
        f"- Organization: {opp.get('organization') or 'unknown'}",
        f"- Claimed payment (unverified): {pay}",
        f"- Deadline: {opp.get('deadline') or 'not stated'}",
        f"- Risk flags: {opp.get('scam_indicators') or 'none'}",
        "",
        "## Proposed approach",
        "1. Summarise the request in my own words and confirm scope with the maintainer if anything is unclear.",
        "2. Implement the smallest change that fully solves it, with tests.",
        "3. Document how to verify the change.",
        "",
        "## Message to the maintainer (edit before sending)",
        f"Hi, I'd like to work on \"{opp['title']}\". My plan: {FILL} (one or two sentences, in your own words).",
        f"Relevant experience: {FILL} (only real experience; leave out if none).",
        f"Payout address / method: {FILL} (confirm the network with the payer first).",
        "",
        "## Owner checklist before submitting",
        "- [ ] The source page is genuine and still open",
        "- [ ] No fee, deposit, wallet connection or private information is requested",
        "- [ ] Every [OWNER TO FILL] is replaced or removed",
        "- [ ] The work is tested and actually done",
    ]
    return "\n".join(lines)
