# Master Plan (draft, 28 Oct 2026)

Weekly rhythm (from HANDOFF): Mon BuildFlow, Tue Agriloop, Wed trading, Thu e-commerce, Fri BuildFlow growth,
Sat Agriloop growth, Sun OS review. One venture folder per chat.

## Priorities to 15 Nov
1. **Agriloop launch (hard date 15 Nov).** Cut scope to what can honestly ship:
   - By 31 Oct: decide data layer (Firestore on the BuildFlow Firebase setup vs. finishing Supabase) and verify the
     live `AGRILOOP_DATA_SOURCE`. No build before this is decided.
   - By 7 Nov: persistent data layer, auth, listings and browse working with real data; smoke tests added.
   - By 12 Nov: payments either live (one provider) or launch with manual/offline payment and say so.
   - 13-14 Nov: deploy, legal pages, rollback plan. Slip the date rather than ship in-memory data.
2. **BuildFlow:** provision Firebase Storage, replace legal placeholders, run the existing suites against prod
   Firebase. Same payment decision as Agriloop.
3. **Gmail token (before 2 Nov, low effort):** reissue token or publish the OAuth app; otherwise outreach sends stop.
4. **Choice-Yaad n Abroad (research only until 15 Nov):** write the brand brief in `ventures/ECOMMERCE.md`:
   diaspora audience, product category, distinct style, pricing, fulfilment, name/domain check. No build yet.
5. **Trading:** paper-trade/backtest only; no live capital until there is a journal with statistics.

## Phases
- **Phase 0 (now):** this audit + plan, per-venture docs `docs/master/ventures/{BUILDFLOW,AGRILOOP,TRADING,ECOMMERCE}.md`.
- **Phase 1:** OS tables `ventures`, `tasks`, `decisions`, `experiments`, `metrics` (reversible migration 007),
  venture-scoped views, weekly-allocation page. Keep Python/Neon/Vercel.
- **Phase 2:** BuildFlow sidekick work (needs `ANTHROPIC_API_KEY`).

## Honest constraints
Claude usage cannot be read or enforced by the app; allocation is a plan plus self-reported usage. Revenue
counts only when verified (existing Treasury rules).

## Next chat
Per HANDOFF step 2: write the four venture docs, starting with AGRILOOP (nearest deadline).
