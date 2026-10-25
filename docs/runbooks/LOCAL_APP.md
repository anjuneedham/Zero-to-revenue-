# Local app (works live too)

The local app is the same code as the live site. It talks to the same Neon database and uses the same owner
login, so anything you do here shows up live and the other way round. It binds to 127.0.0.1 only.

## One-time setup
1. `git clone https://github.com/anjuneedham/Zero-to-revenue-.git && cd Zero-to-revenue-` (branch `ccr-a240a1bc-iekqji`)
2. `pip install -r requirements.txt` (Python 3.12 or newer)
3. Copy `.env.example` to `.env.local` and set:
   - `DATABASE_URL`: Neon console > your project > Connection string (starts with `postgresql://`).
   - `OWNER_WALLET_ADDRESS` and `OWNER_WALLET_CHAIN_IDS` (the same values as in Vercel).
   - Optional: `OWNER_SKILLS`, `LLM_MONTHLY_BUDGET_USD`, `GITHUB_TOKEN`.
   `.env.local` is ignored by git. Never put it in chat, a ticket or a commit.

## Run
`python scripts/run_local.py` opens http://127.0.0.1:8080 with a LOCAL badge. `--port 9000` changes the port,
`--no-browser` skips opening the browser. Ctrl+C stops it.

## Install it like an app
In Chrome open the local address, then the install icon in the address bar (or menu > Install app). It then
opens in its own window. The live site installs the same way, and on a phone via the Chrome menu.

## Things to know
- Both copies write to one database. Agent runs triggered here or by the live daily job all land in the same place.
- The daily scheduler only runs on the live site. Locally, agents run when you press their buttons.
- If the database connection drops (Neon sleeps idle databases), the next click reconnects automatically.
- The launcher refuses to run on the live host and prints no secret values.
- Android APK: wrap the live HTTPS address with PWABuilder or Bubblewrap. You keep the signing key and back it up.
