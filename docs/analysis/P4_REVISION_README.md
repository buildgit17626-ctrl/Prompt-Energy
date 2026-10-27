# Revised professor discussion packet

The editable paper is P4_MANUSCRIPT.md; its checked PDF is
output/pdf/P4_revised_manuscript.pdf. The historical P4_baseline_brief.pdf path
now receives the same revised paper to prevent sharing the superseded headline.
Earlier comparison graphics remain supplementary, not the revised main narrative.

## Current packet and coverage

The PDF contains a continuously paginated A4 paper plus one A1 landscape comparison sheet. Main body,
tables, captions and references use embedded Times New Roman at 14 pt; headings
are larger, and page footers smaller. Continuous flow replaces artificial section
page breaks. The final A1 page supports digital zoom and large-format printing.
The owner's removed author-name line stays removed. An opening rationale before
the abstract explains the practical motivation and states the study's small scope.

- Figures 1-2: task-paired contrasts and energy-per-correct ratio intervals.
- Figure 3: all-row machine failures and selected source-review mechanisms.
- Figure 4: failed-attempt energy shares and energy/token complement.
- Figure 5: registered start versus post-hoc end/midpoint baseline scenarios.
- Section 9.1: the three categories and P1/P3_3/P2 interpretation.
- Final sheet S1-S2: passed/failed bars for each model.
- S3-S5: input by prompt and separate output-by-prompt model views.
- S6-S11: input versus energy, success and output tokens for each model.
- S12-S15: output versus mean net energy; gross/net energy versus prompt.
- S16-S17: output tokens per correct solution for each model.
- S18-S26: P0/P1/P5, P3_1/P3_3 and P2/P4 on output/energy/success.
- S27-S30: P1/P3_3/P2 on output/energy and both per-correct ratios.
- Section 10: three questions for professors; docs/outreach/PROFESSOR_EMAIL.md
  supplies the local email draft. No email was sent.

The charts retain separate arms, never pool category averages. All use stage 1.
Source review annotations are AI-assisted and have no independent second annotator.

All new comparisons were chosen after collection and are post hoc. The five
contrasts must not be described as pre-registered. Original H1-H5 remain unchanged.

## Rebuild and inspect

Run `.venv313/Scripts/python.exe -m analysis.review_revision` from the repository.
It reads original P4/pilot data, validates the schedule and source hashes, and writes
CSV/PNG/SVG evidence under results/p4-revision. No model calls or candidate execution.
Then run `.venv313/Scripts/python.exe -m analysis.professor_figures` to
validate the manuscript table/instructions and build the 30-panel sheet.
Use the separate bundled Python with ReportLab and pypdf to run
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
- The paper is prepared for research discussion; its limitations and AI-assisted
  annotation provenance remain explicit. Numerical auditing is not independent
  expert validation of the scientific conclusions.
