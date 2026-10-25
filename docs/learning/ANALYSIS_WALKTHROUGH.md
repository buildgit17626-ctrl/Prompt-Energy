# Analysing your prompt-energy experiment: an owner workbook

Prepared 2026-10-25 from the registered P4 data. This is a learning guide, not
the owner's report or a change to the analysis plan. No new generations are
needed. The owner supplies interpretation. Keep observations, possible
explanations and limitations in separate sentences.

## 1. Start with a question, then identify your evidence

Write: "On these 40 HumanEval tasks and this laptop, how do the registered
prompt variants change output length, runtime, CPU package energy and test
success for each model?" The scope matters: two small models and one machine
do not establish what all LLMs do.

One row represents one task/model/prompt/repeat generation, not a new independent
task. Stage 1 has 560 rows: 40 tasks x 7 arms x 2 models, once each. Stage 2 has
280 rows: 10 preselected tasks x 7 arms x 2 models x two extra repeats.
Use stage 1 for prompt comparisons and stage 2 for repeat diagnostics. Do not
pool them: otherwise those ten tasks get three times the weight.
Smoke, pilot, warm-up and calibration outputs are excluded from hypothesis tests.
P0 is the overall baseline but is excluded from group-wise comparisons.

Exercise: explain the difference between "840 requests" and "40 tasks" aloud.

## 2. Audit before interpreting

The audit in results/P4-final-audit.json verified 840 unique complete jobs,
matching raw/outcome/measurement IDs, no uncertain intents, all 846 sensor-prefix
checksums across four retained mirrors, and zero API calls on completed resume.
Evidence stayed byte-for-byte unchanged. This is record integrity, not proof
that measurements have no bias or noise.

Stage 1: 347/560 passed, all 560 primary energy estimates exist. All 560 carry
baseline_drift; 70 are low resolution. Its block baseline fell from 17.5530 W
to 11.5164 W. Net energy uses the starting baseline as registered. All stage-1
arms were interleaved within this block, which helps distribute time effects
but cannot prove drift did not influence comparisons. Do not replace the start
baseline with the endpoint or filter away every drift-flagged row.

Stage 2: 224/280 passed, 181 energy estimates exist and 99 are missing after
sensor gaps. 148 rows have no closing baseline, 32 are low resolution and eight
net estimates are negative. These flags can overlap. Only 64 of 140 repeat pairs
have both energy values. The subset has different tasks, so its 80% success rate
cannot be compared with stage 1 as evidence of improvement.

Missing energy is unavailable, never zero. Negative net energy is retained; it
means measured gross energy was below the baseline correction, not that the
computer generated electricity. A failed candidate is a valid correctness
observation, even if its energy reading is missing.

Exercise: write three sentences about data quality before naming any prompt.

## 3. Open the generated tables in this order

Use results/p4-analysis/all_rows/summary.csv first. Each of its 14 rows is one
model/arm combination, with 40 task outcomes. Read these columns:

- rows/successes/passed_mean: attempted tasks, correct tasks, success fraction.
- input_tokens_mean/output_tokens_mean: native Ollama token counts.
- cpu_pkg_post_load_raw_wh_mean: gross estimated post-load CPU package energy.
- cpu_pkg_energy_wh_mean: net estimate after subtracting the starting idle rate.
- cpu_pkg_energy_wh_per_correct: total net cost of all attempts / successes.
- *_n, *_low and *_high: available count and task-bootstrap interval endpoints.

The primary low-resolution sensitivity table is in
without_primary_low_resolution/summary.csv. It has 490 stage-1 rows across
arms, so check per-arm denominators. Dropping short windows can also change the
task mix and pass rates; keep all-attempt correctness visible in all-outcomes.csv.
The source is results/p4-full/full.csv. Never edit it or raw.jsonl to clean up
an inconvenient outcome. Change only derived analysis code, recording changes.

Regenerate the registered scaffolds from the project root:

```powershell
.\.venv313\Scripts\python.exe -m analysis.full_analysis --run results/p4-full --output results/p4-analysis
```

## 4. Learn one comparison before scanning all arms

For 1.5b in stage 1:

| Quantity | P1 code only | P3_1 one example |
| --- | ---: | ---: |
| Correct / attempted | 29/40 | 30/40 |
| Pass rate | 72.5% | 75.0% |
| Mean output tokens | 71.10 | 130.25 |
| Mean net post-load energy, Wh | 0.023585 | 0.040935 |
| Mean gross post-load energy, Wh | 0.043592 | 0.075063 |
| Net energy per correct, Wh | 0.032531 | 0.054581 |

Tool/mode for these energy values: HWiNFO CPU Package Power, trapezoidal
integration, approximate post-load window; net subtracts the block start idle
baseline. These are descriptive sample values with the drift limitation above.

An observation is "P3_1 solved one additional task and used more mean energy in
this sample." A possible explanation is that added examples changed generation
length. Do not write "one example always improves accuracy" from one task's
aggregate difference. Inspect which tasks changed: the 29 and 30 correct answers
need not be the same tasks.

Pass-rate difference: 75.0 - 72.5 = 2.5 percentage points, not 2.5 percent.
A single task is 2.5 points when the denominator is 40.

Energy-per-correct = sum(energy of all attempts) / number of correct attempts.
For P1, roughly (40 x 0.023585) / 29 = 0.03253 Wh per correct solution.
It includes failed-attempt costs. It is a sample aggregate, not a guarantee of
cost for a new task or the expected cost of repeated independent retries.

