"""Outcome classes of examples/workflow_common.classify (no Engine run needed)."""

import unittest

from examples import workflow_common as wc


def row(target_id, status, value=1.0):
    return {"id": target_id, "status": status, "value": value}


class ClassifyTests(unittest.TestCase):
    def test_precedence(self):
        self.assertEqual(wc.classify(None, [], []), "ERROR")
        self.assertEqual(wc.classify("FAIL", ["MODEL_WAVELENGTH_OUTSIDE_BAND"], [row("a", "FAIL")]), "OUT_OF_MODEL")
        self.assertEqual(wc.classify("PASS", ["MODEL_WAVELENGTH_OUTSIDE_BAND"], [row("a", "PASS")]), "OUT_OF_MODEL")
        self.assertEqual(wc.classify("FAIL", [], [row("a", "PASS"), row("b", "UNKNOWN", None)]), "UNKNOWN")
        self.assertEqual(wc.classify("FAIL", [], [row("a", "PASS"), row("b", "FAIL")]), "FAIL")
        self.assertEqual(wc.classify("WARNING", [], [row("a", "WARNING")]), "PASS")

    def test_selection_decides(self):
        rows = [row("a", "PASS"), row("b", "FAIL")]
        self.assertEqual(wc.classify("FAIL", [], rows, selected=["a"]), "PASS")
        self.assertEqual(wc.classify("FAIL", [], rows, selected=["c"]), "UNKNOWN")

    def test_nothing_evaluated_is_never_pass(self):
        for status in ("PASS", "WARNING", "NOT_APPLICABLE", "FAIL", "UNKNOWN"):
            self.assertEqual(wc.classify(status, [], []), "UNKNOWN", status)
        self.assertEqual(wc.classify("PASS", [], [row("a", "PASS")], selected=[]), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
