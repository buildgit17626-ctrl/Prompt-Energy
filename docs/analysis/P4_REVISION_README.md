# Revised professor discussion packet

The editable paper is P4_MANUSCRIPT.md; its checked PDF is
output/pdf/P4_revised_manuscript.pdf. The historical P4_baseline_brief.pdf path
now receives the same revised paper to prevent sharing the superseded headline.
Earlier comparison graphics remain supplementary, not the revised main narrative.

## Review map

1. Headline/lead: P1-P0, pages 1 and 4. P3-P0 is a composite comparison because
   actual P3 wording adds following the example(s); the instruction is not identical.
2. Cost-per-correct intervals: Figure 2, page 5; ratio_intervals.csv has all endpoints.
3. Paired contrasts: Figure 1/page 4; paired_contrasts.csv includes discordances.
4. Failure taxonomy: page 6; P4_FAILURE_REVIEW.csv contains 64 traceable annotations.
   These are AI-assisted, not independently human-adjudicated. Owner review pending.
5. Failed-attempt energy share: page 7; gross and net denominators both included.
6. Computation explanation: page 9; token-generation steps, no extra-networks theory.
7. Resolution selection bias and energy/token complement: page 7.
8. Pilot repeat evidence: page 8; 159/160 pairs, separately labelled and not pooled.
9. Baseline scenarios: page 8; saved window durations, registered/start plus post-hoc
   midpoint/end assumptions. No raw energy or baseline was replaced.
10. Three professor questions: page 9. Final author conclusion review: page 10.

All new comparisons were chosen after collection and are post hoc. The five
contrasts must not be described as pre-registered. Original H1-H5 remain unchanged.

## Rebuild and inspect

Run `.venv313/Scripts/python.exe -m analysis.review_revision` from the repository.
It reads original P4/pilot data, validates the schedule and source hashes, and writes
CSV/PNG/SVG evidence under results/p4-revision. No model calls or candidate execution.
Use the separate bundled Python with ReportLab to run
`-m analysis.build_manuscript` (or `-m analysis.build_brief` for the historical path).
The PDF builder reads the owner's editable Markdown and the generated figures;
it does not regenerate or overwrite the author's prose. Tables in the manuscript
are reviewed snapshots; changing the analysis requires reviewing those tables too.

For a failure: `.venv313/Scripts/python.exe -m experiments.show_run full-0171
--output results/p4-full` (one command line). This prints saved evidence without
running or repairing the candidate. Compare the raw response, reconstructed code,
task requirements and saved test outcome. No extraction failures were identified
in the selected sample; do not extrapolate zero to every generation.

## Assumptions and limits

- Bootstrap units are sampled tasks; intervals describe task variability at fixed
  observed settings and do not include systematic drift or all generation noise.
- Ratios use attempted energy including failures, not only successful requests.
- Missing pilot/stage-2 energies remain missing; no noise imputation or pooling.
- The 64 failures were deliberately sampled, so category fractions are not unbiased
  prevalence estimates. Truncation takes precedence even with a complete function.
- End/midpoint baselines are constant alternatives, not a fitted drift correction.
- Energy/token includes prompt and overhead cost; it cannot isolate decode energy.
- The PDF remains a draft for owner interpretation and annotation approval.
