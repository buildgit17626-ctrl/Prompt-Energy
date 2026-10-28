# Report and code: Prompt design and the energy cost of correct code

A small exploratory experiment on prompt design, correctness, tokens, latency
and estimated CPU package energy on one consumer laptop. It compares seven
prompt arms using Qwen2.5-Coder 0.5B and 1.5B on 40 HumanEval tasks.

## Read the findings and inspect the evidence

- [Two-page summary](artifacts/reports/P4_two_page_summary.pdf)
- [Full report and comparison sheet](artifacts/reports/P4_baseline_brief.pdf)
- [All 840 request rows](artifacts/results/p4-full/full.csv)
- [Figures, tables and saved responses](artifacts/README.md)
- [Exact prompts](docs/PROMPTS.md), [setup](docs/analysis/P4_SETUP.md),
  [safety limits](docs/SAFETY.md), [sources and third-party licences](docs/REFERENCES.md)

Stage 1 (560 requests) supplies the main comparisons; stage 2 (280 requests)
supplies separate repeat diagnostics. They must not be pooled as 840 independent
task comparisons. All stage-1 energy estimates have baseline drift; 70 have
short measurement windows. Stage 2 has 99 missing energy estimates. CPU package
energy is an estimate, not whole-device electricity, battery use or carbon.
This is a student experiment report, not a claim of a general benchmark.

The public export retains failures and missing values. Local account paths are
redacted in metadata; exact saved HTTP response bodies are preserved. Original
local journals are unchanged. See the export provenance for both source and
public-file checksums. No model weights, environments or HWiNFO binary are shipped.
No new software licence is assigned to original project material by publication;
third-party material remains subject to its retained notices.

Offline analysis of the public main data (no Ollama or HWiNFO required):

```powershell
.\.venv313\Scripts\python.exe -m analysis.full_analysis --run artifacts/results/p4-full --output results/public-analysis
```

The following sections document the harness and historical execution workflow.
The full P4 run is complete; live commands below describe reproduction and must
use a new output folder, never overwrite the accepted evidence.

P1 provides a fixed 40-task HumanEval subset and a Windows restricted-subprocess
correctness runner. Read docs/SPEC.md and docs/SAFETY.md before using it.
P2 adds local Ollama inference, exact prompt assembly and auditable result logging.
The owner develops the research interpretation; AI assistance is disclosed in the report.

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

Pilot acceptance alone did not authorize the later full run. P4 subsequently
completed; see the public evidence above.

## Post-pilot diagnostic figure

Run `.\.venv313\Scripts\python.exe -m analysis.pilot_diagnostics` for the
owner-requested diagnostic gross/net energy scatterplots and repeat comparisons.
Read [the diagnostic note](docs/P3_DIAGNOSTICS.md). The future measurement policy
in config disables phase energy and CodeCarbon, with a primary-resolution
sensitivity analysis. This does not start or authorize P4.


## P4 overnight guide: historical run procedure

P3 is accepted. P4's registered schedule is 840 scored requests: 560 on all
40 tasks once, then 280 extra repeats on the seeded 10-task subset. The change
was made for timing feasibility, not outcome selection. Read
[the plan](docs/plans/P4.md) and [learning note](docs/learning/P4.md).

**Do not start a full run until the owner explicitly approves it.** No live P4
requests were made during implementation. The default command is safe/offline:

```powershell
.\.venv313\Scripts\python.exe -m experiments.run_p4 prepare
```

Before the approved overnight block:

1. Plug in the laptop and select Windows Best performance. Set sleep/hibernate
   on AC power to Never for the measurement period. Keep the lid open unless its
   closing action has also been set not to sleep. A screen turning off is fine;
   system sleep is not. Restore preferred settings after measurement.
2. Close unnecessary apps, games, downloads and other inference sessions. Leave
   Ollama and HWiNFO running. Do not update Ollama, model files or dependencies.
   Keep the laptop on a ventilated surface. Avoid interaction during baseline
   windows and scored requests.
3. In HWiNFO, set polling to 500 ms and direct disk CSV logging. Confirm CPU
   Package Power [W]. Start a new log or continue an append-only file; never
   overwrite a log used by an earlier block. Record its path/version.
4. Use the same registered HWiNFO version/dialect across blocks. The pilot used
   HWiNFO64 8.54-6090 and cp1252; pass the actual values. Run preflight:

```powershell
.\.venv313\Scripts\python.exe -m experiments.run_p4 preflight --hwinfo-log 'C:\path\sensors.csv' --encoding cp1252
```

5. Complete the separate registered calibration and freeze both grouping maps
   in P4_GROUPING before the main run. The runner rejects incomplete maps. Labels
   cannot be inferred from main-run outcomes or added to an existing manifest.
   See the calibration instructions below.
6. Only after approval, run **one block**:

