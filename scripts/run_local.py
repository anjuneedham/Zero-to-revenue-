#!/usr/bin/env python3
"""Run the Zero-to-Revenue app on your own computer.

Same code, same database and same owner login as the live site, so what you do here shows up live
and vice versa. Settings come from .env.local (git ignores it). Binds to 127.0.0.1 only.

    python scripts/run_local.py            # opens http://127.0.0.1:8080
    python scripts/run_local.py --port 9000 --no-browser
"""

import argparse
import os
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import envfile  # noqa: E402


def check_env() -> list[str]:
    """Returns human-readable problems; empty list means good to go."""
    problems = []
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith(("postgres://", "postgresql://")):
        problems.append("DATABASE_URL is missing. Copy .env.example to .env.local and paste your Neon connection string "
                        "(Neon console > your project > Connection string). It must start with postgresql://")
    if not os.environ.get("OWNER_WALLET_ADDRESS"):
        problems.append("note: OWNER_WALLET_ADDRESS is not set, so Treasury will show no wallet (the app still runs).")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--env-file", default=str(ROOT / ".env.local"))
    args = ap.parse_args(argv)

    loaded = envfile.load(args.env_file, os.environ)
    print(f"Loaded {len(loaded)} setting(s) from {Path(args.env_file).name}" if loaded else f"No {Path(args.env_file).name} found; using environment only")
    if os.environ.get("VERCEL"):
        print("This looks like the live host; run_local.py is for your own computer.")
        return 2
    problems = check_env()
    fatal = [p for p in problems if not p.startswith("note:")]
    for p in problems:
        print(("ERROR: " if p in fatal else "") + p)
    if fatal:
        return 1

    from dashboard import app  # imported after env is loaded

    url = f"http://127.0.0.1:{args.port}"
    if not args.no_browser:
        threading.Thread(target=lambda: (time.sleep(1.2), webbrowser.open(url)), daemon=True).start()
    print(f"Zero-to-Revenue (LOCAL) running at {url}  - press Ctrl+C to stop")
    try:
        app.serve("127.0.0.1", args.port)
    except KeyboardInterrupt:
        print("\nStopped.")
    except OSError as e:
        print(f"Could not start on port {args.port}: {e}. Try --port 9000.")
        return 1
    except Exception as e:
        print(f"Could not start: {type(e).__name__}. Check DATABASE_URL (is the Neon database awake and the string complete?).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
