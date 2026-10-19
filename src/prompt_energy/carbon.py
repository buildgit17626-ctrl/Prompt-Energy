"""Secondary offline CodeCarbon envelopes, independent of HWiNFO phase estimates."""

import math
from dataclasses import asdict

from experiments.config import CODECARBON
from prompt_energy.ollama import Client, utc_now


class CarbonMeter:
    """Import lazily: constructing a plan or parsing CSV must never start a tracker."""

    def __init__(self, factory=None) -> None:
        if factory is None:
            from codecarbon import OfflineEmissionsTracker

            factory = OfflineEmissionsTracker
        self.tracker = factory(
            country_iso_code=CODECARBON["country_iso_code"],
            tracking_mode="machine",
            measure_power_secs=CODECARBON["measure_power_secs"],
            save_to_file=False,
            save_to_api=False,
            save_to_logger=False,
            save_to_prometheus=False,
            save_to_logfire=False,
            output_handlers=[],
            allow_multiple_runs=False,
            log_level="error",
            pue=1,
        )
        self.active = None

    def start(self) -> None:
        self.tracker.start()

    def begin(self, name: str) -> None:
        if self.active is not None:
            raise RuntimeError("Overlapping CodeCarbon task")
        self.started_at = utc_now()
        self.tracker.start_task(name)
        self.active = name

    def end(self) -> dict:
        if self.active is None:
            raise RuntimeError("No active CodeCarbon task")
        name, self.active = self.active, None
        data = self.tracker.stop_task(name)
        if data is None:
            raise RuntimeError("CodeCarbon returned no measurement")
        native = asdict(data)
        for key in ("energy_consumed", "emissions", "duration"):
            if not isinstance(native.get(key), int | float) or not math.isfinite(native[key]):
                raise ValueError(f"Invalid CodeCarbon {key}")
        if native["energy_consumed"] < 0 or native["duration"] <= 0:
            raise ValueError("Invalid CodeCarbon energy/duration")
        return {
            "tool": "CodeCarbon",
            "mode": CODECARBON["mode"],
            "native": native,
            "started_at": self.started_at,
            "ended_at": utc_now(),
            "raw_wh": native["energy_consumed"] * 1000,
            "raw_co2e_kg": native["emissions"],
            "seconds": native["duration"],
        }

    def close(self) -> None:
        self.tracker.stop()


class MeasuredClient:
    """Measure only the next marked scored call; control and warm-up remain unscored."""

    def __init__(self, client: Client, meter: CarbonMeter) -> None:
        self.client, self.meter = client, meter
        self.next_task = None

    def exchange(self, path: str, payload: dict | None = None) -> dict:
        if self.next_task is None:
            return self.client.exchange(path, payload)
        name, self.next_task = self.next_task, None
        error = None
        try:
            self.meter.begin(name)
        except Exception as exc:
            error = f"start:{type(exc).__name__}:{exc}"
        raw = self.client.exchange(path, payload)
        observation = None
        if error is None:
            try:
                observation = self.meter.end()
            except Exception as exc:
                error = f"stop:{type(exc).__name__}:{exc}"
        return {**raw, "codecarbon": observation, "codecarbon_error": error}


def carbon_adjusted(observation: dict | None, baseline: dict | None) -> dict:
    """Subtract this tool's own idle rate over its actual envelope; no phase allocation."""
    if observation is None or baseline is None:
        return {"flags": ["codecarbon_missing"], "adjusted_wh": None, "co2e_kg": None}
    idle_w = baseline["raw_wh"] * 3600 / baseline["seconds"]
    adjusted = observation["raw_wh"] - idle_w * observation["seconds"] / 3600
    co2 = observation["raw_co2e_kg"] - (
        baseline["raw_co2e_kg"] / baseline["seconds"] * observation["seconds"]
    )
    return {
        "raw_wh": observation["raw_wh"],
        "adjusted_wh": adjusted,
        "co2e_kg": co2,
        "idle_w": idle_w,
        "seconds": observation["seconds"],
        "flags": ["codecarbon_negative_adjusted"] if adjusted < 0 else [],
    }
