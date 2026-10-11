#!/usr/bin/env python3
"""Replay explicit assertions against exported traces. No model or network calls."""
import argparse
import json
import math
from pathlib import Path
import sys

OPS = {"equals", "one_of", "subset", "excludes", "not_contains", "at_most"}
MISSING = object()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def load(path):
    with Path(path).open("rb") as source:
        raw = source.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError("input exceeds 1 MB")
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite JSON number")
        return number
    return json.loads(raw, object_pairs_hook=unique_object, parse_float=finite_float,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON number")))


def index_rows(rows, label):
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{label} must be a nonempty array")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
            raise ValueError(f"{label} row needs a nonempty string id")
        if row["id"] in result:
            raise ValueError(f"duplicate {label} id")
        result[row["id"]] = row
    return result


def validate_cases(cases):
    indexed = index_rows(cases, "cases")
    for case in indexed.values():
        if not isinstance(case.get("checks"), list) or not case["checks"]:
            raise ValueError("case needs checks")
        for check in case["checks"]:
            if not isinstance(check, dict) or set(check) != {"path", "op", "expected"}:
                raise ValueError("check needs exactly path, op, expected")
            path, op, expected = check["path"], check["op"], check["expected"]
            if not isinstance(path, str) or not path or any(not p for p in path.split(".")):
                raise ValueError("invalid check path")
            if not isinstance(op, str) or op not in OPS:
                raise ValueError("unknown check operation")
            if op in {"one_of", "subset", "excludes"} and not isinstance(expected, list):
                raise ValueError("list operation requires an expected array")
            if op == "not_contains" and (not isinstance(expected, str) or not expected):
                raise ValueError("not_contains requires a nonempty string")
            if op == "at_most" and (type(expected) not in (int, float) or not math.isfinite(expected)):
                raise ValueError("at_most requires a finite number")
    return indexed


def equal(a, b):
    # JSON booleans must not compare equal to numeric 0 or 1.
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def matches(actual, op, expected):
    if actual is MISSING:
        return False
    if op == "equals":
        return equal(actual, expected)
    if op == "one_of":
        return any(equal(actual, value) for value in expected)
    if op == "subset":
        return isinstance(actual, list) and all(any(equal(a, e) for e in expected) for a in actual)
    if op == "excludes":
        return isinstance(actual, list) and not any(equal(a, e) for a in actual for e in expected)
    if op == "not_contains":
        return isinstance(actual, str) and expected.casefold() not in actual.casefold()
    if op == "at_most":
        return type(actual) in (int, float) and math.isfinite(actual) and 0 <= actual <= expected
    raise ValueError("unknown check operation")


def evaluate(cases, observations):
    cases = validate_cases(cases)
    observations = index_rows(observations, "observations")
    if set(cases) != set(observations):
        raise ValueError("observation ids must match every case exactly")
    results = []
    for case_id, case in cases.items():
        failed = []
        for check in case["checks"]:
            actual = observations[case_id]
            for part in check["path"].split("."):
                actual = actual.get(part, MISSING) if isinstance(actual, dict) else MISSING
            if not matches(actual, check["op"], check["expected"]):
                # Do not echo response text, retrieved content or private values.
                failed.append({"path": check["path"], "op": check["op"]})
        results.append({"id": case_id, "assertions_passed": not failed, "failed": failed,
                        "manual_review_required": True})
    return {"mode": "exported-trace-replay", "model_calls": 0,
            "cases": len(results), "passed": sum(r["assertions_passed"] for r in results),
            "results": results, "security_certification": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", help="JSON array of exported observations")
    parser.add_argument("--cases", default=str(Path(__file__).with_name("cases.json")))
    args = parser.parse_args()
    try:
        result = evaluate(load(args.cases), load(args.observations))
    except (OSError, ValueError, TypeError, RecursionError):
        print(json.dumps({"error": "Invalid or unreadable input; check JSON, unique ids and case schema."}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] == result["cases"] else 1


if __name__ == "__main__":
    sys.exit(main())
