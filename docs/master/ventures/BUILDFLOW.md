# BuildFlow (venture doc)
Repo `buildflow` · live https://buildflow-app-beta.vercel.app · stage: BUILD → VALIDATE · priority 1.

## Report
Customer/project management SaaS for construction pros plus a public profile customers can use to hire them. $50/mo, 14-day trial. Next.js 16, Firebase `build-6fa95`, Capacitor Android shell. Own report (25 Oct): NOT READY. *(handoff; suites not re-run)*

## Audit / risks
Storage not provisioned (uploads fail); legal pages are placeholders; never run on a real prod Firebase project; billing is a stub (Stripe unavailable in Jamaica); no push/email notifications; no validated demand; Vercel Hobby is non-commercial. Competitor: ClickAway.

## MVP scope (sellable beta)
Customer + project records, public profile, quote requests, photo upload, manual billing (PayPal/bank transfer, marked paid by admin). Out of scope for now: Play Store, chat, automated billing.

## Roadmap (take the first unchecked item)
- [ ] Founder: enable Firebase Storage (Blaze + budget alert), deploy storage.rules
- [ ] Founder: real company details + legal review; set the legal env vars
- [ ] Decide manual billing route for first 10 contractors; add paid-until field
- [ ] Move Vercel project to Pro before charging
- [ ] Re-run the repo's own unit/rules/e2e suites and record the result
- [ ] Sign 10 founding contractors (free 60 days for feedback, photos, testimonial)
- [ ] Push notifications for new leads
- [ ] Real-phone Android test; keystore backed up

## Growth plan
Founder sells directly: WhatsApp/DM/phone to Jamaican trades; each signed contractor shares their profile link/QR with their customers. Log every touch and outcome as OS experiments. Tiers to test: $50/mo; done-for-you setup $750-1,500; retainer $300-1,000/mo.

## Metrics (enter weekly)
contractors_contacted, replies, demos, trials, paying (verified via Treasury), weekly_active_contractors, jobs_created, price_objection_count.

## Acceptance criteria
- A stranger can sign up, create a customer + project, upload a photo on production.
- 10 founding contractors signed; at least 3 say yes to paying $50 (or a logged alternative price).
- First payment recorded and PAYMENT_VERIFIED in Treasury.
**Kill/pivot criterion:** 30 real contractor conversations with 0 willingness to pay at any tested price → stop selling the SaaS, log the decision, pivot to done-for-you service.
