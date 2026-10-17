# Prompt design and the cost of a correct answer

P1 provides a fixed 40-task HumanEval subset and a Windows restricted-subprocess
correctness runner. Read docs/SPEC.md and docs/SAFETY.md before using it.
The owner writes the research analysis. No inference or energy study has run yet.

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
Code extraction and prompt assembly are P2 work, not hidden heuristics in P1.
Notebook/interactive imports need `src` on the Python import path; pytest sets
that path via pyproject.toml. Windows sandbox controls are required; other OSes
fail closed instead of running code with weaker limits.

See docs/ENVIRONMENT.md for observed power settings, docs/REFERENCES.md for
licences, and docs/learning/P1.md for the walkthrough and assumptions.
