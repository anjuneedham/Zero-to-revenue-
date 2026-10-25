# Improvement loop and 12-month plan

## Weekly loop (every Monday, ~30 min owner time)
1. **Measure** (dashboard + daily reports): verified revenue, revenue per owner-hour, revenue per approval,
   submit->accept rate, accept->paid rate, days to payment, Claude spend vs the $80 cap.
2. **Review losses**: every rejected/failed opportunity gets one line: why, and what rule would have caught it.
3. **Change one thing**: one scoring weight, one source, one prompt version, or one offer. Never several at once.
4. **Evaluate before shipping**: prompt and scoring changes run against `tests/` plus a labelled set of past
   opportunities (what we said vs what happened). A change ships only if it doesn't make that set worse.
5. **Version**: prompts live in `prompts/<agent>/<name>-vN.md`; the active version is recorded with every
   LLM call (`llm_usage.purpose`) so results can be compared by version.
Guardrail: the loop may tune ranking, sources, prompts and offers. It may never loosen `core/policy`
(spending, signing, approvals). That stays a human decision (spec section 35).

## Stage gates (move on only when the gate is met)
| Months | Engine | Target revenue/month | Gate to advance |
|---|---|---|---|
| 1-2 | Bounties + small freelance via Scout/Operator | $1k-2k | 3 verified payments; know which source pays |
| 3-4 | "Never Miss a Job" for trades contractors (see docs/strategy/INVESTOR_THESIS.md) | $3.5k-5k | 2 paying clients from one repeatable offer |
| 5-6 | Retainers (monthly maintenance/agent ops) | $6.5k-8k | 3 retainers, churn 0 |
| 7-9 | Agent-as-a-service + referral partners; subcontract delivery | $9.5k-12k | delivery not limited by owner hours |
| 10-12 | Scale what works; paid acquisition only from verified profit | $13k-15k | CAC paid back within 1 month |
Cumulative at plan targets: ~$100k in 12 months. This is a target, not a forecast; each gate decides whether
the next stage is worth it.

## Budget
Claude cap: **$80/month** (`LLM_MONTHLY_BUDGET_USD=80`, enforced in `core/budget.py`). Raise it only when
revenue per Claude dollar is measured and positive.
