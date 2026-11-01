# Hillside: moving it

Everything is plain static files. No build step, no server, no database.

## Move the site
Copy this folder to any static host (Vercel, Netlify, Cloudflare Pages, GitHub Pages, an S3 bucket).
Keep the headers from `vercel.json` if the host lets you set them (CSP, no-index, no-frame).
Users reinstall from the new address. Data lives on each device, so nothing is lost by moving the site.

## Move the data (device to device)
Settings, "My plan and reasons":
- "Download a backup file" (installed app) or "Copy a backup of my data".
- On the new device, paste it into "Restore from a backup".

Backup format (JSON, versioned):

    { "app": "hillside", "schema": 2, "exportedAt": "...",
      "profile": { quitDate, baseline, maxPush, reasons, trusted, helpline, updated },
      "days": { "YYYY-MM-DD": { smokes, cravings, beaten, mood, sleep, workout, note,
                                low, app, task, taskDone, updated } } }

Older backups (no `schema`, separate `grabba` and `weed` counts) import fine: the larger of
the two becomes `smokes`. Restore merges by the `updated` timestamp, newest wins.

## How data is stored on the device
`localStorage["hillside.v2"]` holds one AES-GCM encrypted blob. The key comes from the PIN
(PBKDF2, SHA-256, 600,000 rounds, random salt). The PIN is never stored. Wrong guesses are
counted and slow down (3 tries: 30 s, 5: 5 min, 8: 1 hour).

## Add sync later without touching the app
Define `window.HILLSIDE_REMOTE` before the main script runs:

    window.HILLSIDE_REMOTE = {
      pull: async () => ({ profile, days }),     // newest `updated` wins on merge
      push: async (key, data) => { /* key is "profile" or a date; data is that document */ }
    };

Data passed to `push` is plain. Encrypt it yourself first if the server should not read it.
Any store works (Supabase, SQLite, a file). One row per day plus one profile row maps directly.
