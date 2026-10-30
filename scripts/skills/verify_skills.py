#!/usr/bin/env python3
"""Verify the built-in skills library. Exit code 1 on any failure.

Checks (per the Agent Skills spec, agentskills.io/specification): 70 vendored + 6 custom skill folders; each SKILL.md has valid frontmatter with name + description;
name == folder name; no duplicate names; vendored skills have a LICENSE and a manifest entry with a pinned commit;
no symlinks; no unexpected binaries; and reports total size.

    python3 scripts/skills/verify_skills.py
"""
import json, os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".claude" / "skills"
MANIFEST = ROOT / "docs" / "skills-manifest.json"
EXPECT_VENDORED, EXPECT_CUSTOM = 70, 6
CUSTOM = {"agriloop-growth", "buildflow-growth", "fashion-launch", "trading-lab", "investing-plan", "hormozi-lens"}
BIN_OK = {".png", ".htm"}  # openai/pdf icon; mt5 test fixture (html)

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def main():
    manifest = {e["name"]: e for e in json.loads(MANIFEST.read_text())} if MANIFEST.exists() else {}
    if not manifest:
        err(f"missing or empty {MANIFEST.relative_to(ROOT)}")
    folders = sorted(p for p in SKILLS.iterdir() if p.is_dir()) if SKILLS.exists() else []
    seen, total_bytes, nfiles = {}, 0, 0

    for d in folders:
        md = d / "SKILL.md"
        if not md.is_file():
            err(f"{d.name}: no SKILL.md")
            continue
        fm, e = frontmatter.read(md)
        if e:
            err(f"{d.name}: {e}")
            continue
        name, desc = fm.get("name"), fm.get("description")
        if not isinstance(name, str) or not name.strip():
            err(f"{d.name}: frontmatter 'name' missing")
        elif name != d.name:
            err(f"{d.name}: name '{name}' != folder name")
        elif not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
            err(f"{d.name}: name violates Agent Skills spec (a-z0-9 and single hyphens, max 64)")
        if not isinstance(desc, str) or not desc.strip():
            err(f"{d.name}: frontmatter 'description' missing")
        elif len(desc) > 1024:
            err(f"{d.name}: description is {len(desc)} chars (>1024)")
        if isinstance(name, str):
            if name in seen:
                err(f"duplicate skill name: {name}")
            seen[name] = d
        for dp, dn, fn in os.walk(d):
            for f in fn:
                p = Path(dp) / f
                if p.is_symlink():
                    err(f"{p.relative_to(ROOT)}: symlink not allowed")
                    continue
                nfiles += 1
                total_bytes += p.stat().st_size
                if p.suffix.lower() in {".exe", ".dll", ".so", ".dylib", ".bin", ".jar", ".class", ".pyc", ".whl", ".zip", ".tar", ".gz"}:
                    err(f"{p.relative_to(ROOT)}: unexpected binary/archive")

    vendored = [n for n in seen if n not in CUSTOM]
    custom = [n for n in seen if n in CUSTOM]
    if len(vendored) != EXPECT_VENDORED:
        err(f"expected {EXPECT_VENDORED} vendored skills, found {len(vendored)}")
    if len(custom) != EXPECT_CUSTOM or set(custom) != CUSTOM:
        err(f"expected custom skills {sorted(CUSTOM)}, found {sorted(custom)}")

    for n in vendored:
        d = seen[n]
        if not any(f.name.lower().startswith("licen") for f in d.iterdir() if f.is_file()):
            err(f"{n}: no LICENSE file in skill folder")
        m = manifest.get(n)
        if not m:
            err(f"{n}: not in manifest")
        elif len(m.get("commit", "")) != 40 or m.get("license") not in ("MIT", "Apache-2.0", "BSD", "CC-BY"):
            err(f"{n}: manifest commit/license invalid ({m.get('commit')}, {m.get('license')})")
    for n in manifest:
        if n not in seen:
            err(f"manifest lists '{n}' but folder is missing")

    print(f"vendored skills : {len(vendored)} (expected {EXPECT_VENDORED})")
    print(f"custom skills   : {len(custom)} (expected {EXPECT_CUSTOM})")
    print(f"total folders   : {len(seen)}   files: {nfiles}")
    print(f"total size      : {total_bytes/1024/1024:.2f} MiB ({total_bytes:,} bytes)")
    print(f"duplicate names : {'none' if not any('duplicate' in x for x in errors) else 'FOUND'}")
    if errors:
        print(f"\nFAILED ({len(errors)}):")
        for x in errors:
            print("  -", x)
        sys.exit(1)
    print("\nOK: all checks passed")


if __name__ == "__main__":
    main()
