# Master plan: Zero to Hero OS for multiple ventures (28 Oct 2026)

## 1. Principle
One OS, many ventures, **one venture gets the main push at a time**. Revenue is only what Treasury verifies
(PAYMENT_VERIFIED). Everything else is a hypothesis with an owner, a deadline and a kill criterion.

## 2. Priorities (ranked)
1. **BuildFlow**: sell it by hand to 10 founding contractors (manual billing). ~50% of effort.
2. **Agriloop**: make it production-safe (real data source), then pilot with a handful of real farmers/buyers. ~20%.
3. **E-commerce**: one brand, one product, one paid-traffic test with a hard spend cap. ~20%.
4. **Trading**: research only. Backtest + paper journal; no live money. ~10%.

## 3. Weekly allocation (from HANDOFF; one chat per day, touches only that venture)
Mon BuildFlow, Tue Agriloop, Wed trading, Thu e-commerce, Fri BuildFlow growth, Sat Agriloop growth, Sun OS review.
Encoded in the OS as `venture_allocation` (migration 007) so the Ventures page can show planned vs logged effort.
Claude usage is self-reported (`effort_logs`), never enforced.

## 4. Gates (a venture moves to the next stage only when the evidence exists)
| Stage | Gate to enter |
|---|---|
| BUILD | founder decision logged |
| VALIDATE | product usable by a stranger (BuildFlow: storage + legal; Agriloop: persistent data) |
| SELL | 3 real conversations booked |
| SCALE | first PAYMENT_VERIFIED customer + 1 repeatable channel |
| KILL | kill criterion in the venture doc is met; decision logged, not silently dropped |

## 5. Roadmap
| Phase | Deliverable | State |
|---|---|---|
| 0 | Audit + handoff | Done |
| 1 | These docs | Done |
| 2 | OS venture workspace: migration 007 (ventures, venture_tasks, decisions, experiments, metrics, effort_logs, venture_allocation), `/api/ventures*`, Ventures page, MCP-safe read model, stale-doc banners | This session |
| 3 | Daily venture chats working each venture doc's roadmap | Next |
| 4 | BuildFlow sidekick (screenshots/fit scoring) | Needs `ANTHROPIC_API_KEY` |
| 5 | Customers table + PayPal anchoring (replace synthetic `opp_manual_*`) | After first paying customer |

## 6. Rules the OS enforces (unchanged)
Approval gate on outreach/submissions, kill switch, append-only audit, no secrets, no trading/spending/signing,
external text is untrusted. New in phase 2: every venture write is audited; metrics and experiment results are
owner-entered or agent-entered and labelled with their source, and never counted as revenue.

## 7. Risks
Spreading thin across 4 ventures; trading losses (mitigated by ban); founder time; unverified assumptions in
venture repos (listed per venture); Gmail token expiry; cold email deliverability.
