# Prompt design and the cost of a correct answer

P1 provides a fixed 40-task HumanEval subset and a Windows restricted-subprocess
correctness runner. Read docs/SPEC.md and docs/SAFETY.md before using it.
P2 adds local Ollama inference, exact prompt assembly and auditable result logging.
The owner writes the research analysis. No energy measurement or full study has run.

## Setup (PowerShell, Windows, Python 3.13 64-bit)

```powershell
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv313\Scripts\python.exe -m pytest
.\.venv313\Scripts\python.exe -m ruff check .
```

The active study environment is `.venv313` using installed Python 3.13.7 (64-bit).
The old `.venv` still contains Python 3.11; it is retained for rollback and is not
the study environment. Interpreter/environment directories are intentionally ignored.
The small licensed benchmark archive is committed, so tests require no network
after environment setup. requirements.txt contains direct version pins;
requirements-lock.txt also pins transitive dependencies of the validated environment.

The tests run all 40 unchanged reference solutions and 40 deliberately incorrect
implementations; they also exercise timeout, memory limits and policy failures.
For a focused acceptance check: `python -m pytest tests/test_sandbox.py -k reference`.
Use the `.venv313\Scripts\python.exe` path if the environment is not activated.

Configuration lives in experiments/config.py; task loading and execution live
in src/prompt_energy/. The runner accepts a complete Python function module.
P2 uses the fixed extraction and prompt-assembly rules in docs/PROMPTS.md.
Notebook/interactive imports need `src` on the Python import path; pytest sets
that path via pyproject.toml. Windows sandbox controls are required; other OSes
fail closed instead of running code with weaker limits.

See docs/ENVIRONMENT.md for observed power settings, docs/REFERENCES.md for
licences, and docs/learning/P1.md for the walkthrough and assumptions.

## See the restrictions in action

From the repository root:

```powershell
.\.venv313\Scripts\python.exe -m experiments.sandbox_demo
```

With `.venv313` activated, use `python -m experiments.sandbox_demo`.
Expected outcomes: correct -> passed; wrong -> failed; import os -> rejected;
infinite loop -> timeout; memory hog -> memory_limit. The command exits nonzero
if any outcome differs. It uses the same five-second/256-MiB limits as the tests,
executes only authored snippets in workers, and writes no model outputs.

## P2 smoke and resume (no energy measurement)

Start the installed Ollama application/service. Both registered tags must already
be installed: `qwen2.5-coder:0.5b` and `qwen2.5-coder:1.5b`. Review the exact
prompts in docs/PROMPTS.md; docs/PROMPT_EXAMPLES.md contains copyable examples.
From the repository root, with AC power and Best performance selected:

```powershell
.\.venv313\Scripts\python.exe -m experiments.run_p2 --output results/p2-smoke
```

This performs two identical P0 requests per model, records the cache decision,
and runs 35 scored requests: five tasks, seven arms, the 1.5b model, one repeat.
Warm-ups and probes are saved but excluded from scored rows. The command never
starts HWiNFO or CodeCarbon and has no full-study option. All model-generated
code is checked only through the existing Windows subprocess restrictions.

Repeat the **same command and output path** to resume. Completed failures are
also skipped. A saved response is reused if its correctness result was not yet
written. A completed batch makes no API calls on resume. Do not change config,
runtime, models or harness source within a batch. A different output path starts
a new batch and therefore new calls; do not use that to replace unwanted results.

Inspect `results/p2-smoke/results.csv` for the SPEC rows and
`cache_policy.json` for observed determinism/cache signals. Each CSV row links
to a request ID in `raw.jsonl`. The exact HTTP body is base64-encoded to retain
even malformed responses losslessly; decode it with Python's `base64.b64decode`
and parse valid JSON with `json.loads`. This is data decoding, never code execution.
`results.jsonl` includes detailed failure reasons and sandbox outcomes. The
manifest records model digests/templates, runtime and source hashes; session
records preserve the actual host/power observations. All these files are local
and git-ignored. Back them up unchanged before any later study run.

If the runner reports an uncertain in-flight request or damaged journal, preserve
the directory and investigate. It intentionally does not regenerate or edit raw
data. A network timeout logs a failed row and stops because the server might
still be working. Read docs/learning/P2.md for the walkthrough and evidence.

## Inspect a saved answer (no generation or execution)

```powershell
.\.venv313\Scripts\python.exe -m experiments.show_run smoke-026
```

With the study environment activated, use `python -m experiments.show_run smoke-026`.
The viewer prints the saved system/user prompts, raw response text, extracted
code, prelude, combined source, saved test result and benchmark checks. It does
not rerun code or modify files. Use `--output <batch-folder>` for another folder.
It warns if current extraction/task/config files differ from the saved hashes.
Read docs/P2_SMOKE_REVIEW.md for the four failure explanations and two passing
verbose examples. Smoke rows are excluded from research analysis.


## P3: pilot completed; commands for reproduction

The owner-approved 320-request pilot completed on 2026-10-20. See
[the pilot audit](docs/P3_PILOT_REVIEW.md). Read
[the P3 plan](docs/plans/P3.md), [registered protocol](docs/SPEC.md) and
[learning note](docs/learning/P3.md) first.

Safe offline preparation (no model or tracker calls):

```powershell
.\.venv313\Scripts\python.exe -m experiments.run_p3 prepare
.\.venv313\Scripts\python.exe -m experiments.show_run smoke-026
```

Start HWiNFO sensor CSV logging at **500 ms**. While plugged in with Best
performance, run this read-only preflight, replacing the example path:

```powershell
.\.venv313\Scripts\python.exe -m experiments.run_p3 preflight --hwinfo-log 'C:\path\sensors.csv'
```

Defaults: UTF-8 with optional BOM, comma delimiter, decimal dot, Date format
`%d.%m.%Y`, Time `%H:%M:%S.%f`, UTC+05:30, exact column `CPU Package Power [W]`.
Use `--help` to specify actual encoding, delimiter, decimal, date/time format,
timezone or header. Duplicate sensor headers require `--power-index` (zero-based
CSV column). These settings are recorded; the parser never guesses dates.
Retain the original CSV and record the installed HWiNFO version.

**Only after owner approval**, the live command is:

```powershell
.\.venv313\Scripts\python.exe -m experiments.run_p3 pilot --owner-approved --hwinfo-log 'C:\path\sensors.csv' --hwinfo-version 'ACTUAL_VERSION'
```

Use the same output folder, version and format options to resume. Every new
session with pending requests obtains a new baseline. An uncertain in-flight
request stops for investigation instead of automatic regeneration. Keep raw
logs and sensor files; back them up after the approved pilot.

The offline report can be rebuilt with:

```powershell
.\.venv313\Scripts\python.exe -m experiments.run_p3 report --output results/p3-pilot
```

It writes derived energy.csv and energy-summary.json with load summaries, repeat
spread, flags and a qualified runtime proxy. Smoke data is rejected. Pilot data
is labelled excluded from main analysis. Primary HWiNFO energy is estimated
post-load CPU package energy; CodeCarbon is a separate whole-request estimate.


The accepted pilot output folder is `results/p3-pilot-2026-10-20` (git-ignored).
Its recorded parser option is `--encoding cp1252`, and HWiNFO version is
`8.54-6090`. Report-only access requires no model requests:

```powershell
.\.venv313\Scripts\python.exe -m experiments.run_p3 report --output results/p3-pilot-2026-10-20
```

No full run (P4) has been started or authorized by completing this pilot.
