"""Tiny .env reader for the local app. Never overrides variables already set, never logs values."""

from pathlib import Path


def parse(text: str) -> dict:
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip().removeprefix("export ").strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if key.replace("_", "").isalnum() and key:
            out[key] = value
    return out


def load(path, environ) -> list[str]:
    """Load KEY=VALUE pairs into `environ` without overriding. Returns the names that were set."""
    p = Path(path)
    if not p.is_file():
        return []
    set_names = []
    for k, v in parse(p.read_text(encoding="utf-8")).items():
        if v and k not in environ:
            environ[k] = v
            set_names.append(k)
    return set_names
