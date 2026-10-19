"""P2 smoke orchestration: immutable schedule, native counts, and auditable resume."""

import hashlib
import json
import random
import time
import uuid
from pathlib import Path

from experiments import config
from prompt_energy.evaluation import evaluate
from prompt_energy.metadata import host_metadata
from prompt_energy.ollama import Client, decode_response, generation_request, utc_now
from prompt_energy.prompts import build_prompt
from prompt_energy.records import (
    FIELDS,
    append_json,
    directory_lock,
    export_csv,
    read_jsonl,
    result_index,
    validate_row,
    write_once,
)
from prompt_energy.tasks import DATA_DIR, Task, load_tasks


def registration() -> dict:
    """Fingerprint executable protocol and dataset, not editable report prose."""
    root = DATA_DIR.parent
    files = sorted((root / "src" / "prompt_energy").glob("*.py"))
    files += [root / "experiments" / "config.py", DATA_DIR / "manifest.json"]
    return {
        str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in files
    }


def smoke_schedule() -> list[dict]:
    """Interleave all task/prompt combinations with a local seeded RNG."""
    jobs = [
        {"model": config.P2_SMOKE["model"], "task_id": task, "prompt_id": prompt, "repeat": 1}
        for task in config.P2_SMOKE["task_ids"]
        for prompt in config.P2_SMOKE["prompt_ids"]
    ]
    random.Random(config.P2_SMOKE["order_seed"]).shuffle(jobs)
    return [{"run_id": f"smoke-{i:03d}", **job} for i, job in enumerate(jobs)]


class Journal:
    """Record intent before HTTP, response before parsing, and never silently retry."""

    def __init__(self, root: Path, client: Client, session: str) -> None:
        self.root, self.client, self.session = root, client, session
        self.raw = {}
        intents = {}
        for item in read_jsonl(root / "requests.jsonl"):
            key = item["request_id"]
            if key in intents:
                raise ValueError(f"Duplicate request intent: {key}")
            intents[key] = item
        for item in read_jsonl(root / "raw.jsonl"):
            key = item["request_id"]
            if key in self.raw or key not in intents:
                raise ValueError(f"Duplicate/orphan raw response: {key}")
            if (item["path"], item["request"]) != (intents[key]["path"], intents[key]["request"]):
                raise ValueError(f"Request/response mismatch: {key}")
            self.raw[key] = item
        if pending := intents.keys() - self.raw.keys():
            raise RuntimeError(
                f"Uncertain in-flight requests {sorted(pending)}; retain files and investigate. "
                "No automatic regeneration is permitted."
            )

    def request(self, key: str, kind: str, path: str, payload: dict | None = None) -> dict:
        """Reuse a durable response even if the prior process stopped before evaluation."""
        if key in self.raw:
            saved = self.raw[key]
            if (saved["path"], saved["request"], saved["kind"]) != (path, payload, kind):
                raise ValueError(f"Changed request for {key}")
            return saved
        append_json(
            self.root / "requests.jsonl",
            {
                "request_id": key,
                "kind": kind,
                "session": self.session,
                "path": path,
                "request": payload,
                "intent_at": utc_now(),
            },
        )
        record = {
            **self.client.exchange(path, payload),
            "request_id": key,
            "kind": kind,
            "session": self.session,
        }
        append_json(self.root / "raw.jsonl", record)
        self.raw[key] = record
        return record

    def control(self, label: str, path: str, payload: dict | None = None) -> dict:
        """Control observations are session-specific and also preserved."""
        key = f"{self.session}/{label}"
        return decode_response(self.request(key, "control", path, payload))

    def unload(self, model: str, label: str) -> None:
        """Zero unloads after a request, so explicitly remove existing cached state first."""
        self.control(f"{label}/unload", "/api/generate", {"model": model, "keep_alive": 0})
        deadline = time.monotonic() + config.P2_CONTROL["unload_timeout_seconds"]
        attempt = 0
        while True:
            state = self.control(f"{label}/ps-{attempt}", "/api/ps")
            if not any(
                row.get("name") == model or row.get("model") == model for row in state["models"]
            ):
                return
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Model did not unload: {model}")
            time.sleep(config.P2_CONTROL["unload_poll_seconds"])
            attempt += 1


