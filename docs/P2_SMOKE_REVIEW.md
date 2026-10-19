# P2 smoke inspection before P3

Reviewed 2026-10-19. Scope: four failed rows and the first passing P4 and P2 rows
in the saved schedule (smoke-001 and smoke-009). No new generations were made.
All 35 smoke rows remain excluded from the research analysis.

## Extraction and prelude checks

Each inspected response contains one complete python fence defining the required
top-level function. The registered extractor selects that entire block, preserving
the function and the model's demonstration calls. It removes surrounding prose
but makes no code repairs. For HumanEval/1, /11 and /14 the trusted prelude
contains `from typing import List`; the model's block also imports it. Repeating
this import is harmless. HumanEval/13's prelude is whitespace.

The four failures are genuine assertion failures in the candidate algorithms,
not syntax, policy, extraction, prelude, timeout or infrastructure failures.
All six were replayed through the existing restricted subprocess both with the
registered added prelude and with the selected block alone; outcomes matched
the originals in both cases. No generated code ran in the parent process.

## Four concrete wrong answers

| Run | Task / arm | Verified example | Required output | Actual output |
| --- | --- | --- | --- | --- |
| smoke-015 | HumanEval/1, P4 | `separate_paren_groups('(())')` | `['(())']` | `['(()', ')']` |
| smoke-023 | HumanEval/14, P4 | `all_prefixes('')` | `[]` | `['']` |
| smoke-025 | HumanEval/11, P2 | `string_xor('0101', '0000')` | `'0101'` | `'101'` |
| smoke-026 | HumanEval/1, P2 | `separate_paren_groups('()()')` | `['()', '()']` | `['()()']` |

- smoke-015 appends and resets the group at **every closing parenthesis**, rather
  than waiting until nesting depth returns to zero. Nested groups are split.
- smoke-023 starts its loop at zero, so it adds the empty prefix. The supplied
  benchmark explicitly requires `[]` for an empty string.
- smoke-025 converts both inputs to integers and converts XOR back with `bin`.
  It does not restore the input width, so leading zeroes are lost.
- smoke-026 checks whether the stack is empty **before popping**. For balanced
  groups the reset branch is never reached, so separate groups are concatenated.

The actual outputs above were verified with separate trusted diagnostic checks
inside the same sandbox. Those diagnostics intentionally assert the observed
wrong output; their passing status confirms the diagnosis, not task correctness.
The original full benchmark replays still failed. Original results were not edited.

## Two passing verbose answers

- smoke-001, P4, HumanEval/11: XOR is performed character by character and joined
  back into a string. This preserves zeroes and input width. All benchmark checks
  pass, including the cases that fail in smoke-025.
- smoke-009, P2, HumanEval/13: the Euclidean algorithm repeatedly updates
  `(a, b)` to `(b, a % b)` until `b` is zero, then returns `a`. All supplied
  benchmark checks pass.

These comparisons validate the extraction path for the inspected rows; they do
not establish that verbose prompts are generally worse. No extraction change
is warranted by this review. Prompts, original source, tests and raw logs remain
unchanged. The viewer displays existing test results rather than implying a new
test has run whenever a result is viewed.

## Owner commands

```powershell
python -m experiments.show_run smoke-015
python -m experiments.show_run smoke-023
python -m experiments.show_run smoke-025
python -m experiments.show_run smoke-026
python -m experiments.show_run smoke-001
python -m experiments.show_run smoke-009
```

Use `.\.venv313\Scripts\python.exe` instead of `python` unless that environment
is activated. Each command prints prompts, response, extracted code, prelude,
combined source, saved result and benchmark checks. It makes no model calls,
executes no solution, and changes no data.

## Raw-log backup and audit artifacts

Copied the complete results/p2-smoke folder to:
`C:\Users\Dhruv Brahmbhatt\prompt-energy-backups\p2-smoke-2026-10-19`.
All eight files, including the inactive lock file, match by SHA-256. The backup
is outside the repo but on the same physical drive; it is not protection from
drive failure. No cloud upload of raw generations was performed.

Local receipt: results/P2-backup-receipt.json. Independent replay evidence:
results/P2-manual-review.json. Committed copies of these audit records are in
results/samples/. Full model responses remain in the original and backup folders.
Hash verification before/after the replay confirms original logs were unchanged.

## Loading overhead in this smoke (descriptive only)

The native load_duration values below are converted from nanoseconds to seconds.
Each row is the 1.5b model, five scored calls. Warm-ups/probes are excluded.
There are no scored 0.5b smoke rows, so no 0.5b prompt-group statistic is invented.
These figures describe loading overhead, not energy or a hypothesis test.

| Model | Prompt | Calls | Mean load seconds | Minimum | Maximum |
| --- | --- | --- | --- | --- | --- |
| 1.5b | P0 | 5 | 1.8445 | 1.6708 | 2.2338 |
| 1.5b | P1 | 5 | 1.7273 | 1.6709 | 1.9281 |
| 1.5b | P2 | 5 | 1.7844 | 1.6698 | 1.9492 |
| 1.5b | P3_1 | 5 | 1.7800 | 1.6468 | 2.2064 |
| 1.5b | P3_3 | 5 | 1.8522 | 1.6830 | 1.9808 |
| 1.5b | P4 | 5 | 1.7829 | 1.6735 | 1.9216 |
| 1.5b | P5 | 5 | 1.6754 | 1.6619 | 1.6870 |

Verification after adding the read-only viewer: **261 tests passed in 28.42
seconds**, Ruff check passed, and all 23 Python files passed formatting checks.
The six new tests cover read-only behavior, missing/duplicate IDs, missing test
results, malformed HTTP bodies, reconstruction warnings and CLI exit codes.
Local report: results/P2-review-tests.xml.

## Assumptions

- This inspection covers the six named rows, not a fresh evaluation of all 35.
- Diagnostic inputs clarify the bugs; they do not replace the benchmark checks.
- Future P3 post-load/phase windows are approximations from aggregate durations.
  The owner-approved tolerance max(0.1 seconds, 5% of API total duration) is now
  registered in SPEC; no P3 implementation or measurement occurred here.