```powershell
.\.venv313\Scripts\python.exe -u -m experiments.run_p4 run-block --owner-approved --output results/p4-full --hwinfo-log 'C:\path\sensors.csv' --hwinfo-version '8.54-6090' --encoding cp1252
```

The block discards saved warm-ups, unloads models and records a 60-second start
baseline. It stops launching after 3 hours, finishes the bounded active request,
unloads and measures a 60-second end baseline. Four hours is the safety ceiling;
OS suspension can defeat wall-clock guarantees and will be flagged. The final
block can be shorter. No next block starts automatically. Leave logging active
until the command exits and the end baseline has been saved.

Repeat the same command/folder for the next approved block. A new log path is
allowed if format/version are unchanged; earlier logs must remain accessible.
Resume skips saved outcomes, including failures, and recovers saved raw responses
without regeneration. An uncertain in-flight request stops for investigation.
Do not delete journals, regenerate a timed-out answer or edit a failed row.
Ctrl+C attempts safe cleanup/end baseline; killing the process or shutting down
may leave a missing-end flag. Never rerun blindly after an API timeout: first
ensure Ollama is no longer processing that request.

Net energy uses each block's starting baseline. Drift above max(1 W, 10% of start)
is flagged and retained; missing end baselines are explicit. Report gross and
net. No phase-energy estimates or CodeCarbon tracking occur in P4. Every response
and failure is retained. Back up each closed block, including sensor mirrors,
and verify OneDrive sync or an independent-device copy before relying on it.

Derived reporting and analysis (no inference):

```powershell
.\.venv313\Scripts\python.exe -m experiments.run_p4 report --output results/p4-full
.\.venv313\Scripts\python.exe -m analysis.full_analysis --run results/p4-full --output results/p4-analysis
```

full.csv joins immutable answers/measurements/block events. Analysis emits both
all-row and primary-low-resolution-excluded summaries; unavailable energy is
never zero. It includes per-arm bootstrap intervals, gross/net cost per correct
answer, input/output-token OLS and residuals, Pareto plots, and stage-2 noise.
Grouping files are emitted only for frozen labels; P0 is excluded from them.
Scaffolds include tool/mode and limitations. The owner writes interpretation.
Partial batches are provisional, and stage-2 repeats do not overweight stage 1.


### Before the first full block: separate calibration

The owner registered 40 requests: 1.5b/P0 once on all tasks, without energy.
The reference-length grouping is already fixed (median 6 lines, 21 short/19 long).
The main runner refuses execution until both complete grouping maps are frozen.
Calibration completed on 2026-10-21: 26 solved and 14 failed; both maps are
frozen in config with provenance. For historical reproduction, use source commit
cc12c44 and a separate output directory; do not regenerate accepted observations.
Plug in and select Best performance before any authorized run. Preparation is offline:

```powershell
.\.venv313\Scripts\python.exe -m experiments.calibrate prepare
```

When ready for the separately approved calibration:

```powershell
.\.venv313\Scripts\python.exe -u -m experiments.run_p4 calibrate --owner-approved
.\.venv313\Scripts\python.exe -m experiments.calibrate labels
```

Review the complete exported labels, freeze them and their source checksums in
P4_GROUPING, and commit before the main run. Do not use pilot/main outcomes or
rerun failed answers. Because freezing config changes the registration fingerprint,
any later calibration resume needs its original committed source. The read-only
labels command remains available for auditing complete original evidence.
A separate calibration is not proof of statistical independence; use the labels
solved/failed, and report actual group sizes as descriptive, noisy groups.

Before any new approved main run, confirm with the owner that HWiNFO logging has begun
and obtain the new CSV path. Calibration does not require that log.

## Completed P4: additional comparison review

The saved full run has 840 scored requests (560 stage 1, 280 stage 2).
Regenerate the owner-requested supplementary views without model calls:

```powershell
.\.venv313\Scripts\python.exe -m analysis.comparisons
```

This requires the existing local results/p4-full, results/p4-analysis and
results/p4-presentation evidence folders. Results are git-ignored and must be
restored from a verified backup on a fresh checkout. Eight new PNG/SVG figures,
summary CSVs, provenance and index.html are written to results/p4-comparisons.
Existing broad figures are reused under its existing/ folder. Open index.html
for the gallery. No scored data is changed; source and summary consistency are
checked. The original PDF remains unchanged.

Read [full setup](docs/analysis/P4_SETUP.md) and
[expectations versus evidence](docs/analysis/P4_EXPECTATIONS_OBSERVATIONS.md).
The latter includes candidate metric leaders, corrections, sensitivity caveats,
and a future roadmap. Conclusions remain owner-review drafts until approved.
These descriptive views do not change preregistered H1-H5 or start P5.
The current public report incorporates the owner's subsequent wording and review
changes; older review documents preserve the history of proposed interpretations.
