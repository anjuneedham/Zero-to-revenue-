# World Builders Construction: landing page (v1 draft)

Static single page, no build step. Open `index.html` or deploy the folder to any static host.

## Loader test (with vs without logo screen)
- Visitors are split 50/50 and remembered. Force a variant with `?loader=on` or `?loader=off`.
- The variant is pushed to `dataLayer` and stored on every lead (`variant` field), so conversion can be compared.

## Lead capture
- 3-step funnel, then a thank-you with a prefilled WhatsApp handoff (876-513-4962), so no lead is lost.
- Set `CFG.endpoint` in `index.html` (Formspree / Web3Forms / own API) to receive each lead by email.
- Leads are also saved in the visitor's browser as a fallback; this is not a server-side record.

## To finish before launch
- More project photos (see `GALLERY` array in `index.html`), testimonials, before/after shots.
- Confirm site-visit fee wording (not yet stated on the page).
- Domain: worldbuildersconstruction.com. Confirm the business email to publish.
