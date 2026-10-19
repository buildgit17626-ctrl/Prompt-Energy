"""Owner-gated P3 pilot; no live action is performed by preparing the schedule."""

import json
import random
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from experiments.config import CODECARBON, ENERGY, P3_PILOT
from prompt_energy.carbon import CarbonMeter, MeasuredClient, carbon_adjusted
from prompt_energy.energy import idle_baseline, request_energy
from prompt_energy.energy_report import export_energy, measurement_index
from prompt_energy.hwinfo import LogFormat, capture_log, check_recent, parse_log, preflight_log
from prompt_energy.metadata import host_metadata
from prompt_energy.ollama import Client, decode_response, generation_request, utc_now
from prompt_energy.prompts import build_prompt
from prompt_energy.records import append_json, directory_lock, read_jsonl, result_index, write_once
from prompt_energy.runner import (
    Journal,
    inspect_runtime,
    make_result,
    metadata_for,
    registration,
    warm_up,
)
from prompt_energy.tasks import load_tasks


def pilot_schedule() -> list[dict]:
    """Seeded interleaving across models, tasks, prompts and both repeats."""
    jobs = [
        {"model": model, "task_id": task, "prompt_id": prompt, "repeat": repeat}
        for model in P3_PILOT["models"]
        for task in P3_PILOT["task_ids"]
        for prompt in P3_PILOT["prompt_ids"]
        for repeat in range(1, P3_PILOT["repeats"] + 1)
    ]
    random.Random(P3_PILOT["order_seed"]).shuffle(jobs)
    return [{"run_id": f"pilot-{i:04d}", **job} for i, job in enumerate(jobs)]


def prepare_pilot() -> dict:
    """Return reviewable registration without network, sensors, trackers or output writes."""
    return {
        "milestone": "P3 pilot",
        "pilot_approved": False,
        "registration": registration(),
        "settings": P3_PILOT,
        "energy": ENERGY,
        "codecarbon": CODECARBON,
        "request_count": len(pilot_schedule()),
        "schedule": pilot_schedule(),
    }


def _check_host(host: dict) -> None:
    if host["python"].split(".")[:2] != ["3", "13"] or host["bits"] != 64:
        raise RuntimeError("Require Python 3.13 64-bit")
    if host["ac_line_status"] != 1 or host["power_mode"] != "Best performance":
        raise RuntimeError("Require observed AC power and Best performance")


def preflight(path: Path, fmt: LogFormat, *, sleep=time.sleep, now=time.time) -> dict:
    """Read host and growing sensor log only; no Ollama or CodeCarbon actions."""
    host = host_metadata()
    _check_host(host)
    return {"host": host, "log": preflight_log(path, fmt, sleep=sleep, now=now)}


def _finish_run(
    root: Path, job: dict, raw: dict, manifest: dict, tasks: dict, *, sleep, now
) -> dict:
    """Recover a saved answer without another request; never rewrite earlier evidence."""
    host = metadata_for(raw, root)
    baseline = next(b for b in read_jsonl(root / "baselines.jsonl") if b["id"] == raw["session"])
    fmt = LogFormat(**host["log_format"])
    source = Path(host["hwinfo_log"])
    try:
        response = decode_response(raw, generation=True)
    except (ValueError, KeyError, TypeError):
        response = None
    mirror = root / "sensors" / f"{raw['session']}.csv"
    snapshot = None
    try:
        samples, snapshot = capture_log(
            source,
            mirror,
            fmt,
            datetime.fromisoformat(raw["ended_at"]).timestamp(),
            sleep=sleep,
            now=now,
        )
        energy = request_energy(samples, raw, response, baseline["hwinfo"]["watts"])
        sensor_error = None
    except (OSError, ValueError) as exc:
        sensor_error = str(exc)
        energy = {
            "flags": ["sensor_unavailable"],
            "windows": {},
            "idle_baseline_w": baseline["hwinfo"]["watts"],
        }
    if job["run_id"] not in result_index(root):
        record = make_result(job, raw, manifest, tasks[job["task_id"]], host)
        append_json(root / "results.jsonl", record)
    measure = {
        "run_id": job["run_id"],
        "baseline_id": baseline["id"],
        "snapshot": snapshot,
        "energy": energy,
        "sensor_error": sensor_error,
        "carbon": carbon_adjusted(raw.get("codecarbon"), baseline.get("codecarbon")),
    }
    append_json(root / "measurements.jsonl", measure)
    export_energy(root)
    return measure


