# P3 pilot audit, 2026-10-20

Owner approval was received before the live pilot. All 320 requests completed
and the runner exited with code 0. These are diagnostic pilot data, excluded
from main hypothesis analysis. No P4 full run was started.

## Evidence and correctness

- 320 unique scheduled IDs, 320 raw scored responses and 320 measurement records.
- 206 passed; 98 test_failed; 10 truncated; 4 timeout; 2 no_code.
- All scored native cached-token counts were zero.
- Completed resume returned completed=320, new_requests=0. JSON/JSONL hashes
  were identical before and after resume.
- All 320 saved sensor byte-prefix hashes were verified.
- Accepted P2 smoke evidence remains unchanged.

No failed answer was repaired, retried or removed. Two startup attempts failed
before scoring: integer-vs-float CodeCarbon pue compatibility, then a stale
tracker lock. The multiplier remains 1.0 and research settings are unchanged.
The fix was tested and committed before scoring; all startup journals remain.

## Measurement quality

HWiNFO64 8.54-6090, approximately 501 ms observed cadence, 60-second idle baseline
15.4201366935 W, plugged in with Best performance. The scored span was
00:14:15–01:59:35 IST on 2026-10-20 (approximately 105 minutes).

Primary adjusted post-load CPU package energy exists for 319/320 rows.
`pilot-0036` crossed a sensor gap >1 s: total, post-load and decode estimates
are missing and flagged. Its answer and remaining measurements remain saved.
There are 159 complete energy pairs out of 160 paired task/model/prompt groups.

Low-resolution flags: 320 prompt-eval windows, 46 decode windows, 34 primary
post-load windows and 7 total windows. No phase-sum mismatch appeared. Absence
of a mismatch does not establish accurate phase boundaries. In particular,
these data cannot support precise attribution of energy to input processing.

CodeCarbon recorded constant CPU power 42.5 W and RAM power 10 W for every
scored request. Its baseline-adjusted values are near zero, with five negative
estimates retained and flagged. This secondary estimate is not sensitive enough
to corroborate HWiNFO differences. CPU package energy remains an estimate and
excludes other laptop components. No retrospective filtering was introduced.

Load-duration summaries by model/prompt and paired-repeat sample dispersion are
in energy-summary.json. The four-arm full-run proxy is approximately 8.42 hours
for request time plus gaps and one baseline. It excludes testing, controls,
warm-ups, sensor waits and differences in the three unpiloted arms; actual
full-run duration can be longer. The owner decides subsequent research design.

## Files and backup

- results/p3-pilot-2026-10-20/: raw responses, intents, sessions, baseline,
  measurements, exact sensor mirror, derived energy.csv and energy-summary.json.
- results/p3-pilot/: preserved first failed startup.
- results/samples/P3-pilot-audit.json and P3-backup-receipt.json: small audit
  receipts committed without the raw model outputs.
- Backup: C:\Users\Dhruv Brahmbhatt\prompt-energy-backups\p3-pilot-2026-10-20.
  All 16 copied files passed SHA-256 comparison. This is a second folder on the
  same physical drive, not an independent-device backup.

Final validation after collection: Python 3.13.7, 304 tests passed in 41.15 s;
Ruff check passed and all 32 Python files passed formatting. Assumptions and
five learning questions are in docs/learning/P3.md. Owner review of measurement
quality is still important before authorizing P4.
