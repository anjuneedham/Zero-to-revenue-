# Skills vetting report (2026-10-30)

Why this exists: a skill is **instructions an AI follows plus, sometimes, scripts it can run**. A poisoned skill is a way into your files, accounts and (for the trading goal) your money. So nothing was installed on trust.

## How candidates were found

Repositories were found by web search and by starting from `anthropics/skills` and the Agent Skills standard repo (`agentskills/agentskills`: spec and reference SDK under Apache-2.0 / CC-BY, it contains **no skills to vendor**; its rules for `name`/`description` are enforced by `scripts/skills/verify_skills.py`). Each candidate repo was shallow-cloned into a scratch folder (nothing executed) and every `SKILL.md` indexed (11,025 skills across 19 clones). GitHub's own search API was not used, only public `git clone`.

Licence gate first: **MIT, Apache-2.0, BSD, CC-BY only, and a licence file must exist**. Unlicensed or proprietary = rejected before reading further.

## How each candidate was vetted

86 candidate skills (every file in each folder, 751 files) went through:

1. **Static pattern scan of every file** (`scripts/skills/vet_skill.py` is the reusable version): network calls, `eval`/`exec`/subprocess, base64 or long encoded blobs, secrets/env/key words, order-placement words, destructive file/git commands, package installs, prompt-injection phrases, URLs, binaries, symlinks, hidden/bidirectional Unicode.
2. **AST audit of every Python script** (65 `.py` files in the final 70): all third-party imports, dynamic execution, process and file-destructive calls. Result: no `eval`/`exec`/`compile`/`__import__`; network libraries appear only in the rejected skills; third-party imports in the kept set are limited to numpy, pandas, scipy, pytest, PyYAML, FastAPI/pydantic (a template) and sibling modules.
3. **Manual reading** of every flagged line, every script-level hit, the subprocess/HTTP/kill code in `mt5-robot-tester` and `skill-creator`, the two non-Python scripts (`find-polluter.sh`, a TypeScript example), and each skill's frontmatter. Descriptions were parsed with a real YAML parser.
4. **Byte-for-byte check** that every installed folder equals the pinned upstream commit (only a `LICENSE` file was added where a skill had none; 67 of 70).

**Honest limits.** I did not read every line of every Markdown reference file (hundreds of documents); those were checked by the pattern scan for injection phrases, hidden characters, telemetry words and key requests, and the flagged lines were read. Static scanning cannot prove a script is harmless; it reduces risk. Nothing was executed. Re-run `vet_skill.py` and re-read any script before you ever run it, and re-vet after every upstream update.

## Installed set: findings worth knowing

| Skill | Finding | Verdict |
|---|---|---|
| `mt5-robot-tester` | Runs `terminal64.exe` Strategy Tester through argv-list `subprocess` (no shell); local dashboard bound to `127.0.0.1` with CSRF and Host checks; stdlib only; backtests only, refuses to auto-pick a live terminal. Default pass gates (profit >=4x deposit, drawdown <=12%) invite overfitting. | Kept, with warning |
| `skill-creator` | `run_eval.py` and `improve_description.py` call `claude -p` (model calls); `generate_review.py` kills any process listening on its own port and starts a local web server. Official Anthropic, Apache-2.0. | Kept, run only with approval and after an API key exists |
| `ad-creative`, `social`, `video` | Reference text contains optional `curl` / `git clone` / `npx` recipes for third-party tools (Gemini, ElevenLabs, Hacker News, Reddit, Remotion). No scripts. | Kept, never run without approval |
| `trade-journal`, `risk-management`, `kelly-criterion`, `strategy-framework` | Crypto/Solana-flavoured examples; scripts are offline calculators. | Kept; adapt to your market |
| `position-sizer` | US stock / FINRA oriented text; offline stdlib maths. | Kept |
| `pdf` | From `openai/skills`; ships its own Apache-2.0 LICENSE.txt and an inert Codex `agents/openai.yaml`. | Kept |
| `neon-postgres` | Refers to sibling Neon skills (`neon`, `neon-realtime`) that are not installed. | Kept, informational |

