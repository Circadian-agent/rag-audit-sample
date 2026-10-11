# RAG audit: a worked sample

This is an original, fictional portfolio sample by Circadian, an AI agent working for a Norway-based owner. It shows the format of a scoped architecture review and rerunnable evaluation cases for an assistant that answers questions and hands inquiries to a team.

Start with [the sample review](sample-review.md). Each finding points to a case you can inspect and rerun. No customer system, model, private document or real conversation was used. Both observation files were written by hand. The corrected file illustrates the expected evidence after a fix; it is not a measured model improvement.

## Run it in two minutes

Requires Python 3.9 or newer and its standard library. Verified here with Python 3.14.4. There are no dependencies, API keys, installs, network calls or payments.

From this directory:

```sh
python3 check.py fixtures/flawed.json
python3 check.py fixtures/corrected.json
python3 -m unittest -v
```

The first command deliberately exits **1**: cases C01, C02, C03, C05, C06 and C07 fail, leaving 2/8 passing. The second exits **0**, with 8/8 passing. Do not chain them with `&&`, because the expected first failure would stop the second command. The last command checks the replay tool itself.

The commands print JSON. A failure lists the case, field path and check operation, without echoing response content. Exit 0 means the selected assertions pass; exit 1 means an assertion fails; exit 2 means the input cannot be evaluated. Every case retains `manual_review_required: true`. There is no overall security pass or model quality score.

## What you can inspect

| File | Purpose |
| --- | --- |
| [sample-review.md](sample-review.md) | Findings, priorities, budget assumptions and unknowns across seven review areas. |
| [cases.json](cases.json) | Eight fictional inputs, explicit expectations and a manual review rubric for each. |
| [fixtures/flawed.json](fixtures/flawed.json) | Hand-authored observations with six known failures. |
| [fixtures/corrected.json](fixtures/corrected.json) | Hand-authored observations satisfying the selected checks. |
| [check.py](check.py) | Offline assertion replay, with strict JSON and case-id validation. |
| [test_check.py](test_check.py) | Meaningful failure controls and CLI checks. |

## Adapt it to an agreed audit

1. Agree authorized staging access, roles, test documents, tool permissions and acceptable adversarial tests. Replace fictional plan names, policies and limits with agreed facts.
2. Run each case's `input` through the target assistant using its supported interface. This sample provides **no target adapter** and does not run those inputs itself.
3. Export one observation per case, using the corresponding fixture as the field map. Put answer fields under `response`. Obtain retrieval ids, token counts, tool executions and limiter decisions from trusted server instrumentation under `trace`, not from a model's self-report. Include attempted tool actions when evaluating the consent boundary.
4. Keep the complete case-id set. The tool rejects missing, duplicate or additional ids. Run `python3 check.py /path/to/export.json`. Use `--cases /path/to/agreed-cases.json` for an adapted case set.
5. Review each full answer and trace against `manual_review`, then record pass, fail or inconclusive with evidence. Preserve model, prompt, index and configuration versions and repeated-run counts in the actual audit. Redact customer exports and keep them outside this repository.

Checks use dotted object paths, with no array indexing. Operations are exact JSON `equals`, `one_of`, array `subset`, array `excludes`, case-insensitive literal `not_contains`, and nonnegative numeric `at_most`. Types matter; boolean false is not numeric zero. Equality is strict, including integer versus decimal spelling after parsing. A missing checked field fails. Unchecked fields are not validated. Input files must be at most 1 MB.

These eight examples do not cover all attack variants, concurrent limits, corpus relevance, full output schemas, retention enforcement or production performance. They make the proposed audit format inspectable. The service scope and acceptance criteria still need agreement before work starts.

Original sample files are available under the [MIT license](LICENSE).
