# E-commerce (brand undecided)

Evidence source: docs/master/HANDOFF.md (verified 28 Oct 2026). Claims not re-verified this chat are marked UNVERIFIED.

## Report
- **The brand is undecided. There is no fashion brand repo.** (Checked: Tonysperformance = mechanic site, Convoy-supply = cab storage, Theo-s- = empty; `Echo-Ai` is private and inaccessible.)
- Two existing, non-fashion storefronts:
  - `Kadeform-`: Shopify/Dawn theme, single hero product (FlexBack Pro lumbar support), 446 files.
  - `NF-Fragrance-`: static Netlify site, five colognes, 24 files.
- UNVERIFIED: whether either is live, has traffic, or has orders.

## Audit
1. No brand decision, so no positioning, name, or domain commitment.
2. Neither storefront has recorded sales, traffic or margin data in evidence.
3. Supplier, unit cost, shipping and returns terms are undocumented.
4. Payment/checkout status unknown for both. UNVERIFIED.

## Risks
- Building before choosing a brand wastes effort across two or three directions.
- Inventory or ad spend before demand is validated.
- Fragrance and health-adjacent products (lumbar support) carry claims/regulatory and returns risk. UNVERIFIED which rules apply.
- Dropship dependence: margin and delivery times outside the founder's control.

## MVP scope
In: a founder decision on the brand (see options), one hero offer, one landing/product page, a checkout that works, a margin sheet, 10 validated visitor-to-purchase tests.
Out: multi-product catalog, brand-building content, paid scaling, fashion line until a fashion repo exists.

## Brand decision (Thu, first task)
| Option | Pros | Cons |
|---|---|---|
| Kadeform- (FlexBack Pro) | Real Shopify store, single hero product = simple | Product claims risk; 446-file theme to maintain |
| NF-Fragrance- | Small static site, quick to change | Static: needs checkout added; five SKUs dilute focus |
| New fashion brand | Matches stated intent | Nothing exists; highest effort |

Recommendation: choose one existing storefront and test demand before creating anything new. Founder decides.

## Roadmap
| Step | Work | Day |
|---|---|---|
| 1 | Founder picks the brand | Thu |
| 2 | Margin sheet: cost, price, shipping, fees, returns | Thu |
| 3 | Confirm checkout works end to end with a test order | Thu |
| 4 | One offer + one landing page; small organic/test-traffic run | Thu |
| 5 | Review conversion; kill, fix or scale | Sun |

## Growth plan
Organic first (founder network, short-form content, communities); small paid test only after checkout works and unit margin is positive. No spend beyond a fixed test budget set by the founder.

## Metrics
Visitors, add-to-cart rate, conversion rate, AOV, gross margin per order, refund rate, spend and revenue per test.

## Acceptance criteria
- [ ] Brand chosen and recorded in the OS `decisions` table
- [ ] Margin sheet shows positive unit margin after fees and shipping
- [ ] Test order completes checkout, payment and fulfillment path
- [ ] First 10 visitors-to-purchase test recorded with conversion data
- [ ] Kill/scale rule written before any ad spend
