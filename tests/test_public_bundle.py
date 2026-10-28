"""Check that the committed public bundle is complete and internally consistent."""

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "artifacts"


def test_public_file_hashes_and_counts() -> None:
    manifest = json.loads((ROOT / "provenance.json").read_text(encoding="utf-8"))
    assert manifest["rows"] == 840
    assert manifest["stages"] == {"1": 560, "2": 280}
    for name, metadata in manifest["files"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == metadata["export_sha256"]
    full = manifest["files"]["results/p4-full/full.csv"]
    assert full["source_sha256"] == full["export_sha256"]


def test_every_public_scored_outcome_has_a_saved_response() -> None:
    batch = ROOT / "results/p4-full"
    with (batch / "full.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    ids = {row["run_id"] for row in rows}
    assert len(rows) == len(ids) == 840
    assert sum(row["stage"] == "1" for row in rows) == 560
    assert sum(row["stage"] == "2" for row in rows) == 280
    assert sum(row["stage"] == "1" and row["passed"] == "True" for row in rows) == 347
    assert sum(row["cpu_pkg_energy_wh"] == "" for row in rows) == 99
    raw = [json.loads(line) for line in (batch / "raw.jsonl").read_text().splitlines()]
    saved_ids = {item["request_id"] for item in raw}
    assert ids <= saved_ids
    outcomes = [json.loads(line) for line in (batch / "results.jsonl").read_text().splitlines()]
    assert {item["row"]["run_id"] for item in outcomes} == ids
