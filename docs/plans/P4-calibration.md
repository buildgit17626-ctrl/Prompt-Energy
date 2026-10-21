# P4 calibration follow-up (2026-10-21)

Before any main-run generation, implement the owner-specified separate 40-task
calibration: qwen2.5-coder:1.5b, P0, one repeat, existing decoding/extraction/sandbox,
keep_alive=0, no energy. Numeric task order is fixed; no retries of failed answers.
A warm-up is saved but excluded. Preserve raw requests, responses and outcomes;
resume saved responses and reject uncertain intents or changed registration.

Files: config and SPEC register rules; src/prompt_energy/calibration.py and
experiments/calibrate.py provide run/export; tests/test_calibration.py checks
length counting, median ties, schedule, labels, gate and recovery. Compute length
from canonical_solution only: physical lines with non-whitespace content whose
stripped form does not start with #; inline comments do not remove a code line.
Docstring/string lines count, as the rule excludes only blank/comment lines.
Freeze explicit reference-length labels and median in config before generation.
Export calibration labels only after all 40 outcomes are available; failed means
any nonpassing outcome, with failure reasons retained. Infrastructure/transport
failures stop collection for investigation and prevent automatic label freezing.
Do not reuse smoke, pilot or main outcomes. Commit labels and provenance before P4.

Risks: calibration is a single noisy observation, not intrinsic difficulty;
separate generations do not prove statistical independence under fixed decoding.
Group size is unknown until calibration; pilot 65% pooled accuracy does not
predict 1.5b/P0 accuracy. P0 remains excluded from group comparisons.

Also: inspect existing pilot noise/backup evidence, verify the stage-2 seed,
run pytest/Ruff/prepare, and copy all results to a fresh OneDrive backup with
checksums. Cloud upload requires separate verification. No main-run permission.
The requested idle recheck waits for owner readiness/new CSV and is not performed
while tests or inference are active. The earlier 6.5 W source is still unknown.


## Execution authorization update (2026-10-21)

Owner explicitly authorized implementing and running calibration only, then
freezing both maps with timestamp and rules in SPEC. Add `run_p4 calibrate`
as the public entry point, defaulting to a separate calibration directory;
keep the existing calibration command compatible. Test dispatch and confirm
no HWiNFO requirement or scored-block path. Commit before generation, execute
40 requests once, verify complete no-op resume before changing config, then
freeze labels and source checksums. No idle check or scored P4 block this step.
The earlier 6.5 W observation was clarified as Energy saver, not comparable idle.
