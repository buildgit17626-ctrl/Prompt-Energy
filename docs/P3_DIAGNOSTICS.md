# Pilot diagnostics and prospective decisions, 2026-10-20

Diagnostic only; pilot data remain excluded from hypothesis tests. HWiNFO CPU
Package Power, trapezoidal integration, approximate post-load windows. Failed
answers are included; missing energy is never imputed.

## Energy versus output tokens

The scatterplots show a strong near-linear association separately by model.
Descriptive least-squares R-squared, intercept included:

| Model | Available rows | Net R2 | Gross R2 | Net R2 excluding primary low resolution |
| --- | ---: | ---: | ---: | ---: |
| 0.5b | 160 | 0.961 | 0.971 | 0.944 (145 rows) |
| 1.5b | 159 | 0.986 | 0.989 | 0.981 (140 rows) |

These are in-sample descriptive fits, not causal estimates or confirmation of
H1. Repeat/task dependence, truncation at 768 tokens, limited prompt arms and
shared hardware remain limitations. Input tokens remain a predictor for the
future analysis; this plot alone does not separate their contribution.

## Repeat variability versus arm differences

Within the same task/model/prompt, median absolute difference between repeats
is 0.00299 Wh for 0.5b (80 complete pairs) and 0.00436 Wh for 1.5b (79 pairs).
90th percentiles are 0.00983 and 0.01718 Wh, respectively. This variation includes
changes in generated output, thermal state and background load as well as
measurement noise; it is not a pure sensor precision estimate.

For comparison, using task-matched arm means with both repeats present:

| Model | Median absolute P1-P2 task contrast | Median absolute P1-P4 task contrast | Median absolute P2-P4 task contrast |
| --- | ---: | ---: | ---: |
| 0.5b | 0.03589 Wh | 0.03043 Wh | 0.00699 Wh |
| 1.5b | 0.10999 Wh | 0.11439 Wh | 0.00970 Wh |

The large code-only versus verbose-arm differences exceed typical repeat
variation. P2 versus P4 is much less separated: its median contrast is below the
90th percentile of repeat variation for both models. Do not claim that every
prompt contrast is reliably measurable. Two repeats are insufficient for strong
inference; task-specific effects and generated lengths vary.

## Baseline and quality

The owner skipped the proposed new two-minute idle check. Retain the measured
15.4201366935 W pilot baseline and report gross alongside net energy. The cited
~6.5 W idle average has no supplied comparable record. Current screenshot:
10.864 W CPU Package Power, average 13.643 W, min 9.451 W, max 25.828 W.
Its averaging interval/activity is not a controlled baseline. No old result is
replaced, and the difference is not attributed to Best performance without data.

One primary estimate remains missing (pilot-0036, sensor gap); 34 short primary
windows are retained in the all-available view and excluded in sensitivity.
All-row correctness still uses 320 outcomes. All phase-energy interpretation
and CodeCarbon tracking are dropped prospectively, not removed from old logs.

## Reproduction and backup

Run `.\.venv313\Scripts\python.exe -m analysis.pilot_diagnostics`.
Outputs: results/p3-diagnostics/diagnostics.json and energy-vs-output.png/.pdf.
Original energy.csv SHA-256 is embedded in the diagnostic JSON and checked
unchanged. Figure caption labels tool, mode, baseline, counts and pilot status.

The full pilot folder (11 files) was copied to:
C:\Users\Dhruv Brahmbhatt\OneDrive\Documents\Experiments\Prompt-Energy-backups\p3-pilot-2026-10-20.
Every local copy passed SHA-256 verification. Cloud upload completion is not
verified; check OneDrive's sync status before treating it as off-device backup.
The receipt is results/samples/P3-onedrive-backup-receipt.json.

## Assumptions

No new model calls; original pilot untouched; diagnostic rather than confirmatory
interpretation; missing energy unavailable; phase boundaries approximate; no
replacement idle estimate; no claim that local OneDrive copying proves cloud
sync; no full-run authorization. The owner writes the final research analysis.

## Validation

Python 3.13.7: 307 tests passed in 49.09 s; Ruff check and format check passed
for all 34 Python files. Original 11 pilot files still match backup checksums.
Repeat-pair counts agree with the existing energy-summary.json.
