"""P3-only derived reports; original answer and measurement journals stay immutable."""

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from experiments.config import CODECARBON, ENERGY
from prompt_energy.records import FIELDS, read_jsonl, result_index

EXTRA_FIELDS = [
    "record_kind",
    "include_in_main_analysis",
    "energy_tool",
    "energy_mode",
    "primary_window",
    "cpu_pkg_total_raw_wh",
    "cpu_pkg_total_wh",
    "cpu_pkg_post_load_raw_wh",
    "cpu_pkg_prompt_eval_wh",
    "cpu_pkg_decode_wh",
    "energy_flags",
    "load_seconds",
    "phase_residual_seconds",
    "wall_minus_api_seconds",
    "baseline_id",
    "codecarbon_tool_mode",
    "codecarbon_raw_wh",
    "codecarbon_idle_w",
    "codecarbon_seconds",
]


def measurement_index(root: Path) -> dict:
    records = {}
    for row in read_jsonl(root / "measurements.jsonl"):
        if row["run_id"] in records:
            raise ValueError("Duplicate measurement ID")
        records[row["run_id"]] = row
    return records


def energy_rows(root: Path) -> list[dict]:
    """Keep every outcome and flag missing energy; explicitly reject smoke data."""
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("milestone") != "P3 pilot":
        raise ValueError("Only P3 pilot batches are eligible; smoke rows are excluded")
    measures = measurement_index(root)
    rows = []
    for run_id, result in result_index(root).items():
        measure = measures.get(run_id, {})
        energy = measure.get("energy", {})
        windows = energy.get("windows", {})
        carbon = measure.get("carbon", {})
        flags = list(energy.get("flags", [])) + list(carbon.get("flags", []))
        if not measure:
            flags.append("measurement_missing")
        for name, window in windows.items():
            flags.extend(f"{name}:{flag}" for flag in window["flags"])
        row = {**result["row"], **dict.fromkeys(EXTRA_FIELDS, None)}
        row.update(
            {
                "record_kind": "pilot",
                "include_in_main_analysis": False,
                "energy_tool": ENERGY["tool"],
                "energy_mode": ENERGY["mode"],
                "primary_window": "post_load",
                "energy_flags": ";".join(sorted(set(flags))),
                "cpu_pkg_energy_wh": windows.get("post_load", {}).get("adjusted_wh"),
                "cpu_pkg_total_raw_wh": windows.get("total", {}).get("raw_wh"),
                "cpu_pkg_total_wh": windows.get("total", {}).get("adjusted_wh"),
                "cpu_pkg_post_load_raw_wh": windows.get("post_load", {}).get("raw_wh"),
                "cpu_pkg_prompt_eval_wh": windows.get("prompt_eval", {}).get("adjusted_wh"),
                "cpu_pkg_decode_wh": windows.get("decode", {}).get("adjusted_wh"),
                "idle_baseline_w": energy.get("idle_baseline_w"),
                "load_seconds": energy.get("load_seconds"),
                "phase_residual_seconds": energy.get("phase_residual_seconds"),
                "wall_minus_api_seconds": energy.get("wall_minus_api_seconds"),
                "baseline_id": measure.get("baseline_id"),
                "codecarbon_wh": carbon.get("adjusted_wh"),
                "co2e_kg": carbon.get("co2e_kg"),
                "codecarbon_raw_wh": carbon.get("raw_wh"),
                "codecarbon_idle_w": carbon.get("idle_w"),
                "codecarbon_seconds": carbon.get("seconds"),
                "codecarbon_tool_mode": CODECARBON["mode"],
            }
        )
        rows.append(row)
    return rows


def spread(values: list[float]) -> dict:
    """Sample dispersion for diagnostics; two repeats do not justify strong inference."""
    if not values:
        return {"n": 0, "mean": None, "sd": None, "min": None, "max": None}
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "sd": statistics.stdev(values) if len(values) > 1 else None,
        "min": min(values),
        "max": max(values),
    }


def summarize(rows: list[dict]) -> dict:
    loads, repeats = defaultdict(list), defaultdict(list)
    for row in rows:
        loads[(row["model"], row["prompt_id"])].append(row)
        repeats[(row["model"], row["prompt_id"], row["task_id"])].append(row)
    load_rows = []
    for (model, prompt), group in sorted(loads.items()):
        values = [r["load_seconds"] for r in group if r["load_seconds"] is not None]
        load_rows.append(
            {
                "model": model,
                "prompt_id": prompt,
                "rows": len(group),
                "missing": len(group) - len(values),
                **spread(values),
            }
        )
    noise = []
    for (model, prompt, task), group in sorted(repeats.items()):
        values = [r["cpu_pkg_energy_wh"] for r in group if r["cpu_pkg_energy_wh"] is not None]
        noise.append(
            {
                "model": model,
                "prompt_id": prompt,
                "task_id": task,
                "tool": ENERGY["tool"],
                "mode": ENERGY["mode"],
                "rows": len(group),
                "missing": len(group) - len(values),
                "flagged": sum(bool(r["energy_flags"]) for r in group),
                "complete_pair": len(group) == 2 and len(values) == 2,
                "absolute_repeat_difference_wh": abs(values[1] - values[0])
                if len(values) == 2
                else None,
                **spread(values),
            }
        )
    return {
        "pilot_rows": len(rows),
        "load_by_model_prompt_seconds": load_rows,
        "repeat_noise_primary_post_load_wh": noise,
        "full_run_1680_request_plus_gap_seconds_proxy": (
            1680 * statistics.mean(r["wall_seconds"] + ENERGY["gap_seconds"] for r in rows)
            + ENERGY["baseline_seconds"]
            if rows
            else None
        ),
        "runtime_estimate_limit": "Four-arm pilot proxy excludes warm-up, testing, sensor waits "
        "and control overhead; unpiloted few-shot/long arms may differ. Not a promised runtime.",
    }


def export_energy(root: Path) -> dict:
    """Replace only derived reports, never raw/answer/measurement journals."""
    rows = energy_rows(root)
    path = root / "energy.csv.tmp"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS + EXTRA_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    path.replace(root / "energy.csv")
    report = summarize(rows)
    temporary = root / "energy-summary.json.tmp"
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(root / "energy-summary.json")
    return report
