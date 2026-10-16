# AGENTS.md: Working agreement

## Project
A small, reproducible research study on the accuracy-versus-energy trade-off of classical and small neural models on tabular classification datasets. Read `docs/SPEC.md` before any work. It is the source of truth: if code and spec diverge, update the spec in the same change.

The owner is a student learning research. He will write the analysis and the report himself. Your job is to build a clean, trustworthy experiment harness and explain it.

## Stack (fixed)
- Python 3.11, a virtual environment, `requirements.txt` with pinned versions.
- `numpy`, `pandas`, `scikit-learn`, `openml`, `codecarbon`, `matplotlib`, `scipy`. Optional: `lightgbm` (ask first).
- Layout: `src/` (library code), `experiments/` (runnable scripts and configs), `results/` (raw CSV output, git-ignored except small samples), `analysis/` (scripts the owner edits), `docs/`, `tests/`.
- Windows-friendly: no Linux-only tools; use `pathlib`.

## How to work
1. One milestone at a time (`docs/SPEC.md`, section "Milestones"). Do not start the next unasked.
2. Before coding, write `docs/plans/<milestone>.md`: files to add, design, risks, open questions. If a question is about research design (not code), stop and ask.
3. Small commits with clear messages. Tests for data loading, metrics, the result schema, and any statistics helper.
4. A milestone is done only when its acceptance criteria pass and `pytest` and `ruff` (or the chosen linter) are clean.
5. After each milestone write `docs/learning/<milestone>.md`: plain-English explanation of what was built, how data flows, key files, and 5 questions the owner should be able to answer.
6. List every assumption at the end of each milestone.

## Research integrity rules (non-negotiable)
- Never fabricate, smooth or hand-edit results. Raw outputs are written by code and never modified.
- Fix and log every random seed. Record library versions, CPU model, OS, power mode and date in each results file.
- Log failed runs. Do not silently drop a model, dataset or fold. If something fails, write the reason in the results table.
- All tuning uses training data only. The test fold is never used to choose hyperparameters.
- Use the same tuning budget (number of configurations and inner folds) for every model and dataset.
- Energy numbers are estimates. Name the tool and measurement mode in every plot and table. Do not present them as lab measurements.
- Cite datasets and libraries in `docs/REFERENCES.md`. Check dataset licences before use.
- Write comments and docs that explain why, not only what.

## Code style
- Type hints on public functions, short modules, one responsibility each.
- Config-driven: datasets, models, budgets and seeds live in YAML or a Python dict in `experiments/config.py`, not hard-coded in loops.
- Prefer boring, well-known libraries. Ask before adding a dependency.
