# Public review bundle

Published at the owner's request on 2026-10-28. Start with
[the two-page summary](reports/P4_two_page_summary.pdf), then
[the full report](reports/P4_baseline_brief.pdf). These retain the limitations,
AI-assistance disclosure and distinction between exploratory and registered work.

## Contents

- `results/p4-full/full.csv`: all 840 scored requests, unchanged from the local
  numeric CSV. Stage 1 = 560 main requests; stage 2 = 280 noise-only repeats.
  `cpu_pkg_energy_wh` is net estimated post-load CPU package Wh;
  `cpu_pkg_post_load_raw_wh` is gross. Missing values are empty, never zero.
- `results/p4-full/raw.jsonl`: exact saved HTTP bodies in `body_base64`, alongside
  request settings/timings. Includes saved control/warm-up records; identify
  scored requests through `full.csv`, not by counting every raw line.
- Other `p4-full` journals retain outcome details, measurement windows, baselines,
  block events, model metadata and observed environment. No failures are removed.
- `results/p4-full/sensors/`: original Date, Time and CPU Package Power [W]
  readings extracted from the four sensor mirrors, UTF-8 CSV. Unrelated hardware
  telemetry is omitted. Timestamps retain the registered UTC+05:30 interpretation.
- `results/p4-analysis/`: registered analysis tables and grouping summaries.
- `results/p4-revision/`: explicitly post-hoc paired contrasts, ratio intervals,
  baseline alternatives, failure and noise diagnostics.
- `results/p4-presentation/`, `p4-comparisons/`, `p4-professor/`, `p4-summary/`:
  report figures, underlying tables and numerical checks.
- `results/p3-pilot-2026-10-20/`: pilot energy table/summary for supplementary
  noise diagnostics only, excluded from main hypothesis comparisons.
- `results/p4-calibration-2026-10-21/`: the separate 40-task calibration and
  frozen-label provenance; not scored main data.
- `results/p2-smoke/`: smoke, warm-up and determinism/cache evidence; excluded
  from the main analyses. Control records do not count as scored requests.
- `provenance.json`: original source and exported SHA-256 hashes for each file.

## Integrity and limitations

Exports are copies: local journals are not edited. JSON serialization changes
formatting and Windows user-directory paths become `<USER_HOME>`. Saved HTTP
response bodies remain byte-for-byte recoverable from base64. Numeric main CSV
is byte-identical. Sensor exports preserve the selected recorded fields, not
the complete original CSV bytes. Original sensor-prefix hashes refer to local
full telemetry and cannot be verified against reduced public sensor files.
The main-block sensor mirror ends with one incomplete power record; its timestamp
is retained with an empty power field, never filled in or treated as zero.
Historical analysis provenance likewise refers to original local files; the
public `provenance.json` distinguishes their hashes from exported-file hashes.

These redacted exports are for inspection/offline analysis, **not inference
resume**. To explore locally, copy `artifacts/results/` to a separate ignored
`results/` directory, or pass `--run artifacts/results/p4-full` to full_analysis.
Rebuilding documents requires the separate ReportLab/pypdf PDF tooling described
by their builders, as well as Windows Times New Roman. It does not require
regenerating answers. The study's pinned environment is for the experiment and
analysis; PDF authoring used a separate bundled runtime.

Generated code is untrusted text: do not run saved generations directly. Read
`docs/SAFETY.md` before using the restricted worker, which is not an OS security
boundary. HumanEval is redistributed with `data/HumanEval.LICENSE`; model weights
and proprietary HWiNFO software are not redistributed. Publication does not
assign a new licence to original code/report material.

## Regenerate the export from the owner's local archive

`python -m experiments.export_public` writes this bundle from the existing
ignored results and PDFs. It performs no inference and does not execute saved
code. A fresh clone already contains the export; it does not contain the complete
unredacted local archive required to recreate every original-byte hash.

Assumptions: private account paths and unrelated sensor telemetry are unnecessary
for public review. All 840 scored rows, original saved model responses, failures
and absent energy values are required and retained. Publishing these files does
not strengthen conclusions or remove the report's measurement caveats.
