"""One owner-approved P4 block per invocation, with durable recovery and no tracker."""

import json
import random
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from experiments.config import ENERGY, MODELS, OLLAMA, P3_PILOT, P4, P4_GROUPING, PROMPTS, TASK_IDS
from prompt_energy.energy import idle_baseline
from prompt_energy.full_energy import block_index, export_full, full_energy, measurement_index
from prompt_energy.hwinfo import LogFormat, capture_log, check_recent, parse_log, preflight_log
from prompt_energy.metadata import host_metadata
from prompt_energy.ollama import Client, decode_response, generation_request, utc_now
from prompt_energy.prompts import build_prompt
from prompt_energy.records import append_json, directory_lock, result_index, write_once
from prompt_energy.runner import (
    Journal,
    inspect_runtime,
    make_result,
    metadata_for,
    registration,
    warm_up,
)
from prompt_energy.tasks import load_tasks


def full_schedule() -> list[dict]:
    jobs = []
    for stage, tasks, repeats in (
        (1, TASK_IDS, P4["stage1_repeats"]),
        (2, P4["stage2_task_ids"], P4["stage2_repeats"]),
    ):
        part = [
            {"model": model, "task_id": task, "prompt_id": arm, "repeat": repeat, "stage": stage}
            for model in MODELS
            for task in tasks
            for arm in PROMPTS
            for repeat in repeats
        ]
        random.Random(P4["order_seed"]).shuffle(part)
        jobs.extend(part)
    return [{"run_id": f"full-{i:04d}", **job} for i, job in enumerate(jobs)]


def prepare() -> dict:
    return {
        "milestone": "P4 full",
        "owner_approval_required": True,
        "settings": P4,
        "registration": registration(),
        "schedule": full_schedule(),
        "request_count": len(full_schedule()),
        "codecarbon_enabled": False,
        "grouping_status": {
            name: "registered" if P4_GROUPING[name] else "pending_owner_labels"
            for name in ("calibration", "reference_length")
        },
    }


def check_host(host: dict) -> None:
    if host["python"].split(".")[:2] != ["3", "13"] or host["bits"] != 64:
        raise RuntimeError("Require Python 3.13 64-bit")
    if host["ac_line_status"] != 1 or host["power_mode"] != "Best performance":
        raise RuntimeError("Require observed AC power and Best performance")


def preflight(log: Path, fmt: LogFormat, *, sleep=time.sleep, now=time.time) -> dict:
    host = host_metadata()
    check_host(host)
    return {"host": host, "log": preflight_log(log, fmt, sleep=sleep, now=now)}


def launch_allowed(elapsed: float) -> bool:
    # Reserve worst-case HTTP, sandbox, end-baseline and bounded control/sensor time.
    reserve = OLLAMA["request_timeout_seconds"] + P4["baseline_seconds"] + 120
    return elapsed < P4["stop_launch_seconds"] and elapsed + reserve < P4["ceiling_seconds"]


def baseline(log: Path, mirror: Path, fmt: LogFormat, *, sleep, now) -> dict:
    sleep(ENERGY["gap_seconds"])
    start = now()
    sleep(P4["baseline_seconds"])
    samples, snapshot = capture_log(
        log, mirror, fmt, start + P4["baseline_seconds"], sleep=sleep, now=now
    )
    return {
        **idle_baseline(samples, start, start + P4["baseline_seconds"]),
        "snapshot": snapshot,
    }