def inspect_runtime(journal: Journal) -> dict:
    """Record exact runtime version, model digest, template, parameters and licence."""
    version = journal.control("version", "/api/version")["version"]
    tags = journal.control("tags", "/api/tags")["models"]
    models = {}
    for model in config.MODELS:
        tag = next((row for row in tags if row["name"] == model), None)
        if tag is None:
            raise RuntimeError(f"Required model is not installed: {model}")
        shown = journal.control(f"show/{model}", "/api/show", {"model": model})
        models[model] = {"digest": tag["digest"], "details": tag["details"], "show": shown}
    return {"version": version, "models": models}


def resolve_cache(journal: Journal, tasks: dict) -> dict:
    """Report observed text equality; timing decreases are conservative signals, not proof."""
    target = journal.root / "cache_policy.json"
    if target.exists():
        return json.loads(target.read_text(encoding="utf-8"))
    observations = []
    for model in config.MODELS:
        keys = [f"probe/{model}/{i}" for i in range(2)]
        present = [key in journal.raw for key in keys]
        if any(present) and not all(present):
            raise RuntimeError(
                "Interrupted probe pair: cannot infer cache behavior across sessions"
            )
        if not all(present):
            journal.unload(model, f"probe-start/{model}")
            warm_up(journal, model)
        request = generation_request(model, build_prompt(tasks[config.TASK_IDS[0]], "P0"), -1)
        envelopes = [journal.request(key, "determinism", "/api/generate", request) for key in keys]
        first, second = [decode_response(item, generation=True) for item in envelopes]
        observations.append(
            {
                "model": model,
                "request_ids": keys,
                "text_identical": first["response"] == second["response"],
                "prompt_eval_count": [first["prompt_eval_count"], second["prompt_eval_count"]],
                "prompt_eval_duration": [
                    first["prompt_eval_duration"],
                    second["prompt_eval_duration"],
                ],
                "reuse_signal": (
                    second["prompt_eval_count"] < first["prompt_eval_count"]
                    or second["prompt_eval_duration"] < first["prompt_eval_duration"]
                ),
            }
        )
    resolved = {
        "registered_rule": config.CACHE_POLICY,
        "observations": observations,
        "keep_alive": 0 if any(row["reuse_signal"] for row in observations) else -1,
        "resolved_at": utc_now(),
    }
    write_once(target, resolved)
    return resolved


def warm_up(journal: Journal, model: str) -> None:
    """One saved but unscored warm-up per model per process session."""
    warmup = journal.request(
        f"{journal.session}/warmup/{model}",
        "warmup",
        "/api/generate",
        generation_request(model, config.WARMUP_PROMPT, -1),
    )
    decode_response(warmup, generation=True)


def make_result(job: dict, raw: dict, manifest: dict, task: Task, metadata: dict) -> dict:
    """Map native measurements to SPEC, leaving all unmeasured fields empty."""
    row = dict.fromkeys(FIELDS, "")
    row.update(job)
    row.update(
        {
            "timestamp": raw["started_at"],
            "seed": config.EXECUTION_SEED,
            "model_hash": manifest["runtime"]["models"][job["model"]]["digest"],
            "wall_seconds": raw["wall_seconds"],
            "raw_output_path": f"raw.jsonl#{job['run_id']}",
            "python": metadata["python"],
            "runtime_version": manifest["runtime"]["version"],
            "codecarbon": metadata["libraries"]["codecarbon"],
            "cpu_model": metadata["cpu_model"],
            "os": metadata["os"],
            "power_mode": metadata["power_mode"],
        }
    )
    detail = {}
    try:
        response = decode_response(raw, generation=True)
    except (ValueError, KeyError, TypeError) as exc:
        failure = raw["error"]["type"] if raw["error"] else "api_error"
        reason = str(exc)
    else:
        row.update(
            {
                "input_tokens": response["prompt_eval_count"],
                "output_tokens": response["eval_count"],
                "tokens_per_second": (
                    response["eval_count"] * 1e9 / response["eval_duration"]
                    if response["eval_duration"]
                    else ""
                ),
            }
        )
        failure, reason, detail = evaluate(task, response)
    row.update({"passed": not failure, "failure_type": failure})
    validate_row(row)
    return {"row": row, "reason": reason, "sandbox": detail, "session": raw["session"]}


