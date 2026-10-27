# P4 expectations versus observations: owner review draft

Prepared 2026-10-27. **Interpretation approval pending.** This record combines the
owner's working expectations, their observations and verified numerical corrections.
It does not mark conclusions accepted. H1-H5 retain their original registration.
Owner expectations supplied during this review are labelled later working
expectations; their pre-run timing has not been established. Results are descriptive,
not proof or disproof of a population hypothesis. The owner remains final author.

Read [setup and methods](P4_SETUP.md) alongside this record. Main comparisons:
560 stage-1 attempts, 40 tasks per arm/model. Stage 2 is not pooled. Energy below
is HWiNFO CPU Package Power, trapezoidal integration, approximate post-load,
start-idle-adjusted net unless explicitly gross. All stage-1 energy is drift-flagged;
70 windows are low resolution. No new model requests or outcome repairs.

## 1. The owner's three prompt families, with precise wording

| Presentation family | Arms | What differs |
| --- | --- | --- |
| Task-completion instructions | P0, P1, P5 | Minimal request versus short code-only versus long code-only instruction |
| Example-guided generation | P3_1, P3_3 | One versus three original input/output demonstrations |
| Explanation / step-by-step requests | P2, P4 | Explain then code versus reason step by step then code |

These are post-collection organizational labels, not new experimental arms or
pooled category estimates. P0 does not explicitly require code-only output.
Explanation text does not establish internal reasoning or additional networks.

## 2. Numerical anchor table

All attempts, including failed ones, contribute to means and per-correct costs.
One task = 2.5 percentage points. Wh values are converted to mWh here.

| Model | Arm | Correct / 40 | Mean input tokens | Mean output tokens | Net mWh / attempt | Gross mWh / attempt | Net mWh / correct | Output tokens / correct |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5B | P0 | 24 | 162.05 | 462.20 | 52.65 | 97.91 | 87.74 | 770.33 |
| 0.5B | P1 | 24 | 166.05 | 227.50 | 26.61 | 49.74 | 44.34 | 379.17 |
| 0.5B | P5 | 22 | 198.05 | 243.55 | 29.52 | 55.06 | 53.67 | 442.82 |
| 0.5B | P3_1 | 21 | 212.05 | 357.82 | 41.05 | 77.54 | 78.18 | 681.57 |
| 0.5B | P3_3 | 19 | 285.05 | 194.22 | 25.18 | 48.68 | 53.01 | 408.89 |
| 0.5B | P2 | 22 | 169.05 | 530.95 | 59.13 | 110.66 | 107.50 | 965.36 |
| 0.5B | P4 | 22 | 169.05 | 520.38 | 57.28 | 106.80 | 104.14 | 946.14 |
| 1.5B | P0 | 26 | 162.05 | 336.07 | 89.06 | 164.73 | 137.01 | 517.04 |
| 1.5B | P1 | 29 | 166.05 | 71.10 | 23.59 | 43.59 | 32.53 | 98.07 |
| 1.5B | P5 | 27 | 198.05 | 73.62 | 25.28 | 46.68 | 37.44 | 109.07 |
| 1.5B | P3_1 | 30 | 212.05 | 130.25 | 40.94 | 75.06 | 54.58 | 173.67 |
| 1.5B | P3_3 | 28 | 285.05 | 98.22 | 33.84 | 63.02 | 48.34 | 140.32 |
| 1.5B | P2 | 26 | 169.05 | 500.10 | 128.29 | 239.78 | 197.37 | 769.38 |
| 1.5B | P4 | 27 | 169.05 | 526.50 | 136.34 | 253.52 | 201.99 | 780.00 |

Full-precision values, intervals and independently recalculated summaries are
in results/p4-analysis/all_rows/summary.csv and results/p4-comparisons/summary.csv.
Rounding in this table does not change original measurements.

## 3. Original pre-registered hypotheses and descriptive review

### H1

**Registered:** Output tokens explain most of the variation in latency and
estimated energy across prompt variants.

**Evidence:** P1 versus P2 has 227.50 versus 530.95 output tokens and 26.61 versus
59.13 net mWh on 0.5B; 71.10 versus 500.10 tokens and 23.59 versus 128.29 mWh
on 1.5B. Existing joint input/output OLS has net R-squared 0.974 (0.5B) and
0.993 (1.5B), 280 requests each using the same 40 tasks across arms.

**Review status:** Consistent with a strong token-energy association, not proof
that output explains most variation independently. Joint fit alone cannot isolate
output from input contribution, demonstrate causation, or establish latency's
variance decomposition. Do not turn a seven-mean scatter into a linear-law claim.

### H2

**Registered:** Concise-output prompts reduce tokens and energy with little loss
in pass rate on easy tasks, but may lower pass rate on harder tasks.