def finish_saved(
    root: Path, job: dict, raw: dict, manifest: dict, tasks: dict, *, sleep, now
) -> dict:
    """Evaluate a saved raw answer at most once; never regenerate missing energy."""
    host = metadata_for(raw, root)
    block = block_index(root)[raw["session"]]["start"]
    fmt = LogFormat(**host["log_format"])
    mirror = root / "sensors" / f"{raw['session']}.csv"
    try:
        response = decode_response(raw, generation=True)
    except (ValueError, KeyError, TypeError):
        response = None
    snapshot = None
    sensor_error = None
    try:
        # Prefer the live source; a retained mirror also permits recovery after log removal.
        source = Path(host["hwinfo_log"])
        if not source.exists():
            source = mirror
        samples, snapshot = capture_log(
            source,
            mirror,
            fmt,
            datetime.fromisoformat(raw["ended_at"]).timestamp(),
            sleep=sleep,
            now=now,
        )
        energy = full_energy(samples, raw, response, block["baseline"]["watts"])
    except (OSError, ValueError) as exc:
        sensor_error = str(exc)
        energy = {"windows": {}, "flags": ["sensor_unavailable"]}
    if job["run_id"] not in result_index(root):
        base_job = {k: v for k, v in job.items() if k != "stage"}
        answer = make_result(base_job, raw, manifest, tasks[job["task_id"]], host)
        # No CodeCarbon observation exists in P4, even though the historic package is installed.
        answer["row"]["codecarbon"] = ""
        append_json(root / "results.jsonl", answer)
    result = {
        "run_id": job["run_id"],
        "block_id": raw["session"],
        "snapshot": snapshot,
        "energy": energy,
        "sensor_error": sensor_error,
    }
    append_json(root / "measurements.jsonl", result)
    export_full(root)
    return result


def validate_saved(
    journal: Journal, schedule: list, answers: dict, measures: dict, tasks: dict
) -> None:
    planned = {j["run_id"] for j in schedule}
    if (answers.keys() | measures.keys()) - planned:
        raise ValueError("Unexpected full-run IDs")
    if {k for k, r in journal.raw.items() if r["kind"] == "full_scored"} - planned:
        raise ValueError("Unexpected scored raw IDs")
    if measures.keys() - answers.keys() or answers.keys() - journal.raw.keys():
        raise ValueError("Missing supporting raw/answer records")
    for job in schedule:
        key = job["run_id"]
        if key in journal.raw:
            saved = journal.raw[key]
            expected = generation_request(
                job["model"],
                build_prompt(tasks[job["task_id"]], job["prompt_id"]),
                P4["keep_alive"],
            )
            if saved["kind"] != "full_scored" or saved["request"] != expected:
                raise ValueError("Saved full request differs from registration")
        if key in answers and any(
            answers[key]["row"][field] != job[field]
            for field in ("model", "task_id", "prompt_id", "repeat")
        ):
            raise ValueError("Saved result differs from scheduled job")