def run_pilot(
    root: Path,
    log: Path,
    fmt: LogFormat,
    hwinfo_version: str,
    *,
    owner_approved: bool = False,
    client_factory=Client,
    meter_factory=CarbonMeter,
    sleep=time.sleep,
    now=time.time,
) -> dict:
    """Explicit approval is required even before metadata calls or a warm-up."""
    if not owner_approved:
        raise PermissionError(
            "Pilot is not approved. Review the plan and obtain owner approval first."
        )
    if not hwinfo_version.strip():
        raise ValueError("Record the actual installed HWiNFO version")
    with directory_lock(root):
        session = uuid.uuid4().hex
        journal = Journal(root, client_factory(), session)
        schedule = pilot_schedule()
        planned = {j["run_id"] for j in schedule}
        answers, measures = result_index(root), measurement_index(root)
        if answers.keys() - planned or measures.keys() - planned:
            raise ValueError("Unexpected pilot IDs")
        if measures.keys() - answers.keys() or answers.keys() - journal.raw.keys():
            raise ValueError("Pilot journal is missing supporting answer/raw records")
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
        fingerprint = registration()
        if manifest and (
            manifest["registration"] != fingerprint or manifest["schedule"] != schedule
        ):
            raise ValueError(
                "Pilot source/config changed; do not resume under a different protocol"
            )
        if (answers or measures) and not manifest:
            raise ValueError("Pilot records without a manifest")
        if manifest and (
            manifest["log_format"] != asdict(fmt) or manifest["hwinfo_version"] != hwinfo_version
        ):
            raise ValueError("Sensor format/version changed during pilot")
        tasks = {t.task_id: t for t in load_tasks(P3_PILOT["task_ids"])}
        for job in schedule:
            key = job["run_id"]
            if key in journal.raw and key not in measures:
                measures[key] = _finish_run(
                    root, job, journal.raw[key], manifest, tasks, sleep=sleep, now=now
                )
        if len(measures) == len(schedule):
            export_energy(root)
            return {"completed": len(measures), "new_requests": 0}
        check = preflight(log, fmt, sleep=sleep, now=now)
        host = check["host"]
        runtime = inspect_runtime(journal)
        if runtime["version"] != P3_PILOT["expected_runtime_version"] or any(
            runtime["models"][model]["digest"] != digest
            for model, digest in P3_PILOT["expected_model_digests"].items()
        ):
            raise ValueError("Ollama version/model digest differs from accepted P2 registration")
        if manifest and manifest["runtime"] != runtime:
            raise ValueError("Runtime metadata changed")
        if manifest is None:
            manifest = {
                "milestone": "P3 pilot",
                "created_at": utc_now(),
                "registration": fingerprint,
                "schedule": schedule,
                "runtime": runtime,
                "log_format": asdict(fmt),
                "hwinfo_version": hwinfo_version,
                "include_in_main_analysis": False,
            }
            write_once(manifest_path, manifest)
        append_json(
            root / "sessions.jsonl",
            {
                "session": session,
                "started_at": utc_now(),
                **host,
                "hwinfo_log": str(log.resolve()),
                "log_format": asdict(fmt),
                "preflight": check["log"],
            },
        )
        meter = meter_factory()
        try:
            for model in P3_PILOT["models"]:
                warm_up(journal, model)
                journal.unload(model, f"pilot-warmup/{model}")
            meter.start()
            sleep(ENERGY["gap_seconds"])
            meter.begin(f"{session}/baseline")
            baseline_start = now()
            sleep(ENERGY["baseline_seconds"])
            baseline_end = baseline_start + ENERGY["baseline_seconds"]
            carbon = meter.end()
            samples, snapshot = capture_log(
                log, root / "sensors" / f"{session}.csv", fmt, baseline_end, sleep=sleep, now=now
            )
            baseline = {
                "id": session,
                "hwinfo": idle_baseline(samples, baseline_start, baseline_end),
                "codecarbon": carbon,
                "snapshot": snapshot,
            }
            append_json(root / "baselines.jsonl", baseline)
            measured = MeasuredClient(journal.client, meter)
            journal.client = measured
            count = 0
            for job in schedule:
                key = job["run_id"]
                if key in measures:
                    continue
                sleep(ENERGY["gap_seconds"])
                _check_host(host_metadata())
                check_recent(parse_log(log.read_bytes(), fmt, live=True), now())
                journal.unload(job["model"], f"pilot-before/{key}")
                measured.next_task = key
                raw = journal.request(
                    key,
                    "pilot_scored",
                    "/api/generate",
                    generation_request(
                        job["model"],
                        build_prompt(tasks[job["task_id"]], job["prompt_id"]),
                        0,
                    ),
                )
                measure = _finish_run(root, job, raw, manifest, tasks, sleep=sleep, now=now)
                measures[key] = measure
                count += 1
                print(f"{len(measures)}/{len(schedule)} {key} saved", flush=True)
                if raw["error"] or measure["sensor_error"] or raw.get("codecarbon_error"):
                    raise RuntimeError(
                        "Failed transport/sensor/secondary measurement saved; inspect before resume"
                    )
                if "cached_prompt_tokens" in measure["energy"]["flags"]:
                    raise RuntimeError(
                        "Cached tokens detected despite keep_alive=0; saved and stopped"
                    )
                journal.unload(job["model"], f"pilot-after/{key}")
            return {"completed": len(measures), "new_requests": count}
        finally:
            meter.close()
