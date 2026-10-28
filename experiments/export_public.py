"""Export existing evidence for public review, without running any model/code."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER_PATH = re.compile(r"[A-Za-z]:[/\\]Users[/\\][^/\\\r\n]+", re.IGNORECASE)


def redact(value: object) -> object:
    """Remove local account directories; preserve opaque saved HTTP bytes."""
    if isinstance(value, dict):
        return {k: v if k == "body_base64" else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return USER_PATH.sub("<USER_HOME>", value)
    return value


def export_file(source: Path, target: Path) -> dict[str, object]:
    """Copy a source, recording byte hashes and metadata-only redaction."""
    original = source.read_bytes()
    if source.suffix == ".json":
        content = (json.dumps(redact(json.loads(original)), indent=2) + "\n").encode()
    elif source.suffix == ".jsonl":
        content = b"".join(
            (json.dumps(redact(json.loads(line)), ensure_ascii=True) + "\n").encode()
            for line in original.splitlines() if line.strip()
        )
    elif source.suffix == ".csv":
        # Ordinary numeric CSVs remain byte-identical; review/provenance CSVs can
        # contain local source paths, which are unnecessary for public analysis.
        content = USER_PATH.sub("<USER_HOME>", original.decode("utf-8")).encode("utf-8")
    else:
        content = original
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return {
        "source": source.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(original).hexdigest(),
        "export_sha256": hashlib.sha256(content).hexdigest(),
        "changed": original != content,
    }


def main() -> None:
    """Write the reviewed public bundle from already collected local evidence."""
    destination = ROOT / "artifacts"
    provenance = {}
    journals = (
        "manifest.json", "requests.jsonl", "raw.jsonl", "results.jsonl",
        "measurements.jsonl", "sessions.jsonl", "blocks.jsonl", "full.csv",
    )
    for batch, names in (
        ("p4-full", journals),
        ("p3-pilot-2026-10-20", ("energy.csv", "energy-summary.json")),
        ("p4-calibration-2026-10-21", (
            "manifest.json", "raw.jsonl", "requests.jsonl", "results.jsonl",
            "results.csv", "sessions.jsonl", "grouping-export.json", "resume-audit.json",
        )),
        ("p2-smoke", (
            "manifest.json", "raw.jsonl", "requests.jsonl", "results.jsonl",
            "results.csv", "sessions.jsonl", "cache_policy.json",
        )),
    ):
        for name in names:
            source = ROOT / "results" / batch / name
            target = destination / "results" / batch / name
            provenance[target.relative_to(destination).as_posix()] = export_file(source, target)
    for folder in (
        "p4-analysis", "p4-presentation", "p4-comparisons", "p4-revision",
        "p4-professor", "p4-summary",
    ):
        for source in sorted((ROOT / "results" / folder).rglob("*")):
            if not source.is_file() or source.suffix not in {".csv", ".json", ".png", ".svg"}:
                continue
            # existing/ duplicates figures already included in p4-presentation.
            if "existing" in source.relative_to(ROOT / "results" / folder).parts:
                continue
            target = destination / source.relative_to(ROOT)
            provenance[target.relative_to(destination).as_posix()] = export_file(source, target)
    for name in ("P4_baseline_brief.pdf", "P4_two_page_summary.pdf"):
        source = ROOT / "output" / "pdf" / name
        target = destination / "reports" / name
        provenance[target.relative_to(destination).as_posix()] = export_file(source, target)
    # Publish the measured signal, rather than unrelated hardware telemetry.
    for source in sorted((ROOT / "results/p4-full/sensors").glob("*.csv")):
        target = destination / "results/p4-full/sensors" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        missing_power = 0
        with source.open(encoding="cp1252", newline="") as incoming:
            reader = csv.DictReader(incoming)
            fields = ["Date", "Time", "CPU Package Power [W]"]
            if not set(fields).issubset(reader.fieldnames or []):
                raise ValueError(f"Missing required sensor columns: {source.name}")
            with target.open("w", encoding="utf-8", newline="") as outgoing:
                writer = csv.DictWriter(outgoing, fieldnames=fields)
                writer.writeheader()
                for row in reader:
                    missing_power += row[fields[-1]] in (None, "")
                    writer.writerow({k: row[k] for k in fields})
        provenance[target.relative_to(destination).as_posix()] = {
            "source": source.relative_to(ROOT).as_posix(),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "export_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "changed": True,
            "transformation": "CPU package power and original date/time columns only; UTF-8",
            "missing_power_rows_retained_as_empty": missing_power,
        }
    rows = list(csv.DictReader((destination / "results/p4-full/full.csv").open(newline="")))
    counts = {stage: sum(r["stage"] == stage for r in rows) for stage in ("1", "2")}
    if len(rows) != 840 or counts != {"1": 560, "2": 280}:
        raise ValueError(f"Unexpected full-run counts: {counts}")
    (destination / "provenance.json").write_text(
        json.dumps({"rows": len(rows), "stages": counts, "files": provenance}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Exported {len(provenance)} evidence files; {len(rows)} scored rows ({counts}).")


if __name__ == "__main__":
    main()