def run_block(
    root: Path,
    log: Path,
    fmt: LogFormat,
    hwinfo_version: str,
    *,
    owner_approved: bool = False,
    client_factory=Client,
    sleep=time.sleep,
    now=time.time,
    monotonic=time.monotonic,
) -> dict:
    """Run one bounded block only. Completed resume does not contact local services."""
    if not owner_approved:
        raise PermissionError("Full run not approved; no requests made")
    if not hwinfo_version.strip():
        raise ValueError("Record actual HWiNFO version")
    with directory_lock(root):
        session = uuid.uuid4().hex
        journal = Journal(root, client_factory(), session)
        jobs = full_schedule()
        tasks = {t.task_id: t for t in load_tasks()}
        answers, measures = result_index(root), measurement_index(root)
        path = root / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        if manifest and (
            manifest["milestone"] != "P4 full"
            or manifest["registration"] != registration()
            or manifest["schedule"] != jobs
            or manifest["log_format"] != asdict(fmt)
            or manifest["hwinfo_version"] != hwinfo_version
        ):
            raise ValueError("Full-run registration/format/version changed")
        if (
            answers or measures or any(k.startswith("full-") for k in journal.raw)
        ) and not manifest:
            raise ValueError("Full-run evidence without manifest")
        validate_saved(journal, jobs, answers, measures, tasks)
        for job in jobs:
            key = job["run_id"]
            if key in journal.raw and key not in measures:
                measures[key] = finish_saved(
                    root, job, journal.raw[key], manifest, tasks, sleep=sleep, now=now
                )
        if len(measures) == len(jobs):
            export_full(root)
            return {"completed": len(measures), "new_requests": 0, "remaining": 0}
        checked = preflight(log, fmt, sleep=sleep, now=now)
        started = monotonic()
        runtime = inspect_runtime(journal)
        if runtime["version"] != P3_PILOT["expected_runtime_version"] or any(
            runtime["models"][m]["digest"] != digest
            for m, digest in P3_PILOT["expected_model_digests"].items()
        ):
            raise ValueError("Runtime/model digest changed from registered versions")
        if manifest and manifest["runtime"] != runtime:
            raise ValueError("Runtime metadata changed")
        if manifest is None:
            manifest = {
                "milestone": "P4 full",
                "created_at": utc_now(),
                "registration": registration(),
                "schedule": jobs,
                "runtime": runtime,
                "log_format": asdict(fmt),
                "hwinfo_version": hwinfo_version,
                "grouping": P4_GROUPING,
            }
            write_once(path, manifest)
        append_json(
            root / "sessions.jsonl",
            {
                "session": session,
                "started_at": utc_now(),
                **checked["host"],
                "hwinfo_log": str(log.resolve()),
                "log_format": asdict(fmt),
                "preflight": checked["log"],
            },
        )
        for model in MODELS:
            warm_up(journal, model)
            journal.unload(model, f"warmup/{model}")
        mirror = root / "sensors" / f"{session}.csv"
        opening = baseline(log, mirror, fmt, sleep=sleep, now=now)
        append_json(
            root / "blocks.jsonl",
            {
                "block_id": session,
                "event": "start",
                "baseline": opening,
                "at": utc_now(),
            },
        )
        count = 0
        safe_idle = True
        status = "complete"
        try:
            for job in jobs:
                key = job["run_id"]
                if key in measures:
                    continue
                if not launch_allowed(monotonic() - started):
                    status = "time_limit"
                    break
                sleep(ENERGY["gap_seconds"])
                check_host(host_metadata())
                check_recent(parse_log(log.read_bytes(), fmt, live=True), now())
                if not launch_allowed(monotonic() - started):
                    status = "time_limit"
                    break
                journal.unload(job["model"], f"before/{key}")
                if not launch_allowed(monotonic() - started):
                    status = "time_limit"
                    break
                safe_idle = False
                raw = journal.request(
                    key,
                    "full_scored",
                    "/api/generate",
                    generation_request(
                        job["model"],
                        build_prompt(tasks[job["task_id"]], job["prompt_id"]),
                        P4["keep_alive"],
                    ),
                )
                safe_idle = raw["error"] is None
                measures[key] = finish_saved(root, job, raw, manifest, tasks, sleep=sleep, now=now)
                count += 1
                print(f"{len(measures)}/{len(jobs)} {key} stage {job['stage']} saved", flush=True)
                if raw["error"] or measures[key]["sensor_error"]:
                    raise RuntimeError("Transport/sensor failure retained; inspect before resume")
                if "cached_prompt_tokens" in measures[key]["energy"]["flags"]:
                    raise RuntimeError("Cached tokens detected; saved and stopped")
                journal.unload(job["model"], f"after/{key}")
        except BaseException:
            status = "interrupted"
            raise
        finally:
            ending = None
            flags = []
            reason = None
            closure_reserve = P4["baseline_seconds"] + 120
            if safe_idle and monotonic() - started + closure_reserve < P4["ceiling_seconds"]:
                try:
                    for model in MODELS:
                        journal.unload(model, f"end/{model}")
                    check_host(host_metadata())
                    ending = baseline(log, mirror, fmt, sleep=sleep, now=now)
                except (OSError, ValueError, RuntimeError) as exc:
                    reason = str(exc)
            else:
                reason = "Request completion uncertain or block ceiling leaves no idle window"
            if ending is None:
                flags.append("end_baseline_missing")
            elapsed = monotonic() - started
            if elapsed > P4["ceiling_seconds"]:
                flags.append("block_ceiling_exceeded")
            append_json(
                root / "blocks.jsonl",
                {
                    "block_id": session,
                    "event": "end",
                    "baseline": ending,
                    "status": status,
                    "flags": flags,
                    "reason": reason,
                    "elapsed_seconds": elapsed,
                    "at": utc_now(),
                },
            )
            export_full(root)
        return {
            "completed": len(measures),
            "new_requests": count,
            "remaining": len(jobs) - len(measures),
            "block_status": status,
            "end_baseline_available": ending is not None,
        }
