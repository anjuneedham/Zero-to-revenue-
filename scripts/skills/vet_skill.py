#!/usr/bin/env python3
"""Static security scan of a skill folder BEFORE you vendor it. Never executes anything; stdlib only.

    python3 scripts/skills/vet_skill.py /path/to/skill [--detail]

It flags (and you must then READ the flagged lines and every script yourself):
  NET      network calls          EXEC   dynamic execution / subprocess      OBFUS  encoded or obfuscated blobs
  SECRET   env vars / key words   ORDER  trading or order-placement words     FSDEL  destructive file/git commands
  INSTALL  runtime package installs  INJECT  prompt-injection style phrases   plus: URLs, binaries, symlinks, hidden unicode.
Rejection rules: exfiltration, calls to unknown URLs, telemetry, obfuscation, asking for keys/secrets, hidden characters,
live-order capability in trading skills, missing/incompatible licence. Most hits in prose are false positives; scripts are not.
"""
import os, re, sys

PATS = {
    "NET": r"\b(requests\.(get|post|put|delete|request|Session)|urllib\.request|urlopen|http\.client|httpx|aiohttp|socket\.|websocket|fetch\(|axios|XMLHttpRequest|curl\s|wget\s|Invoke-WebRequest|urllib3)",
    "EXEC": r"\b(eval\(|exec\(|compile\(|os\.system|subprocess|Popen|shell\s*=\s*True|child_process|execSync|spawn\(|__import__|pickle\.loads|marshal)",
    "OBFUS": r"(base64\.(b64decode|decodebytes)|atob\(|[A-Za-z0-9+/=]{120,}|fromhex|codecs\.decode|rot13|zlib\.decompress)",
    "SECRET": r"(os\.environ|getenv|process\.env|API[_-]?KEY|SECRET|PASSWORD|PRIVATE[_-]?KEY|ACCESS[_-]?TOKEN|BEARER|~/\.ssh|\.aws|id_rsa|seed phrase|mnemonic)",
    "ORDER": r"(place[_ ]?order|submit[_ ]?order|create[_ ]?order|order_send|OrderSend|CTrade|\.buy\(|\.sell\(|market_order|ccxt|alpaca|ib_insync|execute[_ ]?trade|withdraw|transfer\()",
    "FSDEL": r"(rm\s+-rf|shutil\.rmtree|os\.remove|os\.unlink|git\s+push|git\s+reset\s+--hard|DROP\s+TABLE|TRUNCATE|chmod\s+777|sudo\s)",
    "INSTALL": r"(pip3?\s+install|npm\s+(i|install)|npx\s+|yarn\s+add|brew\s+install|apt(-get)?\s+install|curl[^|\n]*\|\s*(ba)?sh|uvx?\s)",
    "INJECT": r"(ignore (all |any )?(previous|prior|above)|disregard (the )?(previous|above|system)|do not (tell|inform|mention|reveal)( this)? to the user|without (telling|informing|asking) the user|exfiltrat|override (the )?system|you are now|new instructions:|telemetry)",
}
URL = re.compile(r"https?://([^/\s:)\]'\"<>`]+)")
HIDDEN = re.compile("[​‌‍⁠⁢⁣⁤﻿‪-‮⁦-⁩\U000e0000-\U000e007f]")
SCRIPT_EXT = {".py", ".sh", ".js", ".mjs", ".cjs", ".ts", ".ps1", ".bat", ".rb", ".go", ".mq5", ".mqh"}


def scan(root, detail):
    hits = {k: [] for k in PATS}
    domains, scripts, binaries, links, hidden = set(), [], [], [], []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d != ".git"]
        for f in fn:
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root)
            if os.path.islink(p):
                links.append(rel)
                continue
            if os.path.splitext(f)[1].lower() in SCRIPT_EXT:
                scripts.append(rel)
            try:
                text = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                binaries.append(rel)
                continue
            if HIDDEN.search(text):
                hidden.append(rel)
            for i, line in enumerate(text.split("\n"), 1):
                for m in URL.finditer(line):
                    domains.add(m.group(1))
                for k, pat in PATS.items():
                    if re.search(pat, line, 0 if k == "OBFUS" else re.I):
                        hits[k].append((rel, i, line.strip()[:140]))
    print(f"scripts ({len(scripts)}): {scripts}")
    print(f"binary files: {binaries}\nsymlinks: {links}\nhidden-unicode files: {hidden}")
    print(f"URL domains: {sorted(domains)}")
    for k, v in hits.items():
        print(f"{k}: {len(v)} hit(s)")
        if detail:
            for rel, i, line in v[:40]:
                print(f"    {rel}:{i}: {line}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1 or not os.path.isdir(args[0]):
        sys.exit(__doc__)
    scan(args[0], "--detail" in sys.argv)
