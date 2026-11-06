"""Regression tests for the production tools (run: python3 -m unittest discover -s andrew-builds/tools/tests)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import produce  # noqa: E402


class Captions(unittest.TestCase):
    def test_srt_time_carries_rounding_into_seconds(self):
        self.assertEqual(produce.srt_time(534.9996), "00:08:55,000")
        self.assertEqual(produce.srt_time(0), "00:00:00,000")
        self.assertEqual(produce.srt_time(3661.5), "01:01:01,500")
        self.assertEqual(produce.srt_time(59.9996), "00:01:00,000")

    def test_times_never_go_backwards(self):
        ts = [i / 1000 + 0.0004 for i in range(0, 200000, 7)]
        out = [produce.srt_time(t) for t in ts]
        self.assertEqual(out, sorted(out))

    def test_cards_never_exceed_line_limits(self):
        for text, mc in (("Not the polished launch. The Tuesday where you send a message and hear nothing.", 24),
                         ("If you're thinking about starting something, I want you to see that you can start with what you have.", 42)):
            for card in produce.chunk_words(text, mc, 2):
                for c in produce.fit_card(card, mc, 2):
                    lines = produce.wrap_card(c, mc, 2)
                    self.assertLessEqual(len(lines), 2)
                    self.assertTrue(all(len(l) <= mc for l in lines), lines)

    def test_placeholders_are_never_captioned(self):
        self.assertEqual(produce.clean_text("I did [FILL: a number] things."), "I did things.")

    def test_estimate_counts_placeholders_as_speech(self):
        a = produce.est_seconds("Hello there friend.", 2.5, 0.6, 10)
        b = produce.est_seconds("Hello there friend. [FILL: x]", 2.5, 0.6, 10)
        self.assertGreater(b, a + 3)


if __name__ == "__main__":
    unittest.main()