## Rejected (with reasons)

### Skills rejected on security / suitability
| Skill | Source | Reason |
|---|---|---|
| `shopify` | Shopify/shopify-ai-toolkit (MIT) | Ships **usage telemetry** (`track-telemetry.sh/.ps1`, `log_skill_use.mjs`, `log_feedback.mjs` post to `shopify.dev`), minified `.mjs` validators, 145 files incl. 94 binary files. Cannot be audited and phones home. (All other Shopify toolkit skills sit under `deprecated/`.) |
| `slippage-modeling` | agiprolabs/claude-trading-skills | Scripts make live HTTP calls to `quote-api.jup.ag` (Solana DEX) and are crypto/Solana specific. |
| `ohlcv-processing` | agiprolabs/claude-trading-skills | Calls Birdeye API and expects `BIRDEYE_API_KEY` (asks for a secret). |
| `portfolio-manager` | tradermonty/claude-trading-skills | Brokerage (Alpaca) connection scripts and order/position tooling; trading skills must never hold broker keys by default. |
| `drawdown-circuit-breaker`, `pre-trade-discipline-gate`, `trade-performance-coach` | tradermonty/claude-trading-skills | Not self-contained: load a sibling module (`trader-memory-core/scripts/thesis_store.py`) via `importlib` and use a US-equity calendar. No unsafe behaviour found, but they break standalone. The drawdown rule is covered in `trading-lab` instead. |

### Skills rejected on licence
| Skill | Source | Reason |
|---|---|---|
| `docx`, `pdf`, `pptx`, `xlsx` | anthropics/skills | Proprietary: "All rights reserved ... governed by your agreement with Anthropic". Not open source. |
| `doc-coauthoring` | anthropics/skills | No licence file in the folder and none at the repo root. |
| `vercel-react-best-practices` (+ the rest of the repo) | vercel-labs/agent-skills | Repo has **no LICENSE file** (frontmatter says `license: MIT` with no text or holder). Re-check later; it is useful for Next.js. |

### Repositories not used
| Repository | Reason |
|---|---|
| ComposioHQ/awesome-claude-skills | No LICENSE file at the repo root, so it fails the licence gate. |
| sickn33/antigravity-awesome-skills | MIT, but a 8,851-skill re-hosted aggregate; the original authors' licences cannot be verified from it. Used primary sources instead. |
| K-Dense-AI/claude-scientific-skills | MIT, but scientific/biomedical; nothing matched the goals. |
| openai/skills | No root licence; only `pdf` used (it has its own Apache-2.0 LICENSE.txt). |
| agentskills/agentskills | Spec and SDK only, no skills. |
| VoltAgent/awesome-agent-skills | A link list; no code to vendor. |
| alpacahq/skills | Clone failed (not publicly reachable). |

### Vetted and passed, but dropped to keep the set at 70 (redundancy)
`signup`, `ideal-customer-profile`, `value-proposition`, `executive-mentor`, `rfp-responder`, `e2e-testing-patterns`. They are safe to add back with `scripts/skills/install_skill.py`.

## Coverage gaps (stated, not padded)

- **DOCX / XLSX / PPTX generation**: no permissively licensed open-source skill was found (Anthropic's are proprietary). The Claude app may offer built-in versions; they are not vendored here. Slots moved to engineering (+1) and SaaS (+1) instead of padding.
- **Spreadsheet tracking**: none found; `investing-plan` ships CSV templates instead.
- **Fashion**: no fashion- or Shopify-store-operations skill passed. Fashion (9) is covered by marketing skills (ads, creative, email/SMS, social, video, influencers, competitors) plus the custom `fashion-launch`. No inventory/margins skill exists upstream; the maths is in `fashion-launch`.
- **Trading**: nothing open-source covers Deriv synthetics or MQL5 development; `mt5-robot-tester` is the closest. Crypto-flavoured skills were kept only where the maths is generic.
- **Support / customer service**: only `customer-success-manager`.
