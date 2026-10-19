"""Durable append-only journals and derived CSV with the exact SPEC schema."""

import csv
import json
import msvcrt
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

FIELDS = (
    "run_id,timestamp,model,model_hash,prompt_id,task_id,difficulty_group,repeat,seed,"
    "input_tokens,output_tokens,wall_seconds,tokens_per_second,cpu_pkg_energy_wh,"
    "codecarbon_wh,idle_baseline_w,co2e_kg,passed,failure_type,raw_output_path,python,"
    "runtime_version,codecarbon,cpu_model,os,power_mode"
).split(",")
ENERGY_FIELDS = ("cpu_pkg_energy_wh", "codecarbon_wh", "idle_baseline_w", "co2e_kg")
FAILURES = {
    "",
    "no_code",
    "truncated",
    "policy_rejected",
    "syntax_error",
    "test_failed",
    "timeout",
    "memory_limit",
    "infrastructure_error",
    "api_error",
    "transport_error",
}


@contextmanager
def directory_lock(root: Path) -> Iterator[None]:
    """OS-released lock prevents two processes sending the same scheduled request."""
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".lock").open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError("Another runner owns this output directory") from exc
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def append_json(path: Path, record: dict) -> None:
    """Flush each complete record to disk before the next dependent action."""
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_jsonl(path: Path) -> list[dict]:
    """Fail closed on truncated or malformed records, retaining the original file."""
    if not path.exists():
        return []
    data = path.read_text(encoding="utf-8")
    if data and not data.endswith("\n"):
        raise ValueError(f"Truncated journal: {path}")
    rows = [json.loads(line) for line in data.splitlines()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"Non-object journal record: {path}")
    return rows


def write_once(path: Path, record: dict) -> None:
    """Exclusive creation makes registration and cache decisions immutable."""
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def validate_row(row: dict) -> None:
    """Reject schema drift, invented energy, and inconsistent pass/failure labels."""
    if set(row) != set(FIELDS):
        raise ValueError("Result columns differ from SPEC")
    if any(row[key] != "" for key in (*ENERGY_FIELDS, "difficulty_group")):
        raise ValueError("P2 must not contain energy or difficulty data")
    if type(row["passed"]) is not bool or row["failure_type"] not in FAILURES:
        raise ValueError("Invalid result outcome")
    if row["passed"] != (row["failure_type"] == ""):
        raise ValueError("Pass/failure mismatch")
    for key in ("input_tokens", "output_tokens"):
        if row[key] != "" and (type(row[key]) is not int or row[key] < 0):
            raise ValueError("Invalid token count")


def result_index(root: Path) -> dict[str, dict]:
    """Read validated results, rejecting duplicate run IDs rather than dropping rows."""
    indexed = {}
    for record in read_jsonl(root / "results.jsonl"):
        validate_row(record["row"])
        key = record["row"]["run_id"]
        if key in indexed:
            raise ValueError(f"Duplicate result: {key}")
        indexed[key] = record
    return indexed


def export_csv(root: Path) -> None:
    """CSV is a replaceable view; original JSONL records are never rewritten."""
    rows = result_index(root).values()
    temporary = root / "results.csv.tmp"
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(record["row"] for record in rows)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(root / "results.csv")
