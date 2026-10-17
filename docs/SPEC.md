# SPEC: The cost of a correct answer

Working title: **Prompt design and the cost of a correct answer: tokens, estimated energy and verified yield in small-model code generation**

## 1. Research question
How do common prompt design choices (instruction style, few-shot examples, reasoning requests, output-length constraints, prompt compression) change token use, latency, estimated energy and task success for small open-weight code models running locally, and what is the energy cost per *correct* solution?

## 2. What is already known (read first; this is a replication-plus-extension)
Earlier work reports that inference energy is driven mainly by output length and response time, that targeted prompt phrases which shorten outputs can cut energy while preserving quality, and that prompt characteristics themselves show weak association with energy. Our contribution is deliberately modest:
1. A **verified-yield metric**: energy (and tokens) per correct solution, not per response.
2. A **controlled comparison of prompt variants** on code tasks with automatic correctness checks.
3. A replication across 2 to 3 small model sizes on consumer hardware.
Do not claim novelty beyond this.

## 3. Hypotheses (fixed before any run)
- **H1:** Output tokens explain most of the variation in latency and estimated energy across prompt variants.
- **H2:** Concise-output prompts reduce tokens and energy with little loss in pass rate on easy tasks, but may lower pass rate on harder tasks.
- **H3:** Few-shot examples raise input tokens and may raise pass rate; the net effect on energy per correct solution depends on whether it removes failures.
- **H4:** Step-by-step reasoning prompts raise tokens and energy substantially; benefits concentrate on harder tasks, so energy per correct solution may be worse overall.
- **H5 (optional):** Compressing the prompt reduces energy less than its token reduction suggests.
Report results against each hypothesis, including negative results.

## 4. Scope
- Environment: Python 3.13 (64-bit), per the owner's 2026-10-17 update; validated exact patch version is recorded in `docs/ENVIRONMENT.md`.
- Local inference only. Open-weight models of roughly 0.5B to 3B parameters that run on a laptop (exact choices fixed in `config.py`, with licences checked).
- Tasks: 30 to 60 short Python programming tasks with unit tests, from a permissively licensed benchmark subset (for example HumanEval or MBPP, after checking licences), split into easy and harder groups by a baseline pass rate. Note possible training-data contamination as a limitation.
- API models: out of scope for energy (it cannot be measured). Optional token-count-only comparison, clearly labelled as such.

