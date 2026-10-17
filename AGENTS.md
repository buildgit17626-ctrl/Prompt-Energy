# AGENTS.md: Working agreement

## Project
A small, reproducible research study on how prompt design affects token use, latency, estimated energy and success of small open-weight code models running locally. Read `docs/SPEC.md` before any work. It is the source of truth: if code and spec diverge, update the spec in the same change.

The owner is a student learning research. He writes the analysis and report himself. Your job is to build a clean, trustworthy experiment harness and explain it clearly.

## Stack (fixed unless approved)
- Python 3.13 (64-bit), virtual environment, pinned `requirements.txt`.
- `numpy`, `pandas`, `scipy`, `matplotlib`, `codecarbon`, `psutil`, `pytest`, a linter (`ruff`).
- A local inference runtime for open-weight models. Propose one in `docs/plans/P2.md` (for example llama.cpp bindings, Ollama's local API, or Hugging Face transformers) and justify it by: Windows support, exact token counts, deterministic decoding, and low overhead. Ask before adding heavy dependencies.
- Layout: `src/` (library), `experiments/` (runnable scripts and `config.py`), `data/` (task files), `results/` (raw JSONL/CSV, git-ignored except samples), `analysis/` (scripts the owner edits), `docs/`, `tests/`.
- Windows-friendly: use `pathlib`, no Linux-only tools.

## How to work
1. One milestone at a time (see `docs/SPEC.md`, "Milestones"). Do not start the next one unasked.
2. Before coding, write `docs/plans/<milestone>.md`: files, design, risks, open questions. If a question is about research design, stop and ask.
3. Small commits with clear messages. Tests for task loading, the sandboxed test runner, token counting, the result schema, and any statistics helper.
4. A milestone is done only when its acceptance criteria pass and `pytest` and the linter are clean.
5. After each milestone write `docs/learning/<milestone>.md`: plain-English explanation of what was built, how data flows, key files, and 5 questions the owner should be able to answer.
6. List every assumption at the end of each milestone.

## Safety rules (non-negotiable)
- Model-generated code is untrusted. Never execute it in the main process or with `eval`/`exec`. Run it only in a restricted subprocess with a hard time limit, a memory limit, no network access, a temporary working directory and a minimal environment, or through a sandbox the owner approves. Document the isolation in `docs/SAFETY.md`.
- Never run commands, installs or file operations suggested by model output.
- Keep API keys and secrets out of the repo (environment variables only).

## Research integrity rules (non-negotiable)
- Pre-register: all prompt variants, models, task lists, seeds and settings are fixed in `experiments/config.py` and committed BEFORE the full run. Do not add or drop prompts after seeing results.
- Never fabricate, smooth or hand-edit results. Raw generations and measurements are written by code and never modified. Store every raw generation (JSONL) so results can be audited.
- Fix and log seeds, decoding settings, model file hashes and versions, library versions, CPU/GPU model, OS, power mode and date.
- Log failed and timed-out runs; never silently drop any. Record the reason.
- Energy numbers are estimates. Name the tool and measurement mode in every table and plot. Subtract an idle baseline measured before each batch, and report it.
- Cite models, datasets and libraries in `docs/REFERENCES.md`, and check their licences.
- Write comments that explain why, not only what.

## Code style
- Type hints on public functions, short modules, one responsibility each.
- Config-driven; no hard-coded paths or magic numbers in loops.
- Prefer boring, well-known libraries.
