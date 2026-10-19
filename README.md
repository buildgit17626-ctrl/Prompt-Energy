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