**Evidence:** P1 versus P0 reduces cost and output substantially. Correct counts
are 24 versus 24 (0.5B) and 29 versus 26 (1.5B). Within frozen calibration-failed
tasks, P1 passes 8/14 (0.5B) and 6/14 (1.5B); P3_1 passes 4/14 and 8/14.

**Other angle:** Overall concise efficiency is visible, but a general harder-task
accuracy penalty is not established. P1 beats P3_1 on the 0.5B failed group and
loses on the 1.5B failed group. P0 is excluded from group-wise comparisons by
registration; labels are tied to one separate 1.5B/P0 calibration, not universal
easy/hard categories. Review wording: mixed, model-dependent group evidence.

### H3

**Registered:** Few-shot examples raise input tokens and may raise pass rate;
the net effect on energy per correct solution depends on whether it removes failures.

**Evidence:** P1/P3_1/P3_3 average input counts are 166.05/212.05/285.05 for
both models. Correct counts: 24/21/19 on 0.5B; 29/30/28 on 1.5B.
P3_3 has lower energy than P3_1 despite longer input: 25.18 versus 41.05 mWh
(0.5B), 33.84 versus 40.94 (1.5B), accompanying shorter output.

**Where expectation fails:** More examples do not monotonically improve accuracy.
Three examples lower cost relative to one in this sample but lose successes.
P1 still has lower energy per correct than either example arm on both models.

### H4

**Registered:** Step-by-step reasoning prompts raise tokens and energy
substantially; benefits concentrate on harder tasks, so energy per correct
solution may be worse overall.

**Evidence:** P2/P4 have high output and per-correct energy. Yet in the 14
calibration-failed tasks P4 passes only 2 (0.5B) and 4 (1.5B), versus P1's
8 and 6. In the solved group, 0.5B P4 passes 20/26 versus P1's 16/26.

**Where expectation fails:** The anticipated concentration of P4 benefits on
harder tasks is not seen in these descriptive counts. On 0.5B the apparent
benefit is in the calibration-solved group instead. It is also incorrect to
say explanation-requesting arms are always least accurate: P3_3 is lowest on
0.5B; P0/P2 tie lowest on 1.5B. Increased requested explanation is not evidence
of deeper network execution. Failure mechanisms need saved-response inspection.

### H5

**Registered:** Longer instructions with the same demand raise prompt-processing
cost but change total energy little because output length dominates. Compare
the long code-only P5 instruction with the shorter code-only P1 instruction.
P2 records tokens and timings; energy is assessed only in later milestones.

**Evidence:** P5 adds 32 average input tokens to P1 on both models. Output is
243.55 versus 227.50 (0.5B) and 73.625 versus 71.10 (1.5B). Net energy is about
11.0% and 7.2% higher respectively. P5 has two fewer successes on each model.

**Other angle:** The owner's prediction of severe P5 degradation is not seen.
Outputs and whole-window costs are close, not identical. A causal prompt-phase
energy increase is unmeasurable here. "Little" has no registered equivalence
margin, so these differences do not establish equivalence. This is not proof
that verbose instructions cause hallucinations.

## 4. Owner's later working expectations, corrected wording

| ID | Expectation, expressed precisely | Evidence / qualification for owner review |
| --- | --- | --- |
| E1 | The 1.5B model should have higher success across prompts than 0.5B. | Observed in all seven aggregate arm comparisons; not every task. Across 280 matched task/arm cases only 0.5B passes in 21, only 1.5B in 60, both in 133, neither in 66. |
| E2 | The smaller model may generate longer answers and incur greater cost per successful solution. | It does generate more tokens on average (362.38 versus 247.98), but average net energy is LOWER (41.63 versus 68.19 mWh). Per-correct direction depends on arm. The proposed extra-networks mechanism is incorrect. |
| E3 | P1 should minimize output and energy while preserving correctness. | Strong descriptive efficiency, but not every minimum: 0.5B P3_3 has shorter output and lower per-attempt energy. 1.5B P3_1 has one more success. P1 minimizes per-correct energy and tokens for both models in all-row stage 1. |
| E4 | P0 should be competitive because it is short, but may permit unnecessary output. | P0 has lowest input mean but much longer output than P1. It ties P1's 0.5B success while using about twice the net energy; 1.5B also loses three successes. Input brevity alone does not guarantee efficient answers. |
| E5 | P2/P4 should incur higher output and cost and may fail more within a fixed token budget. | High cost is observed, but they are not uniformly least accurate. 768 is an output ceiling, not fixed length. Stage-1 1.5B P4 has no truncations: its 13 failures are test_failed. Do not attribute all failures to the cap. |
| E6 | One example should offer a better cost/accuracy trade-off than three. | Not monotonic. Three examples use less output/energy than one on both models but pass fewer tasks: 19 versus 21 and 28 versus 30. More input can accompany shorter output. |
| E7 | P5's added verbosity should substantially harm accuracy and energy. | Not observed to that degree: P5 is close to P1 in output and cost, with two fewer successes per model. No hallucination measure was collected. |
| E8 | A single prompt ordering should describe energy, tokens and success. | Different metrics and models have different rankings. Category order is categorical, not a linear numerical predictor. A monotonic ranking is not a linear relationship. |
| E9 | 1.5B should use less than half the energy of 0.5B. | Contradicted by aggregate means. Large/small net energy ratios range 0.86-2.38 across arms; 1.5B uses over twice as much for P2/P4, slightly less for P1/P5, nearly equal for P3_1. |
| E10 | Input means should rank P3_3 > P3_1 > P5 > P4 > P2 > P1 > P0. | Almost the proposed input order, but P2 and P4 TIE at 169.05. Actual ascending order: P0 < P1 < P2=P4 < P5 < P3_1 < P3_3. |
| E11 | Output/energy should follow P1 < P0 < P3_1 < P5 < P3_3 < P2 < P4. | Not observed. P3_3 is shortest-output 0.5B; P0 is much longer than P1/P5/examples; P2 exceeds P4 on 0.5B but not 1.5B. See focused figures rather than imposing one ranking. |

