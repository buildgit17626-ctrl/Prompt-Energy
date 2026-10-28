# P4 report wording and two-page overview

Owner request, 2026-10-28: exact neutral title, natural abstract/conclusion,
report terminology, concrete honest findings, accurate AI disclosure focused on
experiment setup and automated Ollama runs, plus a two-page Times New Roman summary.

Files: docs/analysis/P4_MANUSCRIPT.md, docs/analysis/P4_SUMMARY.md,
analysis/build_manuscript.py (optional comparison appendix; source-driven title),
docs/analysis/P4_REVISION_README.md, SPEC presentation amendment, learning notes.
Outputs: full report at both existing PDF paths, new P4_two_page_summary.pdf,
refreshed review archives. All body text remains Times New Roman 14 pt with
consistent spacing. Summary uses two existing, data-backed chart designs:
pass rates and energy per correct solution with the retained bootstrap intervals.

No new inference, scoring, hypothesis or statistics. Preserve raw observations
and their hashes. Do not misrepresent AI involvement: describe setup and automated
Ollama execution, figures/report preparation and AI-assisted failure annotations;
do not claim that all work was independently performed by the owner.

Validation: exact title/terminology and disclosure checks; existing numerical
audit; exactly two summary pages; embedded Times New Roman; render and inspect
every page; Ruff and relevant existing tests. Preserve owner's removed author line.

Assumptions: the summary shortens H1-H5 without changing their meaning; point
estimates do not prove universal accuracy benefits or equivalence. Full report
retains methodology and limitations; neutral headline does not change the five
post-hoc paired contrasts. No publication or email sending is authorized.
