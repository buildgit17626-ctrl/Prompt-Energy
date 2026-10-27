# P4 baseline experiment: methods and setup

Prepared 2026-10-27 for owner review. This describes the saved P4 experiment,
not the computer used later for Colab analysis. Inference was local on the
owner's laptop. No additional inference was performed to produce these figures.

## Hardware, operating system and software

| Component | Saved setting or observation |
| --- | --- |
| CPU | 13th Gen Intel Core i5-13420H |
| Memory | Owner-described 16 GB; session reports 16,786,780,160 physical bytes |
| GPU | No discrete GPU reported; requested CPU-only inference, num_gpu=0 |
| OS | Windows 11; saved string Windows-11-10.0.26300-SP0 |
| Interpreter | Python 3.13.7, 64-bit, MSC v.1944 AMD64; project .venv313 |
| Runtime | Ollama 0.40.6, local HTTP /api/generate at 127.0.0.1:11434 |
| Models | qwen2.5-coder:0.5b and qwen2.5-coder:1.5b |
| Weights | GGUF; both installed models report Q4_K_M quantization |
| NumPy / pandas | 2.2.6 / 2.2.3 |
| SciPy / Matplotlib | 1.15.3 / 3.10.3 |
| psutil / pytest / Ruff | 7.0.0 / 8.3.5 / 0.11.13 |
| CodeCarbon | 3.0.4 retained as a dependency for historical pilot reproduction; disabled in P4 scored execution |

Model digests from the frozen manifest (tags alone are not immutable):

- 0.5b: `4ff64a7f502a08b7616edb8ca0a79eb1853fc363d842b7df4b46915d11a3fb09`
- 1.5b: `d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668`

The manifest retains model templates, parameters, details and licence text.
Both installed model licence texts include Apache 2.0. HumanEval is MIT licensed;
the pinned archive, notice and checksum are retained under data/. See REFERENCES.

## Inference and token limits

| Setting | Value and interpretation |
| --- | --- |
| temperature | 0; not a guarantee of bit-identical responses on this runtime |
| seed | 1729 |
| num_thread | 8 requested CPU threads |
| num_ctx | 4096-token context setting; not an instruction to use 4096 input tokens |
| num_predict | 768-token maximum generation budget for every arm; not fixed actual output length |
| Input length | Variable with task and prompt. No separate fixed input-token length or padding. Stage-1 observed prompt_eval_count spans 74-471 for each model |
| Output length | Native eval_count; stage-1 ranges 50-768 (0.5b), 16-768 (1.5b) |
| Prompt/system | Common system text: "You are a helpful coding assistant." Exact seven user-arm texts and assembly in PROMPTS.md |
| History | Each request independent; no conversational memory or deliberate recall experiment |
| Scheduling | One scored request at a time, seeded interleaving; no concurrent client request batching or batch-size sweep |
| Stop rules | Same across arms; no custom stop strings; registered truncation precedence retained |
| keep_alive | 0 for scored runs under the recorded conservative cache-avoidance rule; loading overhead recorded separately |
| Warm-up | One saved, excluded READY request per used model per process session; unload before scored work under keep_alive=0 |
| Token/timing sources | Ollama response fields prompt_eval_count, eval_count, load_duration, prompt_eval_duration, eval_duration, total_duration; durations in ns |

The native model metadata can advertise a larger supported context (e.g. 32768);
the experiment's requested context was 4096. No context-length, quantization,
thread-count or batch-size optimization was conducted. Prompt directives change
requested text, not network depth. The two models have different parameters;
smaller models do not call extra networks to solve hard tasks.

## Tasks, repeats and correctness

Forty fixed HumanEval tasks selected with seed 1729 from the pinned population.
Stage 1: 40 tasks x seven arms x two models x one repeat = 560 attempts.
Stage 2: ten preselected tasks x seven arms x two models x two extra repeats =
280. Main comparisons use stage 1; stage 2 only diagnoses repeat variation.
Smoke, pilot, calibration and warm-up outcomes are excluded from hypothesis tests.
Run order and stage-2 IDs were frozen before generation. Raw responses, request
intents, outcomes, environment sessions and measurements remain auditable.

Calibration grouping was frozen before the scored run: 26 solved / 14 failed
from a separate 1.5b/P0 calibration. Reference-length sensitivity groups: 21 short /
19 long, median six nonblank, non-comment-only canonical body lines, ties short.
P0 is excluded from group-wise comparisons. These are not intrinsic difficulty labels.

