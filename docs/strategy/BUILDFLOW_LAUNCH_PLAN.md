# BuildFlow: path to launch

Read from the BuildFlow repo (branch `claude/buildflow-v1`) on 25 Oct 2026. The same list is live in the dashboard under Game plan > BuildFlow launch, where items can be ticked off.

**Where it stands.** BuildFlow is live in beta at https://buildflow-app-beta.vercel.app: customer and project management for contractors, a public profile where customers find them, $50/month with a 14-day trial. Its own latest report says NOT READY, with one owner-side blocker (Firebase Storage). Billing is a stub: the price is displayed but nothing charges or enforces the trial, and Stripe is not available in Jamaica. Not yet validated with real contractors. Test counts in its reports: 32 unit, 3 rules, 9 integration, hundreds of attack probes, all run on emulators or the staging project.

| Priority | Who | Item | Why / how | Source |
|---|---|---|---|---|
| P0 | You | **Turn on Firebase Storage** | Needs the Blaze plan (a card), a budget alert, then Storage > Get started and deploy storage.rules. Until this is done every photo and file upload fails: posts, portfolio, job photos. Check that Google accepts your card; prepaid cards are sometimes refused. BuildFlow's own reminder is set for 31 Oct. | Integration test report, P0-3 |
| P0 | Both | **Decide how contractors pay (Stripe is not available in Jamaica)** | Billing is a stub: $50/month is displayed but nothing charges or enforces the trial. For the first 10 founding contractors use bank transfer or PayPal invoices and mark them paid in the admin screen. Then choose WiPay or PayPal subscriptions. Once you choose, I can build trial enforcement and a paid-until field. | V2 audit; strategy section 6 |
| P0 | You | **Add real company details and get the legal pages reviewed** | Production refuses to start until support email, company name, address, governing law and NEXT_PUBLIC_LEGAL_REVIEWED=true are set. The Privacy Policy and Terms still contain placeholders. I can draft wording; a lawyer must review it. | Production readiness report, C4 |
| P0 | You | **Move BuildFlow's Vercel project to Pro before charging** | Hobby is non-commercial. Set the production environment variables at the same time (Firebase values, service account key as a secret, legal and support variables). | Integration test report, P2-5; Firebase checklist |
| P1 | You | **Choose the production Firebase project and deploy it properly** | Decide build-6fa95 or buildflow-prod. Enable Email/Password, add the Vercel domain to authorised domains, set the email sender name, deploy rules, indexes and storage, turn on daily backups. Seed reference data on any new project before anyone signs up. | Firebase production checklist |
| P1 | Both | **Add push notifications for new leads** | Without them a contractor never hears about a lead unless the app is open, the main reason a tester would stop using it. You register the Android app in Firebase; I add google-services.json and the push plugin. | Integration test report, P1-1 |
| P1 | You | **Run the Android app on a real phone** | Check the photo picker, PDFs, back button, offline launch and Android 15 layout. The app has never run on a device. | Readiness report, C1; P2-6 |
| P1 | You | **Create the Android upload keystore and back it up** | Keep it outside git. Losing it means you cannot update the app. Set CAP_SERVER_URL to the production address. | Firebase checklist, Android |
| P1 | Both | **Prepare the Google Play listing** | 512px icon, 1024x500 feature graphic, at least 2 phone screenshots, short and full descriptions, category, content rating, Data safety form, reviewer test account. I can draft the texts. Check Play Console for the current closed-testing tester requirement for new accounts. | Google Play closed-test checklist |
| P1 | You | **Sign 10 founding contractors (your strongest skill)** | Free for 60 days in exchange for feedback, a set of job photos and a testimonial. Pitch: your leads are yours, one flat monthly price, WhatsApp-first. Share each contractor's profile link or QR with their own customers, since a directory has no value without both sides. | Product strategy, cold-start plan |
| P1 | You | **Test the price with real contractors** | $50/month including 1 user, +$20 per extra user, is a bet and has not been validated. Ask each founding contractor: would you pay this, in USD or JMD, and is a cheaper solo tier needed? | Product strategy, open questions |
| P2 | You | **Study ClickAway, the Jamaican competitor** | A local matching app with job bidding and payments, reported at about 2,800 beta users. BuildFlow's angle: leads are yours, flat price, built for the field. | Competitive reverse engineering |
| P2 | Both | **Decide on messaging** | Private client link or in-app chat. Today customers contact contractors by quote request, phone or WhatsApp. | Integration test report, P2-1 |
| P2 | Agent | **Hardening: error monitoring, photo thumbnails, Content-Security-Policy** | Agent work once the P0 items are clear: Sentry-style monitoring, thumbnails once Storage is on, and a CSP header. | Integration test report, P2-2 to P2-4 |

## Go-to-market (your strongest skill)
1. Sign 10 founding contractors: free for 60 days in return for feedback, job photos and a testimonial.
2. Pitch: your leads are yours, one flat monthly price, WhatsApp-first, built for the field.
3. Share each contractor's profile link or QR with their own customers; a directory has no value without both sides.
4. Ask every contractor: would you pay $50/month, in USD or JMD? Is a cheaper solo tier needed?
5. Study ClickAway (Jamaican competitor, about 2,800 beta users) and position against it.

## Order of work
P0 (Storage, billing decision, legal, Pro hosting) -> sign founding contractors with manual billing -> P1 hardening and Play listing -> automate billing -> P2.
