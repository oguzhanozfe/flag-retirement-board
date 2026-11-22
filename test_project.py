import unittest
from project import analyze


def run(levels, traffic=100, errors=0):
    history = [{"date": f"2026-01-{i:02d}", "rollout_pct": r, "evaluations": traffic,
                "errors": errors} for i, r in enumerate(levels, 1) if r is not None]
    return analyze({"as_of": "2026-01-03", "window_days": 3, "flags": {"flag": history}})


class FlagTests(unittest.TestCase):
    def test_both_terminal_states(self):
        for n, state in [(100, "enabled"), (0, "disabled")]:
            self.assertEqual(run([n] * 3)["rows"][0]["Decision"], f"Review {state} branch")

    def test_partial_and_missing_days(self):
        self.assertIn("partial", run([25, 100, 100])["rows"][0]["Decision"])
        self.assertIn("missing", run([100, None, 100])["rows"][0]["Decision"])

    def test_each_day_needs_traffic_and_zero_errors(self):
        self.assertIn("traffic", run([0] * 3, traffic=24)["rows"][0]["Decision"])
        self.assertIn("errors", run([100] * 3, errors=1)["rows"][0]["Decision"])

    def test_rejects_malformed_evidence(self):
        for levels in ([101] * 3, [True] * 3, [100] * 4):
            with self.subTest(levels=levels), self.assertRaises(ValueError):
                run(levels)