## 5. Corrections to the owner's ten observations

1. **"P1 is almost twice better than P3_1 in every field."** P1 uses less cost
   and output, but 1.5B P3_1 has 30 versus 29 successes. P3_1/P1 net-energy
   ratios are 1.54 (0.5B) and 1.74 (1.5B); not universally 2x.
2. **"P3_3 is better than P3_1/P1."** P3_3 lowers cost/output relative to P3_1
   on both models, but reduces success. On 0.5B it costs less per attempt than
   P1, yet more per correct (53.01 versus 44.34 mWh). "Better" needs a metric.
3. **"P0 is worse than P1/P3_1."** It is costlier, but 0.5B P0 passes 24 tasks,
   exceeding P3_1's 21 and tying P1. Keep accuracy and cost separate.
4. **"0.5B uses more tokens and energy with less accuracy."** More average
   tokens and lower aggregate accuracy, yes; more average energy, no. The
   larger model uses more mean net energy overall, with prompt-specific exceptions.
5. **"P4 is bad in everything, by 3-100x."** P4 input is only three tokens
   higher than P1 on average, but outputs are longer. On 1.5B P4/P1 output
   ratio is 7.41 and net energy ratio 5.78, not 100. P4's 27 successes exceed
   P0/P2's 26; on 0.5B its 22 exceed both example arms.
6. **"P3_1 has the highest energy per correct."** Incorrect: P2 and P4 are
   higher on both models; 1.5B P0 is also higher. Use the per-correct bar chart.
7. **"P2 and P4 behave identically."** Similar expensive-output pattern,
   not identical outcomes. 0.5B: both 22 successes, P2 costs more. 1.5B: P4
   passes 27 versus 26, costs more, and has a different failure mix.
8. **"P3_3 has lowest 0.5B accuracy."** Correct in stage 1: 19/40 (47.5%).
   It simultaneously has the lowest per-attempt energy/output on that model.
9. **"P5 is identical to P1, but less accurate."** Close output/cost, not
   identical. Correct counts are 22 versus 24 and 27 versus 29.
10. **"Reasoning prompts are worst; P3_3 is significantly better than P3_1;
    1.5B uses more energy."** P2/P4 are expensive, not always least accurate.
    P3_3 is cheaper but less successful than P3_1; no significance test supports
    that adjective. 1.5B's mean energy is higher overall, not for every arm.
    No other models were scored; broader-model statements need separate evidence.

## 6. Requested focused comparisons

**P0 / P1 / P5:** P1/P5's code-only demand accompanies much shorter output than
P0. P1 has lower energy and higher/equal success than P5 in both all-row models.
P5 is not a dramatic failure. These are observational prompt contrasts, not a
measurement of a particular internal reasoning process.

**P2 / P4:** Similar input lengths (exactly equal average native counts), long
outputs and high cost. P2 costs more on 0.5B; P4 costs more on 1.5B. The same
high-level family can reverse order across model sizes. Equal input length
does not imply equal output length or energy.

**P3_1 / P3_3:** Three examples raise input by 73 tokens on average but reduce
output by 163.60 tokens (0.5B) and 32.03 (1.5B). Correct counts decline by two
for each model. Lower generation cost and lower success coexist.

**P1 / P3_3 / P2:** Among these three, P1 has the most successes on both models
(24/19/22 and 29/28/26), and lowest net energy/output per correct. P3_3's
0.5B per-attempt energy/output advantage disappears when failed attempts count
towards verified yield. This requested contrast does not include the highest
1.5B pass-count arm P3_1; do not imply it exhaustively compares every prompt.

