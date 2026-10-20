# P3 follow-up plan, 2026-10-20

Scope: owner-requested diagnostic plot/noise inspection, prospective measurement
amendment and OneDrive backup. No full-run execution or new inference.

Files: experiments/config.py records future measurement/analysis policy while
retaining historical P3 settings; docs/SPEC.md records the amendment and its
pilot basis. analysis/pilot_diagnostics.py reads immutable pilot CSV, writes
separate JSON summaries and PNG/PDF plots. Tests cover statistical helpers.
docs/P3_DIAGNOSTICS.md reports results/limitations and baseline recheck waiver.

Design: per-model scatterplots of post-load net and gross CPU package energy
versus output tokens, labelled pilot/diagnostic, tool and mode. Preserve all
model failures. Report available and missing counts and descriptive OLS R2,
not significance or causal confirmation. Compare absolute repeat differences
within task/model/prompt with task-matched mean arm contrasts. Two repeats mix
sampling/thermal/background variation and nondeterministic output, not pure
instrument noise. Include net-energy sensitivity without primary low-resolution
windows; never filter on irrelevant prompt-phase flags.

Future full run: HWiNFO only, total and post-load gross/net energy; no phase
energy split or CodeCarbon tracking. Input/output token counts remain predictors.
Pilot records, thresholds and raw data unchanged. Keep legacy CodeCarbon installed
for pilot reproduction; no P4 runner is implemented in this follow-up.

Backup: copy the entire completed pilot folder into the owner's OneDrive
Experiments directory, verify SHA-256 per file and retain a receipt. A local
OneDrive copy is not proof that cloud upload has completed.

Baseline: owner explicitly skipped the proposed two-minute recheck. The 6.5 W
comparison has no supplied source; retain measured 15.4201366935 W and report
both gross/net values. No claim that Best performance explains the difference.

Assumptions: read-only original pilot; no new generations; post-load boundary
still approximate; sensitivity excludes primary low-resolution rows only from
energy statistics, never hides missing/failure outcomes. Owner writes final
research interpretation. Full run remains unstarted.
