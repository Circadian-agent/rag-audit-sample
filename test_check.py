import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import check

HERE = Path(__file__).parent


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.cases = check.load(HERE / "cases.json")
        self.good = check.load(HERE / "fixtures/corrected.json")

    def test_known_flaws_have_specific_evidence(self):
        result = check.evaluate(self.cases, check.load(HERE / "fixtures/flawed.json"))
        self.assertEqual([r["id"] for r in result["results"] if not r["assertions_passed"]],
                         ["C01", "C02", "C03", "C05", "C06", "C07"])
        boundary = result["results"][1]
        self.assertEqual(boundary["failed"], [{"path": "trace.retrieved_ids", "op": "subset"}])

    def test_corrected_fixture_retains_manual_review(self):
        result = check.evaluate(self.cases, self.good)
        self.assertEqual((result["passed"], result["cases"]), (8, 8))
        self.assertTrue(all(r["manual_review_required"] for r in result["results"]))
        self.assertFalse(result["security_certification"])
        self.assertEqual(result["model_calls"], 0)

    def test_missing_observation_is_input_error(self):
        with self.assertRaises(ValueError):
            check.evaluate(self.cases, self.good[:-1])

    def test_duplicate_and_extra_observations_are_input_errors(self):
        for extra in (self.good[0], dict(self.good[0], id="unknown")):
            with self.subTest(extra=extra["id"]), self.assertRaises(ValueError):
                check.evaluate(self.cases, self.good + [extra])

    def test_missing_checked_field_fails(self):
        del self.good[1]["trace"]["retrieved_ids"]
        self.assertFalse(check.evaluate(self.cases, self.good)["results"][1]["assertions_passed"])

    def test_wrong_types_and_negative_counts_fail(self):
        for value in (False, "0", -1, float("inf")):
            with self.subTest(value=value):
                self.good[0]["trace"]["context_tokens"] = value
                self.assertFalse(check.evaluate(self.cases, self.good)["results"][0]["assertions_passed"])
        self.good[6]["trace"]["provider_calls"] = False
        self.assertFalse(check.evaluate(self.cases, self.good)["results"][6]["assertions_passed"])

    def test_invalid_case_definitions_are_errors(self):
        for mutation in ({"op": "execute"}, {"path": ""}, {"op": "subset", "expected": "oops"},
                         {"op": "at_most", "expected": True}, {"unexpected": "field"}):
            cases = copy.deepcopy(self.cases)
            cases[0]["checks"][0].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                check.evaluate(cases, self.good)
        for cases in ([], self.cases + [self.cases[0]]):
            with self.assertRaises(ValueError):
                check.evaluate(cases, self.good)

    def test_failure_report_does_not_echo_sensitive_values(self):
        self.good[4]["response"]["answer"] = "CANARY-EXFIL-907 PRIVATE-SENTINEL"
        result = json.dumps(check.evaluate(self.cases, self.good))
        self.assertNotIn("PRIVATE-SENTINEL", result)
        self.assertNotIn("CANARY-EXFIL-907", result)
        self.assertIn("response.answer", result)

    def test_strict_json_loader(self):
        for raw in (b'{"id":1,"id":2}', b'[NaN]', b'[Infinity]', b'[1e999]', b'\xff', b' ' * 1_000_001):
            with tempfile.TemporaryDirectory() as tmp:
                file = Path(tmp) / "invalid.json"
                file.write_bytes(raw)
                with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                    check.load(file)

    def test_cli_exit_codes_work_from_another_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, code in (("corrected.json", 0), ("flawed.json", 1), ("absent.json", 2)):
                result = subprocess.run([sys.executable, str(HERE / "check.py"),
                                         str(HERE / "fixtures" / name)], cwd=tmp,
                                        text=True, capture_output=True, check=False)
                with self.subTest(name=name):
                    self.assertEqual(result.returncode, code, result.stderr)
                    self.assertIsInstance(json.loads(result.stdout), dict)
                    self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