Exercise: write one observation, one explanation and one limitation for P1/P5.

## 5. Read the figures and uncertainty without overclaiming

In all_rows/pareto.png, left means less net energy and up means more success.
Compare each model separately. A point is dominated in the observed sample if
another has no more energy and no lower success, with at least one strict
improvement. An attractive point is a trade-off, not a universal winner. The
figure has no uncertainty bars: use the table's intervals and exact counts too.

The registered bootstrap resamples task rows 2,000 times (seed 1729) and takes
95% percentile intervals. This describes sampling variability under those
assumptions. It does not fix power drift, benchmark contamination, deterministic
output variation or task representativeness. Do not call interval width a
measurement of all uncertainty. Overlap/non-overlap of two separate intervals
is not the formal paired test of their difference.

Use the matched design: compare P1 and another arm on the same tasks, not two
unrelated collections. A paired task table helps distinguish broad changes from
one or two influential tasks. Do not silently choose exclusions or new tests
because the result becomes more attractive; label additions as exploratory.

## 6. Connect each hypothesis to a comparison

| Hypothesis | What to inspect | What you cannot infer automatically |
| --- | --- | --- |
| H1: output length explains energy/time | token counts, energy, timing; per-model regression and residuals | joint R2 alone does not isolate input vs output contribution or prove cause |
| H2: concise output, group-dependent success | P1 vs P0 overall; eligible non-P0 arms within frozen solved/failed groups | calibration labels are not universal easy/hard labels |
| H3: few-shot cost and verified yield | P3_1/P3_3 vs P0/P1; tokens, successes, cost per correct | examples must improve success on all tasks/models |
| H4: step-by-step costs/benefits | P4 vs baseline overall, non-P0 group comparisons | more explanation is evidence of better reasoning |
| H5: instruction verbosity | P5 vs P1 input tokens, native timings, output length, whole post-load energy | input-phase energy: polling could not measure it |

Read all_rows/regression.csv and residuals.png. The existing regression is joint
OLS: energy = intercept + input coefficient x input tokens + output coefficient
x output tokens, separately by model. A residual is observed minus fitted energy.
Patterns or large residuals suggest variation left unexplained. R2 measures fit
to these data, not held-out prediction or causal proof. The 280 rows per model
contain repeated tasks across arms; they are not 280 independent tasks.

Comparing input-only, output-only and joint fits would help quantify each
predictor's contribution; the current regression.csv contains only joint fits.
Any added fit/comparison should be explicitly documented, retaining the existing
registered outputs. Comparing coefficient magnitudes alone is insufficient
because the predictors vary over different ranges and are related.

Read calibration-groups.csv and reference_length-groups.csv. Solved/failed maps
were frozen from a separate 1.5b/P0 calibration (26/14 tasks). The reference length
split is 21 short/19 long, median six lines, ties short. Length is a proxy, not a
measurement of difficulty. Report the actual smaller per-arm group sizes.

Exercise: for each hypothesis write "consistent", "mixed", "not consistent" or
"not measurable here", followed by evidence and the strongest caveat. These are
descriptive judgements, not declarations of statistical proof.

## 7. Read repeat diagnostics separately

stage2-noise.csv pairs repeats 2 and 3 within task/model/arm. Read rows,
energy_available, energy_sd_wh, absolute_repeat_difference_wh and output_token_sd.
Only 64 pairs have both energy measurements. A one-value pair cannot establish
repeat spread. Missingness followed interrupted blocks and can be nonrandom.
Compare the version excluding primary low resolution, retaining pair counts.

Repeated generations can differ in output even with temperature zero/seed fixed.
Therefore observed spread mixes output variation, hardware/background changes
and sensor measurement noise. Do not describe it as pure meter precision.
The ten-task subset was selected without outcome inspection, but is still small.

## 8. Keep a research notebook and write your own conclusion

For each analysis entry, record:

1. Date, question/hypothesis and exact source/derived file.
2. Stage/model/prompts, row counts, exclusions and units.
3. An observation with numbers, denominator and uncertainty where available.
4. A plausible explanation, explicitly labelled as an explanation.
5. An alternative explanation or measurement limitation.
6. Whether this was registered or an additional exploratory analysis.

Use this sentence structure: "On [scope], [arm] produced [result] compared with
[arm]. This is consistent with [hypothesis/possible explanation]. However,
[limitation], so we conclude only [bounded claim]." Fill it yourself.

Report failures, truncation and unresolved hypotheses alongside attractive
results. Passing HumanEval tests means passing those checks, not proof of
correctness for every possible input. CPU package energy excludes the rest of
the laptop, so do not label it whole-system electricity, carbon savings or bill
cost. No input/output phase-energy attribution is supported here.

Your first exercise: explain the 1.5b P1/P3_1 comparison in 150-200 words, include
both counts, cost per correct, and the drift caveat. Then repeat for P1/P5.

## Assumptions and remaining work

This guide uses the fixed 560/280 split, the original outcome and measurement
journals, original idle corrections and existing analysis code. It changes no
protocol, grouping, seed, generation or outcome. A checksum-valid record can
still be a low-quality measurement. Complete final backups/validation and owner
review are still needed for P4 close-out; P5 is not started. Final interpretation
and report prose belong to the owner.
