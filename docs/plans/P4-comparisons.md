# P4 additional comparisons (2026-10-27)

Scope: owner-requested supplementary scientific figures and an expectations versus
evidence review. No new generation, protocol change, or P5 execution.

Files: analysis/comparisons.py, tests/test_comparisons.py,
docs/analysis/P4_EXPECTATIONS_OBSERVATIONS.md; derived PNG/SVG, CSV, provenance and
a portable HTML review in results/p4-comparisons. Reuse existing brief figures for
energy per correct, output by prompt and gross/net energy by prompt. Add only
missing or specifically requested focused views. Keep the old PDF unchanged.

Design: stage 1 only for comparisons, all 40 tasks per arm. Recalculate summaries
with pandas from full.csv and check against registered summaries. Native token
counts; energy in mWh; ratios include failures and require complete measurements.
Use existing bootstrap intervals where applicable. Aggregate associations have
seven prompt means per model, not seven independent experiments or causal effects.
Family labels are explanatory, post-collection labels; show each arm separately:
task-completion instructions (P0/P1/P5), example-guided (P3_1/P3_3), and
explanation-requesting (P2/P4). They do not establish internal reasoning.

Risks: all stage-1 energy is baseline-drift flagged; 70 low-resolution windows;
registered filtered view changes task mix. Stage 2 remains repeat diagnostics.
Do not call descriptive contradictions proof against a statistical hypothesis.
Keep original H1-H5 and label owner expectations as later working expectations.
Correct mechanisms: smaller models do not invoke extra networks; 768 is a cap.

Validation: tests for aggregation/ratio denominators/missingness and stage
separation, compare tables with registered outputs, inspect all new charts,
pytest and Ruff. Check source hash before/after. No heavy dependencies.

Open question: owner approval of interpretation is required. Build a concrete
review draft and candidate metric leaders first, then ask approval; do not mark
any interpretation accepted or alter the original brief's conclusions.
