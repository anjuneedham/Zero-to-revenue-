# World Builders Construction: landing page (final build, pre-upload)

Static page (`index.html`) plus a PHP + MySQL lead backend for Hostinger. No build step.

```
index.html        the page (CSS + JS inline; config at the top of the <script>)
images/           optimised project photos from the client's Drive, logos, social share image
api/lead.php      receives enquiries: validates, rate-limits, saves to MySQL, emails the owner
api/config.sample.php   copy to config.php on the server (never committed)
admin/index.php   password-protected enquiry viewer: status, notes, search, CSV export
database/schema.sql     tables for hPanel > phpMyAdmin > Import
docs/HOSTINGER_SETUP.md step-by-step setup, MCP/API route, go-live checklist
.htaccess robots.txt sitemap.xml
```

## What changed in this version
- 18 real project photos in a filterable gallery (Roofing / Concrete & block / Finishing) with a keyboard- and swipe-friendly lightbox, plus a four-stage "first block to final coat" photo strip.
- Two new calls to action, repeated hero, services, mid-page band, mobile bar and nav: **Book a site visit** (opens the form pre-set to a site-visit request) and **Call now** (tap-to-call). Every click is pushed to `dataLayer` as `cta_click`.
- Form now posts to `api/lead.php`. If the server is unreachable the visitor is told so honestly and handed a prefilled WhatsApp message instead of a false "received".
- SEO: canonical, Open Graph / Twitter card, `GeneralContractor` structured data, robots and sitemap.

## Loader test (with vs without logo screen)
Visitors are split 50/50 and remembered. Force a variant with `?loader=on` or `?loader=off`. The variant is saved with every lead.

## Open items before go-live
1. **Phone numbers:** WhatsApp is 876-513-4962 (confirmed by the client by email) but the call links use 876-513-4942. Confirm which is right and search/replace `4942` in `index.html`.
2. **Client's two requested calls to action** were not written down anywhere we could find. "Book a site visit" and "Call now" were chosen; tell us if they meant something else (e.g. Download a brochure, WhatsApp-only).
3. **Site-visit fee:** still unconfirmed, so the page does not mention one.
4. **Business email** shown in the footer (`gayle.r.ricardo@gmail.com`): confirm it is the one to publish.
5. **Domain** is assumed to be `worldbuildersconstruction.com` (canonical, sitemap, share image URLs).
6. **Captions** on photos are descriptive only; have the client confirm they want these sites shown, and add testimonials and before/after shots when supplied.
7. Preview banner appears automatically on `*.vercel.app` and localhost only; it never shows on the live domain.
