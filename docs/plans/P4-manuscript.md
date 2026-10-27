# P4 manuscript revision plan

Owner requested revisions after reviewing existing P4 results (2026-10-27).
No new inference, scoring, raw-data modification or experiment is authorized.

## Files and design
- analysis/review_revision.py: task-paired bootstrap contrasts, ratio bootstrap,
  failed-attempt energy share, alternate-baseline diagnostics, pilot repeat summaries.
- docs/analysis/P4_FAILURE_REVIEW.csv: traceable manual review of at least 30
  saved stage-1 failures, with evidence and uncertainty; distinct from machine labels.
- docs/analysis/P4_MANUSCRIPT.md: professor-facing editable paper draft and questions.
- analysis/build_manuscript.py and output/pdf/P4_revised_manuscript.pdf: checked PDF.
- tests/test_review_revision.py: paired alignment and ratio/denominator checks.
- docs/SPEC.md: dated post-hoc analysis amendment; original registration retained.

Task bootstrap: 2,000 draws, seed 1729, percentile 95% intervals. Pair by task
within model; recompute aggregate energy / successes on every bootstrap sample.
Report zero-success samples explicitly, never quietly drop them. Five contrasts
requested now are post hoc, not retrospectively pre-registered. No significance
claims or multiple-comparison-adjusted intervals. Gross/net remain distinct.

Failure review: deterministic sample stratified by model/arm, plus all stage-1
truncations and no-code cases, and all saved NameError/timeout cases. Inspect raw text, extracted source, task and saved
test outcome; never execute candidate code. Non-exclusive mechanisms may coexist;
primary category hierarchy is truncation, extraction, missing helper, wrong logic,
then uncertain/other. Counts describe this selected review sample, not prevalence.

## Risks and decisions
P3 changes instruction wording as well as demonstrations relative to P0; it is
not an isolated examples intervention. Low-resolution exclusion selects by duration.
Energy per token is a complementary ratio, not a correction for sensor bias.
Baseline endpoints do not establish the idle trajectory during requests. End and
midpoint baselines are alternative constant-baseline scenarios, explicitly post hoc.
Pilot repeats are supplementary only and include different conditions/CodeCarbon
overhead; they cannot replace missing P4 measurements. Final interpretation remains
subject to owner review. No open question blocks these requested descriptive edits.
