import os
import tempfile
import unittest

from core import envfile


class EnvFileTest(unittest.TestCase):
    def test_parse(self):
        got = envfile.parse('# c\nA=1\nexport B="two words"\nC=\'x\'\nD=val # note\nbad line\n=nokey\nE=a=b\n')
        self.assertEqual(got, {"A": "1", "B": "two words", "C": "x", "D": "val", "E": "a=b"})

    def test_load_never_overrides_and_skips_empty_values(self):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write("KEEP=new\nFRESH=yes\nEMPTY=\n")
        env = {"KEEP": "old"}
        try:
            self.assertEqual(envfile.load(f.name, env), ["FRESH"])
        finally:
            os.unlink(f.name)
        self.assertEqual(env, {"KEEP": "old", "FRESH": "yes"})
        self.assertEqual(envfile.load("/nonexistent/.env", {}), [])


if __name__ == "__main__":
    unittest.main()
