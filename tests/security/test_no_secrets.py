"""Repository-wide scan for material that must never be committed."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
SKIP_FILES = {".env"}  # local-only, gitignored

PATTERNS = {
    # 64 hex chars is the shape of a raw secp256k1 private key.
    "hex_private_key": re.compile(r"(?<![0-9a-fA-F])(?:0x)?[0-9a-fA-F]{64}(?![0-9a-fA-F])"),
    "pem_private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "assigned_secret": re.compile(
        r"(?i)(private_key|seed_phrase|mnemonic|secret_key)\s*[:=]\s*['\"]?[^\s'\"#]{8,}"),
}


def repo_files():
    for path in ROOT.rglob("*"):
        if (path.is_file() and not SKIP_DIRS.intersection(path.parts)
                and path.name not in SKIP_FILES):
            yield path


class NoSecretsTest(unittest.TestCase):
    def test_no_secret_material_in_repository(self):
        hits = []
        for path in repo_files():
            if path == Path(__file__).resolve():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for name, pattern in PATTERNS.items():
                if pattern.search(text):
                    hits.append(f"{path.relative_to(ROOT)}: {name}")
        self.assertEqual(hits, [])

    def test_env_file_is_gitignored(self):
        ignored = (ROOT / ".gitignore").read_text().splitlines()
        self.assertIn(".env", ignored)


if __name__ == "__main__":
    unittest.main()
