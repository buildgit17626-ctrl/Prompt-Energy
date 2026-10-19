"""Transparent trapezoidal CPU package estimates, never phase-energy fabrication."""

import bisect
import math
from datetime import datetime

from experiments.config import ENERGY
from prompt_energy.hwinfo import Sample


def integrate(samples: list[Sample], start: float, end: float, idle_w: float = 0) -> dict:
    """Interpolate boundaries only within coverage; retain negative corrected estimates."""
    result = {
        "start": start,
        "end": end,
        "seconds": end - start,
        "raw_wh": None,
        "adjusted_wh": None,
        "flags": [],
    }
    flags = result["flags"]
    if not all(math.isfinite(v) for v in (start, end, idle_w)) or end < start:
        flags.append("invalid_window")
        return result
    if end - start < ENERGY["low_resolution_seconds"]:
        flags.append("low_resolution")
    if len(samples) < 2 or start < samples[0].timestamp or end > samples[-1].timestamp:
        flags.append("missing_sensor_coverage")
        return result
    times = [s.timestamp for s in samples]
    if any(b <= a for a, b in zip(times, times[1:], strict=False)) or any(
        not math.isfinite(s.timestamp) or not math.isfinite(s.watts) or s.watts < 0 for s in samples
    ):
        raise ValueError("Invalid sensor series")
    left = max(0, bisect.bisect_right(times, start) - 1)
    right = min(len(samples) - 1, bisect.bisect_left(times, end))
    total_ws = 0.0
    for a, b in zip(samples[left : right + 1], samples[left + 1 : right + 1], strict=False):
        lo, hi = max(start, a.timestamp), min(end, b.timestamp)
        if hi <= lo:
            continue
        width = b.timestamp - a.timestamp
        if width > ENERGY["max_sample_gap_seconds"]:
            flags.append("sensor_gap")
            return result
        p_lo = a.watts + (b.watts - a.watts) * (lo - a.timestamp) / width
        p_hi = a.watts + (b.watts - a.watts) * (hi - a.timestamp) / width
        total_ws += (p_lo + p_hi) * 0.5 * (hi - lo)
    result["raw_wh"] = total_ws / 3600
    result["adjusted_wh"] = (total_ws - idle_w * (end - start)) / 3600
    if result["adjusted_wh"] < 0:
        flags.append("negative_adjusted_energy")
    return result


def idle_baseline(samples: list[Sample], start: float, end: float) -> dict:
    """Time-weighted baseline over the registered 60-second quiet window."""
    if not math.isclose(end - start, ENERGY["baseline_seconds"], abs_tol=0.01):
        raise ValueError("Baseline window must be 60 seconds")
    value = integrate(samples, start, end)
    if value["raw_wh"] is None:
        raise ValueError(f"Invalid baseline: {value['flags']}")
    return {**value, "watts": value["raw_wh"] * 3600 / (end - start)}


def request_energy(samples: list[Sample], raw: dict, response: dict | None, idle_w: float) -> dict:
    """Build explicitly approximate duration-aligned windows and consistency flags."""
    start = datetime.fromisoformat(raw["started_at"]).timestamp()
    end = datetime.fromisoformat(raw["ended_at"]).timestamp()
    flags = []
    windows = {"total": integrate(samples, start, end, idle_w)}
    result = {
        "tool": ENERGY["tool"],
        "mode": ENERGY["mode"],
        "primary": "post_load",
        "idle_baseline_w": idle_w,
        "flags": flags,
        "windows": windows,
        "load_seconds": None,
        "phase_residual_seconds": None,
        "wall_minus_api_seconds": None,
    }
    tolerance = max(
        ENERGY["phase_tolerance_seconds"],
        ENERGY["phase_tolerance_fraction"] * max(0, raw["wall_seconds"]),
    )
    if abs(end - start - raw["wall_seconds"]) > tolerance:
        flags.append("clock_discrepancy")
    fields = ("load_duration", "prompt_eval_duration", "eval_duration", "total_duration")
    if response is None or any(type(response.get(k)) is not int or response[k] < 0 for k in fields):
        flags.append("invalid_api_durations")
        return result
    load, prompt, decode, total = (response[k] / 1e9 for k in fields)
    residual = total - load - prompt - decode
    result.update(
        load_seconds=load,
        phase_residual_seconds=residual,
        wall_minus_api_seconds=raw["wall_seconds"] - total,
    )
    tolerance = max(ENERGY["phase_tolerance_seconds"], ENERGY["phase_tolerance_fraction"] * total)
    if abs(residual) > tolerance:
        flags.append("phase_sum_mismatch")
    for name, lo, hi in (
        ("post_load", start + load, end),
        ("prompt_eval", start + load, start + load + prompt),
        ("decode", start + load + prompt, start + load + prompt + decode),
    ):
        if lo < start or hi > end or hi < lo:
            windows[name] = {
                "start": lo,
                "end": hi,
                "seconds": hi - lo,
                "raw_wh": None,
                "adjusted_wh": None,
                "flags": ["outside_request"],
            }
        else:
            windows[name] = integrate(samples, lo, hi, idle_w)
        windows[name]["approximate"] = True
    if response.get("prompt_eval_cached_count", 0) != 0:
        flags.append("cached_prompt_tokens")
    return result
