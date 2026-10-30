---
name: visual-model
description: Build a visual web page (flow, timeline, checklist, review pack, call script) so the founder and collaborators can see a plan instead of reading it. Use when asked to "show", "map", "visualise", "make a page for", or turn a markdown plan, draft, or process into something visual. Repo-specific to the Founder OS and its ventures (Agriloop, BuildFlow).
---

# Visual model builder

The founder learns visually, and so do the people they work with (partners, creators, farmers, contractors). Turn plans into pages
that can be scanned in 30 seconds.

## When to use
- A markdown plan, agreement, or process needs to be understood, reviewed, or presented to a non-technical person.
- Preparing for a call: build the flow they will talk through.
- Any "what do I need to update/check" request: surface the focus points visually.

## Workflow
1. **Source of truth stays in markdown** under `docs/master/ventures/<venture>/`. Never edit the page by hand to change facts; change the md, rebuild.
2. **Build the page** with `scripts/visual_pack.py <folder> <out.html>` for review packs (it highlights every `[bracket]` placeholder
   as a focus point and builds a per-document checklist). For other visuals, write the HTML directly with the patterns below.
3. **Save the HTML** to `docs/visual/<name>.html` so it is versioned, then publish it as an Artifact (private by default). Share the link only if asked.
4. **Report** in one or two lines: what the page shows and what the reader must do next.

## Visual patterns (pick the one that matches the job)
| Job | Pattern |
|---|---|
| Needs updating or checking | Focus-point chips (yellow marker) on each placeholder, a checklist per document, progress count |
| A process or call | Numbered step cards left-to-right (wrapping on phones), each with time and a one-line goal |
| A plan over time | Timeline rows with dates, owner, and a done/blocked status pill |
| A decision | Two or three option columns with a recommended one marked |
| Money or numbers | Simple chart drawn to scale, with the source named under it |

## Design rules
- Plain language, short sentences, no jargon. Name things the way the reader does ("farmer", "order", "invoice").
- One job per page. Summary first, detail below. Status shown with shape and label, not colour alone.
- Works on a phone at 400px with no sideways scroll; readable in light and dark themes.
- Mark every draft clearly as DRAFT. Never present invented figures, names, or legal conclusions as fact; label estimates and unknowns.
- No personal data, secrets, keys, or private contact details in a page. Placeholders stay as `[bracket]` text.
- Legal documents: always keep the "not legal advice" note on the page.

## Guardrails
- Do not publish publicly or send to anyone unless the user asks; artifacts start private.
- Do not hold or imply payments: the platform takes no money and holds no funds until the legal review is complete.
