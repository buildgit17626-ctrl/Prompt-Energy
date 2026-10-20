"""P4 total/post-load measurements and block flags; no phase energy or CodeCarbon."""

import csv
import json
from datetime import datetime
from pathlib import Path

from experiments.config import ENERGY, P4
from prompt_energy.energy import integrate
from prompt_energy.records import FIELDS, read_jsonl, result_index

FULL_FIELDS = [f for f in FIELDS if f not in {"codecarbon", "codecarbon_wh", "co2e_kg"}] + [
    "stage",
    "block_id",
    "record_kind",
    "include_in_main_analysis",
    "energy_tool",
    "energy_mode",
    "primary_window",
    "cpu_pkg_total_raw_wh",
    "cpu_pkg_total_wh",
    "cpu_pkg_post_load_raw_wh",
    "energy_flags",
    "load_seconds",
    "wall_minus_api_seconds",
    "end_idle_baseline_w",
    "baseline_drift_w",
    "block_status",
]


def full_energy(samples: list, raw: dict, response: dict | None, idle_w: float) -> dict:
    """Integrate only total and post-load windows, retaining boundary uncertainty."""
    start = datetime.fromisoformat(raw["started_at"]).timestamp()
    end = datetime.fromisoformat(raw["ended_at"]).timestamp()
    flags = []
    result = {
        "windows": {"total": integrate(samples, start, end, idle_w)},
        "flags": flags,
        "idle_baseline_w": idle_w,
        "load_seconds": None,
        "wall_minus_api_seconds": None,
    }
    if abs(end - start - raw["wall_seconds"]) > max(
        ENERGY["phase_tolerance_seconds"],
        ENERGY["phase_tolerance_fraction"] * raw["wall_seconds"],
    ):
        flags.append("clock_discrepancy")
    if response is None or any(
        type(response.get(k)) is not int or response[k] < 0
        for k in ("load_duration", "total_duration")
    ):
        flags.append("invalid_api_durations")
        return result
    load = response["load_duration"] / 1e9
    result["load_seconds"] = load
    result["wall_minus_api_seconds"] = raw["wall_seconds"] - response["total_duration"] / 1e9
    if start + load > end:
        flags.append("post_load:outside_request")
    else:
        result["windows"]["post_load"] = integrate(samples, start + load, end, idle_w)
    if response.get("prompt_eval_cached_count", 0) != 0:
        flags.append("cached_prompt_tokens")
    return result


def block_index(root: Path) -> dict:
    """Reject duplicate events; absence of an end event remains an explicit missing value."""
    blocks = {}
    for row in read_jsonl(root / "blocks.jsonl"):
        events = blocks.setdefault(row["block_id"], {})
        if row["event"] in events or row["event"] not in {"start", "end"}:
            raise ValueError("Duplicate/invalid block event")
        events[row["event"]] = row
    return blocks


def measurement_index(root: Path) -> dict:
    indexed = {}
    for row in read_jsonl(root / "measurements.jsonl"):
        if row["run_id"] in indexed:
            raise ValueError("Duplicate full-run measurement")
        indexed[row["run_id"]] = row
    return indexed


def drift(start_w: float, end_w: float | None) -> tuple[float | None, list[str]]:
    """Start-baseline correction is fixed; drift flags never alter past net estimates."""
    if end_w is None:
        return None, ["end_baseline_missing"]
    delta = end_w - start_w
    flags = (
        ["baseline_drift"]
        if abs(delta) > max(P4["drift_absolute_w"], P4["drift_fraction"] * start_w)
        else []
    )
    return delta, flags


def full_rows(root: Path) -> list[dict]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("milestone") != "P4 full":
        raise ValueError("Only P4 data allowed; smoke/pilot excluded")
    jobs = {j["run_id"]: j for j in manifest["schedule"]}
    measurements, blocks = measurement_index(root), block_index(root)
    rows = []
    for key, answer in result_index(root).items():
        job = jobs[key]
        measure = measurements.get(key, {})
        energy = measure.get("energy", {})
        windows = energy.get("windows", {})
        block_id = answer["session"]
        block = blocks.get(block_id, {})
        start_w = block.get("start", {}).get("baseline", {}).get("watts")
        ending = block.get("end", {})
        end_w = (ending.get("baseline") or {}).get("watts")
        delta, flags = (
            drift(start_w, end_w) if start_w is not None else (None, ["start_baseline_missing"])
        )
        flags += energy.get("flags", []) + ending.get("flags", [])
        if not measure:
            flags.append("measurement_missing")
        for name, window in windows.items():
            flags.extend(f"{name}:{f}" for f in window["flags"])
        row = {f: answer["row"].get(f) for f in FULL_FIELDS}
        row.update(
            {
                "stage": job["stage"],
                "block_id": block_id,
                "record_kind": "full",
                "include_in_main_analysis": job["stage"] == 1,
                "energy_tool": "HWiNFO",
                "energy_mode": "CPU Package Power; trapezoidal; block-start idle-adjusted",
                "primary_window": "post_load",
                "cpu_pkg_energy_wh": windows.get("post_load", {}).get("adjusted_wh"),
                "cpu_pkg_post_load_raw_wh": windows.get("post_load", {}).get("raw_wh"),
                "cpu_pkg_total_wh": windows.get("total", {}).get("adjusted_wh"),
                "cpu_pkg_total_raw_wh": windows.get("total", {}).get("raw_wh"),
                "idle_baseline_w": start_w,
                "end_idle_baseline_w": end_w,
                "baseline_drift_w": delta,
                "energy_flags": ";".join(sorted(set(flags))),
                "load_seconds": energy.get("load_seconds"),
                "wall_minus_api_seconds": energy.get("wall_minus_api_seconds"),
                "block_status": ending.get("status", "end_unrecorded"),
            }
        )
        rows.append(row)
    return rows


def export_full(root: Path) -> int:
    """Only this derived view is replaceable; journal evidence is immutable."""
    rows = full_rows(root)
    temporary = root / "full.csv.tmp"
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FULL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(root / "full.csv")
    return len(rows)