## 5. Protocol
- **Prompt variants (pre-registered):** P0 minimal baseline; P1 "return only code"; P2 "explain, then code"; P3 few-shot with 1 and 3 examples; P4 step-by-step reasoning then code; P5 compressed (shortened) instructions.
- **Decoding:** deterministic (temperature 0 or fixed seeds), fixed `max_new_tokens`, identical stop rules.
- **Correctness:** extract code, run unit tests in a restricted sandbox (see AGENTS.md safety rules), record pass or fail, timeouts and extraction failures separately.
- **Repeats:** 3 repeats per (model, prompt, task) to estimate measurement noise.
- **Measurement:** Primary: **CPU Package Power** logged by HWiNFO (confirmed available on the owner's Intel i5-13420H laptop) to CSV at a 1-second interval and integrated over each generation window. The runner records start and end timestamps on the same clock, and an idle baseline measured for 60 seconds before each batch is subtracted. Secondary: CodeCarbon (offline mode), which on Windows estimates power from CPU load and an assumed power rating, so report it only as a cross-check. Also record tokens in, tokens out, wall time and tokens per second. CPU package power excludes memory, display, storage and the rest of the laptop, so say so clearly and treat results as relative comparisons on one machine. Flag any generation shorter than about 3 seconds as low resolution. If a plug-in wall power meter is available, calibrate on a small subset and report it.
- **Machine rules:** plugged in, Windows Power mode set by the owner to Best performance, close other heavy apps, fixed thread count, cool-down gaps between batches. Record actual observed power mode and AC state; do not replace observations with the intended setting.
- **Scale check:** with 40 tasks, 7 prompt conditions (P3 has one- and three-example arms), 2 models and 3 repeats there are 1,680 generations. Estimate run time in milestone P3; ask the owner before changing tasks or repeats.

### P1 registration (2026-10-16)
- Models: `qwen2.5-coder:0.5b` and `qwen2.5-coder:1.5b` in Ollama; both exact tag pages list Apache 2.0. Record local digests in P2 because tags can change.
- HumanEval is MIT licensed. Use the unchanged archive at revision `6d43fb980f9fee3c892a914eda09951f772ad10d`, SHA-256 recorded in `data/manifest.json`; retain its licence notice.
- Sample 40 IDs without replacement from the numeric population 0..163 with `random.Random(1729)`, then sort numerically. Explicit IDs are in `experiments/config.py`. No task is replaced after reference checks.
- Prompt wording and three original synthetic examples are in config. P3_1 uses the first example; P3_3 uses all three in the recorded order. Actual prompt assembly and code extraction remain P2.
- The Windows test runner uses a five-second deadline, 256 MiB commit-memory cap, one-process Job Object, curated computation imports/builtins, socket/DNS audit denial, fresh temp directory and a minimal environment. Candidate script loading occurs only in the worker. Python hash and random seeds are 1729. Cleanup retries transient Windows locks for up to two seconds after reaping; persistent cleanup errors are logged as infrastructure failures. See `docs/SAFETY.md` for exact restrictions and the absence of an OS security boundary.
- HumanEval/160 uses eval in its original reference. The runner substitutes a numeric arithmetic AST interpreter for that builtin, equally for references and model solutions, without changing benchmark records. Policy rejection remains distinct from incorrectness.
- P2 runtime contract: local Ollama `/api/generate`, temperature 0, fixed seed 1729, one fixed `num_predict` output-token cap and identical stop rules. Register the cap and thread count before generation; P1 does not choose them through test performance. Read `prompt_eval_count`, `eval_count`, `total_duration`, `load_duration`, `prompt_eval_duration`, and `eval_duration` from responses; duration fields are nanoseconds. Do not estimate token counts from text. Persist raw response fields, local model digest and Ollama version. CPU-only execution is intended.
- Owner-decided difficulty rule (2026-10-17): group each task by whether `qwen2.5-coder:1.5b` passes with prompt P0 in a calibration run. Fix the calibration settings and resulting grouping in config before the main run. Exclude P0 from group-wise comparisons to avoid defining and assessing its performance on the same grouping criterion. Add a sensitivity grouping by reference solution length. Record this rule only in P1: no grouping code, calibration, labels or length threshold yet. Calibration generations are additional to the approximately 1,680 main-run generations.
- Few-shot examples must be original and not duplicate or specialize any selected task. The semantic audit is in `docs/FEW_SHOT_REVIEW.md`. The initial add-seven example was replaced before any inference because it specialized HumanEval/53.

## 6. Results schema (one row per generation)
`run_id, timestamp, model, model_hash, prompt_id, task_id, difficulty_group, repeat, seed, input_tokens, output_tokens, wall_seconds, tokens_per_second, cpu_pkg_energy_wh, codecarbon_wh, idle_baseline_w, co2e_kg, passed, failure_type, raw_output_path, python, runtime_version, codecarbon, cpu_model, os, power_mode`

## 7. Analysis plan (the owner writes this)
1. Per model and prompt: mean and 95% bootstrap interval for input tokens, output tokens, energy and pass rate.
2. Energy per correct solution; Pareto plot of pass rate versus energy.
3. Regression of energy on output tokens and on input tokens (H1); report R squared and residuals.
4. Breakdown by the owner-decided calibration group (H2, H4), excluding P0 from group-wise comparisons; sensitivity grouping by reference solution length. No grouping is implemented in P1.
5. Measurement noise from repeats; check whether conclusions hold when the noisiest runs are removed.
6. Limitations: estimated energy, one machine, small models, small task set, benchmark contamination.
Avoid strong significance claims; use descriptive statistics and bootstrap intervals.

## 8. Milestones and acceptance criteria
**P1: Scaffold, tasks and sandboxed test runner.**
- Repo layout, pinned requirements, `config.py` with the pre-registered prompts, models and task list, task loader, restricted-subprocess test runner (`docs/SAFETY.md`).
- *Accept:* reference solutions for all tasks pass, deliberately wrong solutions fail, a runaway or malicious test sample is killed by the timeout; tests pass.

**P2: Local model runner and prompt variants.**
- Chosen runtime (justified in the plan), deterministic decoding, exact token counting, prompt builder for all variants, raw generations saved as JSONL.
- *Accept:* a smoke run on 5 tasks across all prompts completes; token counts match the runtime's own counts; failures are logged.

**P3: Energy tracking.**
- CodeCarbon integration, idle baseline subtraction, repeats, machine metadata, run-time estimate for the full run.
- *Accept:* energy columns filled; a noise script reports spread across repeats; the measurement mode is stated in outputs.

**P4: Full run and analysis scripts.**
- Resumable full run (skips completed rows), analysis scripts for section 7 producing CSV and PNG.
- *Accept:* an interrupted run resumes without duplicates; every plot labels the tool and mode.

**P5: Report scaffold and reproducibility.**
- `docs/REPORT_TEMPLATE.md`, README with exact commands, `docs/REFERENCES.md`.
- *Accept:* a fresh clone can reproduce a one-task-subset run following the README.

## 9. Report outline (3 to 4 pages, written by the owner)
1. Question, prior work and hypotheses.
2. Method: tasks, models, prompts, correctness checks, energy measurement and its limits.
3. Results: three or four figures and one summary table.
4. Discussion: which hypotheses held; practical guidance on prompts that save energy without losing correctness.
5. Limitations and next steps (larger models, GPU measurements, real power meters, other tasks, links to the validity and solvability studies).
6. References.

## 10. Background reading (find by title and verify)
- "Towards Sustainable NLP: Insights from Benchmarking Inference Energy in Large Language Models" (2025).
- MELODI: an inference-time energy profiling framework (arXiv 2407.16893).
- TokenPowerBench: benchmarking power consumption of LLM inference (AAAI).
- "Green AI" (Schwartz et al.); "Energy and Policy Considerations for Deep Learning in NLP" (Strubell et al.).
- "Evaluating Large Language Models Trained on Code" (the HumanEval paper).
- CodeCarbon documentation, especially how it estimates power.

## 11. How this extends (for pitches)
With more resources: GPU measurements with real power meters, larger models, other task types, and a link to the owner's studies on LLM-generated problem validity and solvability (energy and token cost per verified problem).