def run_smoke(root: Path, client: Client | None = None) -> dict:
    """Complete/resume the registered smoke only; no energy tracking or full-run switch."""
    with directory_lock(root):
        session = uuid.uuid4().hex
        journal = Journal(root, client or Client(), session)
        manifest_path = root / "manifest.json"
        completed = result_index(root)
        manifest = (
            json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest_path.exists()
            else None
        )
        fingerprint = registration()
        schedule = smoke_schedule()
        if manifest and (
            manifest["registration"] != fingerprint or manifest["schedule"] != schedule
        ):
            raise ValueError("Registration changed; cannot resume this batch")
        scheduled = {job["run_id"] for job in schedule}
        if completed.keys() - scheduled:
            raise ValueError("Unexpected result IDs")
        if completed and not manifest:
            raise ValueError("Results without a manifest")
        if manifest and len(completed) == len(schedule):
            export_csv(root)
            return {"completed": len(completed), "new_requests": 0}
        metadata = host_metadata()
        if metadata["python"].split(".")[:2] != ["3", "13"] or metadata["bits"] != 64:
            raise RuntimeError("Python 3.13 (64-bit) is required")
        append_json(
            root / "sessions.jsonl", {"session": session, "started_at": utc_now(), **metadata}
        )
        runtime = inspect_runtime(journal)
        if manifest:
            if runtime != manifest["runtime"]:
                raise ValueError("Runtime/model metadata changed; cannot resume")
        else:
            manifest = {
                "created_at": utc_now(),
                "registration": fingerprint,
                "schedule": schedule,
                "runtime": runtime,
                "initial_host": metadata,
                "milestone": "P2 smoke",
            }
            write_once(manifest_path, manifest)
        tasks = {task.task_id: task for task in load_tasks()}
        cache = resolve_cache(journal, tasks)
        keep_alive = cache["keep_alive"]
        model = config.P2_SMOKE["model"]
        needs_generation = any(job["run_id"] not in journal.raw for job in schedule)
        if needs_generation:
            # Do not leave a probe of the other model consuming RAM during scored requests.
            for other in config.MODELS:
                if other != model:
                    journal.unload(other, f"before-warmup/{other}")
            warm_up(journal, model)
            if keep_alive == 0:
                journal.unload(model, "after-warmup")
        new_requests = 0
        for job in schedule:
            key = job["run_id"]
            if key in completed:
                continue
            task = tasks[job["task_id"]]
            fresh = key not in journal.raw
            if fresh and keep_alive == 0:
                journal.unload(model, f"before/{key}")
            raw = journal.request(
                key,
                "scored",
                "/api/generate",
                generation_request(model, build_prompt(task, job["prompt_id"]), keep_alive),
            )
            record = make_result(job, raw, manifest, task, metadata_for(raw, root))
            append_json(root / "results.jsonl", record)
            completed[key] = record
            new_requests += int(fresh)
            export_csv(root)
            print(
                f"{len(completed)}/{len(schedule)} {key} {job['task_id']} {job['prompt_id']}: "
                f"{record['row']['failure_type'] or 'passed'}",
                flush=True,
            )
            if raw["error"]:
                # A timed-out server could still be busy: stop, rather than overlap requests.
                raise RuntimeError("Transport failure recorded; stop batch and inspect Ollama")
            if fresh and keep_alive == 0:
                journal.unload(model, f"after/{key}")
        return {"completed": len(completed), "new_requests": new_requests, "keep_alive": keep_alive}


def metadata_for(raw: dict, root: Path) -> dict:
    """Recovered raw output keeps the environment of its original generation session."""
    return next(
        row for row in read_jsonl(root / "sessions.jsonl") if row["session"] == raw["session"]
    )