Extraction uses the last complete python/py/unlabelled fenced block that parses
and defines the required entry point, falling back to the whole stripped response.
The trusted task prelude is prepended; no reference solution is supplied.
Code runs only in a fresh subprocess, five-second deadline, 256 MiB committed
memory limit, one-process Windows Job Object, temporary directory, minimal
environment, AST/import restrictions and Python-level socket/DNS denial.
This is not a hostile-code OS security boundary; see SAFETY.md. Passing means
passing the supplied tests, not proven correctness for every possible input.
Failed tests, truncation, timeout, no_code, syntax/policy and infrastructure
failures have distinct recorded rules; failures are not silently removed.

## Power and measurement

HWiNFO64 8.54-6090 logs CPU Package Power [W], requested 500 ms polling, direct
disk logging. CSV: cp1252, comma separator, decimal dot, date %d.%m.%Y,
time %H:%M:%S.%f, UTC+05:30. Preflight checks growing/fresh logs and cadence.
The runner records client times and rechecks AC/Best performance before requests.
The first saved P4 session confirms ACLineStatus=1 and Best performance overlay
ded574b5-45a0-4f42-8737-46345c09c238. Balanced base plan and Best performance
overlay are different settings. Intended overnight checklist: plugged in, lid
open, AC sleep disabled, unnecessary apps closed. The logs do not prove that
every background process remained inactive throughout every request.

Energy is the trapezoidal integral of CPU package power, not wall-plug energy.
It excludes display, storage and whole-system electricity; do not equate it
with carbon emissions or monetary cost. Candidate testing follows generation
and is outside the request window. A five-second quiet gap is registered.
Each block has 60-second start/end idle windows after model unload; net energy
subtracts the start baseline over the relevant window. Blocks stop launching
after three hours, finish bounded work, with a four-hour safety ceiling.

The whole API call includes loading. Primary approximate post-load interval:
[client request start + Ollama load_duration, response end]. API aggregate
durations are not synchronized phase timestamps, so this does not establish an
exact loading boundary. No measured input-versus-output energy allocation is
supported: pilot prompt-processing windows were all low resolution.

| Saved field | Meaning |
| --- | --- |
| cpu_pkg_total_raw_wh | Gross CPU package energy over whole request including loading |
| cpu_pkg_total_wh | Whole-request energy minus start-idle correction |
| cpu_pkg_post_load_raw_wh | Gross energy over approximate post-load window |
| cpu_pkg_energy_wh | Net post-load energy; primary baseline-adjusted field |
| energy per correct | Sum of ALL attempt energy / successful attempts; not mean energy of successful attempts |
| output tokens per correct | Sum of ALL generated tokens / successful attempts |

Plots convert Wh to mWh by multiplying by 1000. Primary windows shorter than
three seconds are low resolution; sensor gaps or insufficient coverage retain
missing energy, never zero. Drift is flagged when the end idle rate differs
from the start by more than max(1 W, 10% of start).

Stage 1 has 560/560 energies, all baseline-drift flagged: first block idle fell
17.5530 to 11.5164 W. Seventy primary windows are low resolution. Stage 2 has
181/280 energies, 99 missing, 148 rows missing a closing baseline, 32 low-resolution
windows and eight negative net readings; flags overlap. Only 64/140 repeat pairs
have both energy values. Power interruptions and stopped logs are limitations,
not measurements to repair. Preserve negative estimates and original baselines.

## Analysis and reproducibility

Stage-1 summaries use 40 tasks per model/arm, including failures. Registered
95% percentile task-bootstrap intervals: seed 1729, 2000 draws. Aggregate
per-correct ratios and new focused figures are labelled as point estimates where
no intervals are supplied. Intervals do not encompass baseline bias. The registered
sensitivity excludes only primary-low-resolution rows (490/560 remain), changing
per-arm task mix. Do not discard all drift rows, which would discard all stage 1.

Comparison figures are post-collection descriptive extensions, not amended
pre-registered hypotheses or new significance tests. Main stage completed in the
first block on 2026-10-22 IST; later blocks completed stage 2 on 2026-10-23 IST.
The full.csv source SHA-256 is
`b426f6bb5e79af91e437623e6692b9b2f41efc7aad7faec99ef50f81dba6e0e0`.

Sources: results/p4-full/{manifest.json,sessions.jsonl,full.csv,blocks.jsonl},
requirements.txt, docs/{SPEC.md,PROMPTS.md,ENVIRONMENT.md,SAFETY.md,REFERENCES.md}.
The source manifest, rather than this prose, is authoritative for exact templates
and executable fingerprints. Colab is an analysis workspace, not the inference
environment. Owner interpretation and final wording require approval.
