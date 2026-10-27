# P4 professor-facing evidence packet

Owner request: combine their working expectations/observations with verified
results, correct mechanisms and produce formal graphs plus a shareable brief.
This is P4 presentation work, not new data collection or a new preregistration.

Files: analysis/presentation.py renders figures and numerical tables from the
existing P4 full.csv and registered summaries; analysis/build_brief.py builds
a four-page PDF using the bundled PDF runtime; tests/test_presentation.py checks
stage separation, source hashes and expected counts; docs/analysis contains the
combined expectation/observation record. Outputs: results/p4-presentation
(PNG/SVG, CSV, evidence JSON), output/pdf/P4_baseline_brief.pdf, and a ZIP packet.

Design: show pass counts with registered task-bootstrap intervals; output tokens;
gross and net post-load energy per attempt and per correct; per-request token/
energy associations without causal claims; frozen calibration/length groups
excluding P0; low-resolution sensitivity with counts; repeat differences with
available-pair counts. Preserve fixed prompt order; do not pick favorable arms.
Hypotheses H1-H5 remain exact. Owner expectations are paraphrased, attributed and
labelled exploratory unless dated prior evidence exists. Describe candidate
explanation as unverified; no extra networks, universal superiority or forced
768-token lengths. No new tests of significance or tuned exclusions.

Risks: all stage-1 energy is drift-flagged; 70 low-resolution stage-1 windows;
99 missing stage-2 energies and 64 complete energy pairs. Stage separation,
gross/net reporting and explicit denominators are mandatory. The filtered view
changes task mix and is not a paired alternative dataset. Baseline correction
is never replaced. Bootstrap intervals do not include hardware systematic error.
H5 has no measurable input-phase energy. Joint OLS does not isolate predictor
contributions. Distinguish data integrity, quality and inference.

Validation: compare all numbers to source CSVs; reject altered/missing stages;
assert raw/source byte hashes unchanged; test helper computations, run pytest
and Ruff; render PDF pages to PNG and inspect every page and figure for overlap.
PDF libraries are supplied by the separate bundled runtime, not added to the
pinned study environment. No model calls, API messages or remote publication.

Open questions: none blocking; this is a review draft, not evidence of owner
acceptance or a final scientific interpretation. Owner remains final author.
