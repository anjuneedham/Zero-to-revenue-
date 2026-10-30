#!/usr/bin/env python3
"""Vendor ONE skill from a local git clone into .claude/skills/ and record it in the manifest.

Stdlib only. Never touches the network: you clone the upstream repo yourself (so you can pin and inspect it),
run scripts/skills/vet_skill.py on the folder, then run this.

    git clone --depth 1 https://github.com/OWNER/REPO /tmp/REPO
    python3 scripts/skills/vet_skill.py /tmp/REPO/path/to/skill
    python3 scripts/skills/install_skill.py --clone /tmp/REPO --owner-repo OWNER/REPO \
        --path path/to/skill --category saas
    python3 scripts/skills/build_docs.py && python3 scripts/skills/verify_skills.py
"""
import argparse, datetime, json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".claude" / "skills"
MANIFEST = ROOT / "docs" / "skills-manifest.json"
IGNORE = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".DS_Store", "node_modules")
LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING")


def frontmatter_name(skill_md: Path) -> str:
    m = re.match(r"^---\s*\n(.*?)\n---", skill_md.read_text(encoding="utf-8"), re.S)
    n = re.search(r"^name:\s*(.+)$", m.group(1) if m else "", re.M)
    if not n:
        sys.exit(f"{skill_md}: no frontmatter name")
    return n.group(1).strip().strip("\"'")


def find_license(*dirs: Path):
    for d in dirs:
        for name in LICENSE_NAMES:
            p = d / name
            if p.is_file():
                return p
        for p in sorted(d.glob("[Ll][Ii][Cc]*")):
            if p.is_file():
                return p
    return None


def spdx(text: str) -> str:
    if "Apache License" in text and "Version 2.0" in text:
        return "Apache-2.0"
    if re.search(r"\bMIT License\b|Permission is hereby granted, free of charge", text):
        return "MIT"
    if "BSD" in text[:400]:
        return "BSD"
    if "Creative Commons" in text[:600] and "Attribution" in text[:900]:
        return "CC-BY"
    return "UNKNOWN"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clone", required=True, help="local git clone of the upstream repo")
    ap.add_argument("--owner-repo", required=True, help="e.g. coreyhaines31/marketingskills")
    ap.add_argument("--path", required=True, help="skill folder relative to the clone root")
    ap.add_argument("--category", required=True, choices=["saas", "eng", "fashion", "trading", "invest", "sales", "docs"])
    ap.add_argument("--notes", default="")
    a = ap.parse_args()

    clone = Path(a.clone).resolve()
    src = clone / a.path
    if not (src / "SKILL.md").is_file():
        sys.exit(f"{src}/SKILL.md not found")
    name = frontmatter_name(src / "SKILL.md")
    commit = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()

    lic = find_license(src, clone)  # skill-level licence wins over the repo's
    if lic is None:
        sys.exit("No LICENSE found in skill or repo root: REJECT (unlicensed).")
    lic_id = spdx(lic.read_text(encoding="utf-8", errors="replace"))
    if lic_id == "UNKNOWN":
        sys.exit(f"{lic}: not recognisably MIT/Apache/BSD/CC-BY: REJECT or review manually.")

    dest = SKILLS / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=IGNORE)
    if find_license(dest) is None:  # keep licence next to the skill, as required
        shutil.copyfile(lic, dest / "LICENSE")
        lic_file = "LICENSE (copied from repo root)"
    else:
        lic_file = find_license(dest).name

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    manifest = [e for e in manifest if e["name"] != name]
    manifest.append({
        "name": name, "category": a.category, "repo": a.owner_repo, "path": a.path, "commit": commit,
        "license": lic_id, "license_file": lic_file,
        "source_url": f"https://github.com/{a.owner_repo}/tree/{commit}/{a.path}",
        "installed": datetime.date.today().isoformat(), "notes": a.notes,
    })
    manifest.sort(key=lambda e: (e["category"], e["name"]))
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"installed {name} [{lic_id}] @ {commit[:9]}")


if __name__ == "__main__":
    main()
