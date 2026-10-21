"""Separate, energy-free calibration; never learn groups from main-run outcomes."""

import hashlib
import json
import statistics
import uuid
from pathlib import Path

from experiments.config import CALIBRATION, P3_PILOT, TASK_IDS
from prompt_energy.full_run import check_host
from prompt_energy.metadata import host_metadata
from prompt_energy.ollama import Client, generation_request, utc_now
from prompt_energy.prompts import build_prompt
from prompt_energy.records import append_json, directory_lock, export_csv, result_index, write_once
from prompt_energy.runner import (
    Journal,
    inspect_runtime,
    make_result,
    metadata_for,
    registration,
    warm_up,
)
from prompt_energy.tasks import load_tasks


def reference_lengths() -> dict:
    """Count canonical-body physical lines; exclude blank and comment-only lines."""
    counts = {
        t.task_id: sum(
            bool(line.strip()) and not line.lstrip().startswith("#")
            for line in t.canonical_solution.splitlines()
        )
        for t in load_tasks()
    }
    median = statistics.median(counts.values())
    return {
        "counts": counts,
        "median": median,
        "labels": {k: "short" if v <= median else "long" for k, v in counts.items()},
    }


def schedule() -> list[dict]:
    return [
        {
            "run_id": f"calibration-{i:03d}",
            "model": CALIBRATION["model"],
            "prompt_id": "P0",
            "task_id": task,
            "repeat": 1,
        }
        for i, task in enumerate(TASK_IDS)
    ]


def labels(root: Path) -> dict:
    """Export only a complete separate calibration with supporting raw evidence."""
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    jobs = schedule()
    if manifest.get("milestone") != "P4 calibration" or manifest["schedule"] != jobs:
        raise ValueError("Not the registered calibration")
    answers = result_index(root)
    if set(answers) != {j["run_id"] for j in jobs}:
        raise ValueError("Calibration incomplete")
    journal = Journal(root, Client(), "read-only")
    validate_saved_calibration(journal, jobs, answers)
    if any(
        a["row"]["failure_type"] in {"api_error", "transport_error", "infrastructure_error"}
        or journal.raw[k]["error"]
        for k, a in answers.items()
    ):
        raise ValueError("Infrastructure/transport failure requires investigation before freezing")
    return {
        "labels": {
            j["task_id"]: "solved" if answers[j["run_id"]]["row"]["passed"] else "failed"
            for j in jobs
        },
        "source_sha256": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ("manifest.json", "raw.jsonl", "results.jsonl")
        },
    }


def validate_saved_calibration(journal: Journal, jobs: list, answers: dict) -> None:
    tasks = {t.task_id: t for t in load_tasks()}
    # Compare immutable evidence to the registered requests before accepting labels.
    expected = {j["run_id"] for j in jobs}
    if {k for k, r in journal.raw.items() if r["kind"] == "calibration"} - expected:
        raise ValueError("Unexpected calibration raw IDs")
    for job in jobs:
        raw = journal.raw.get(job["run_id"])
        if raw and (
            raw["kind"] != "calibration"
            or raw["request"]
            != generation_request(job["model"], build_prompt(tasks[job["task_id"]], "P0"), 0)
        ):
            raise ValueError("Changed calibration request")
    if answers.keys() - expected or answers.keys() - journal.raw.keys():
        raise ValueError("Unexpected/orphan calibration outcomes")
    for job in jobs:
        if job["run_id"] in answers and any(
            answers[job["run_id"]]["row"][k] != job[k]
            for k in ("model", "prompt_id", "task_id", "repeat")
        ):
            raise ValueError("Changed calibration outcome metadata")


def run(root: Path, *, approved: bool = False, client_factory=Client) -> dict:
    if not approved:
        raise PermissionError("Calibration execution approval required")
    with directory_lock(root):
        journal = Journal(root, client_factory(), uuid.uuid4().hex)
        jobs, answers = schedule(), result_index(root)
        path = root / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        if manifest and (
            manifest["milestone"] != "P4 calibration"
            or manifest["registration"] != registration()
            or manifest["schedule"] != jobs
        ):
            raise ValueError("Calibration registration changed")
        if (
            answers or any(r["kind"] == "calibration" for r in journal.raw.values())
        ) and not manifest:
            raise ValueError("Calibration evidence without manifest")
        validate_saved_calibration(journal, jobs, answers)
        tasks = {t.task_id: t for t in load_tasks()}
        for job in jobs:
            key = job["run_id"]
            if key in journal.raw and key not in answers:
                answers[key] = make_result(
                    job,
                    journal.raw[key],
                    manifest,
                    tasks[job["task_id"]],
                    metadata_for(journal.raw[key], root),
                )
                append_json(root / "results.jsonl", answers[key])
        if len(answers) == len(jobs):
            export_csv(root)
            return {"completed": len(answers), "new_requests": 0}
        if any(
            journal.raw[k]["error"]
            or a["row"]["failure_type"] in {"api_error", "infrastructure_error"}
            for k, a in answers.items()
        ):
            raise RuntimeError("Saved infrastructure failure requires investigation")
        host = host_metadata()
        check_host(host)
        runtime = inspect_runtime(journal)
        if runtime["version"] != P3_PILOT["expected_runtime_version"] or any(
            runtime["models"][m]["digest"] != d
            for m, d in P3_PILOT["expected_model_digests"].items()
        ):
            raise ValueError("Runtime/model changed")
        if manifest and manifest["runtime"] != runtime:
            raise ValueError("Runtime metadata changed")
        if not manifest:
            manifest = {
                "milestone": "P4 calibration",
                "registration": registration(),
                "schedule": jobs,
                "runtime": runtime,
                "settings": CALIBRATION,
                "include_in_main_analysis": False,
                "created_at": utc_now(),
            }
            write_once(path, manifest)
        append_json(
            root / "sessions.jsonl", {"session": journal.session, **host, "started_at": utc_now()}
        )
        model = CALIBRATION["model"]
        warm_up(journal, model)
        journal.unload(model, "after-warmup")
        count = 0
        for job in jobs:
            key = job["run_id"]
            if key in answers:
                continue
            journal.unload(model, f"before/{key}")
            raw = journal.request(
                key,
                "calibration",
                "/api/generate",
                generation_request(model, build_prompt(tasks[job["task_id"]], "P0"), 0),
            )
            answers[key] = make_result(job, raw, manifest, tasks[job["task_id"]], host)
            append_json(root / "results.jsonl", answers[key])
            export_csv(root)
            count += 1
            print(
                f"{len(answers)}/{len(jobs)} {key}: "
                f"{answers[key]['row']['failure_type'] or 'passed'}",
                flush=True,
            )
            if raw["error"] or answers[key]["row"]["failure_type"] in {
                "api_error",
                "infrastructure_error",
            }:
                raise RuntimeError("Calibration failure retained; investigate before resume")
        return {"completed": len(answers), "new_requests": count}
