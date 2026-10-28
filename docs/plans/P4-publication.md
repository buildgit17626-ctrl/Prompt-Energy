# P4 publication follow-up (2026-10-28)

Owner authorizes pushing necessary study material and making the existing GitHub
repository public. No new generation, rescoring or hypothesis change is involved.

Files: update README and SPEC publication status; add a public artifacts bundle,
its provenance/checksums, and an offline export script with tests. Include the
full report, two-page summary, results for all 840 requests, saved responses,
supporting tables/figures and pilot noise evidence. Keep the licensed task archive.

Design: create separate exports from unchanged local journals. Redact Windows
user-directory paths in metadata, retaining source-file hashes and exact saved
HTTP response bodies. Publish a reduced CPU-package-only sensor view rather than
unrelated machine telemetry. Exported journals are for inspection and analysis,
not resumable inference. Exclude environments, binaries, credentials, backups,
outreach packets and temporary rendering images. Audit tracked history for
credential patterns before changing visibility. Verify tests, Ruff, counts,
checksums, push and final public visibility.

Risks: public copies can persist; generated code is untrusted; CPU estimates and
baseline drift must remain explicit; redacted journals differ from local originals
and must never be presented as byte-identical. No new licence is assigned to the
owner's original material without a choice from the owner. Existing third-party
notices remain applicable. No model weights or proprietary HWiNFO binary shipped.

Open questions: none blocking authorized publication. Assumptions: publication
includes saved model text and benchmark material under the retained MIT notice;
personal local directory names are unnecessary for evaluating the findings.