## 7. Figure inventory: no repeated broad views

The existing P4 brief is unchanged. Existing broad plots are reused, not redrawn:
02_output_energy (output tokens and gross/net energy by prompt),
03_verified_cost (gross/net energy per correct), and 05_resolution_sensitivity.
The review gallery includes clearly labelled copies of these existing files.

New supplementary figures in results/p4-comparisons, PNG and vector SVG:

| Figure | Requested question |
| --- | --- |
| 08_success_failure | Passed and did-not-pass percentages side by side, each model; adds failures to the existing correctness view |
| 09_input_by_prompt | Input means and registered 95% bootstrap intervals by prompt/model |
| 10_input_energy | Mean input tokens versus mean net energy, labelled arms |
| 11_input_relationships | Mean input versus success rate and mean output, separate models |
| 12_output_per_correct | All generated output tokens per successful solution, including failure cost |
| 13_output_mean_energy | Seven arm means: output versus mean net energy; distinct from existing 280-request scatter |
| 14_within_families | P0/P1/P5; P3_1/P3_3; P2/P4, by output, energy, success |
| 15_representative_tradeoffs | P1/P3_3/P2, by output/attempt, energy/attempt, energy/correct, output/correct |

Aggregate scatter points represent seven arm means, not individual task data.
No fitted line or independent-sample claim. Focused charts are point estimates;
use the original summary intervals, matched tasks and registered sensitivity.
No input/output phase-energy charts: they are unmeasurable at this resolution.

## 8. Candidate metric leaders: OWNER APPROVAL REQUIRED

These are sample extrema, not accepted recommendations or universal winners.
Family names describe prompt demands, not a general property of every prompt
in that family. Equal-task stage-1 point estimates only:

| Metric | 0.5B candidate | 1.5B candidate |
| --- | --- | --- |
| Highest test success | P0/P1 tie, 24/40 (60%) | P3_1, 30/40 (75%) |
| Lowest mean input | P0, 162.05 tokens | P0, 162.05 tokens |
| Lowest mean output | P3_3, 194.225 tokens | P1, 71.10 tokens |
| Lowest mean net energy | P3_3, 25.18 mWh | P1, 23.59 mWh |
| Lowest mean gross energy | P3_3, 48.68 mWh | P1, 43.59 mWh |
| Lowest net energy per correct | P1, 44.34 mWh | P1, 32.53 mWh |
| Lowest gross energy per correct | P1, 82.91 mWh | P1, 60.13 mWh |
| Lowest output tokens per correct | P1, 379.17 | P1, 98.07 |

**Sensitivity qualification:** removing 70 low-resolution windows changes the
task mix. For 1.5B P5's filtered net mean is 30.02 mWh (n=29), slightly below
P1's 30.52 (n=24), reversing their all-row mean ordering. Do not claim every
energy ranking is robust; these filtered means are not a paired comparison on
the same retained tasks. Accuracy always retains all 40 original outcomes.

**Proposed synthesis, NOT APPROVED:** Short code-only instructions appear most
efficient per verified solution in this sample. Examples offer model-dependent
trade-offs, with one example giving the largest 1.5B pass count and three giving
the lowest 0.5B per-attempt cost but lowest pass count. Requests for explanation
are costly without a consistent correctness benefit here. Broader causal claims
or prescriptions for all LLMs are unsupported.

## 9. Proposed future roadmap, for approval

1. Finalize source audit, backups, uncertainty displays and owner-reviewed wording.
2. Inspect saved examples of changed outcomes and truncations; no repairs/retries.
3. In a separately registered follow-up, stabilize idle/background conditions,
   measure thermal/frequency conditions and validate with a wall-plug meter.
4. Replicate on more tasks, larger models and GPU hardware with suitable power
   measurements. Do not infer GPU/whole-system savings from this CPU-package study.
5. A token-controlled or prompt-cache/recall experiment would be a NEW design:
   match actual lengths or explicitly model them, register settings and contrasts
   first. Current independent requests do not test conversational memory.

## Approval checklist

- Are the three explanatory family labels acceptable?
- Are the distinctions between all-row leaders, uncertainty and filtered results clear?
- Approve or revise the candidate synthesis and future roadmap above before they
  are inserted into a professor-facing conclusion. Until then, status remains draft.

## Assumptions

Raw source remains unchanged. The completed 560/280 split and saved Boolean
outcomes are authoritative. All costs include failures; missing costs are not
imputed. No new inference, new statistical significance tests, phase-energy
claims, post-outcome task substitutions or revised hypotheses. Full methods are
in P4_SETUP.md. The owner reviews interpretation; final report wording is not
accepted merely because this draft has been generated.
