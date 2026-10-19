"""Offline fixtures exercise transport, audit persistence, failures and resumption."""

import base64
import csv
import json
from collections import Counter
from dataclasses import asdict

import pytest

from experiments import config
from prompt_energy import evaluation, ollama, runner
from prompt_energy.metadata import host_metadata
from prompt_energy.ollama import Client, decode_response, generation_request
from prompt_energy.records import (
    ENERGY_FIELDS,
    FIELDS,
    append_json,
    directory_lock,
    read_jsonl,
    result_index,
    write_once,
)
from prompt_energy.sandbox import TestResult as SandboxResult
from prompt_energy.tasks import Task


def response(text="def answer():\n    return 1", **changes):
    return {
        "response": text,
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 31,
        "eval_count": 12,
        "total_duration": 3_000_000_000,
        "load_duration": 500_000_000,
        "prompt_eval_duration": 500_000_000,
        "eval_duration": 2_000_000_000,
        **changes,
    }


def envelope(value, path="/api/generate", request=None, **changes):
    return {
        "started_at": "2026-10-19T00:00:00+00:00",
        "ended_at": "2026-10-19T00:00:03+00:00",
        "wall_seconds": 3.1,
        "path": path,
        "request": request,
        "http_status": 200,
        "body_base64": base64.b64encode(json.dumps(value).encode()).decode(),
        "error": None,
        **changes,
    }


class FakeClient:
    def __init__(self):
        self.calls = []
        self.repetitions = Counter()

    def exchange(self, path, payload=None):
        self.calls.append((path, payload))
        if path == "/api/version":
            value = {"version": "fixture"}
        elif path == "/api/tags":
            value = {
                "models": [
                    {"name": model, "digest": model + "-digest", "details": {}}
                    for model in config.MODELS
                ]
            }
        elif path == "/api/show":
            value = {"template": "fixture", "license": "Apache-2.0"}
        elif path == "/api/ps":
            value = {"models": []}
        elif "prompt" not in payload:
            value = {"done": True}
        else:
            key = (payload["model"], payload["prompt"])
            self.repetitions[key] += 1
            value = response(
                "No implementation",
                prompt_eval_count=31 if self.repetitions[key] == 1 else 1,
            )
        return envelope(value, path, payload)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://localhost:11434",
        "http://127.0.0.1@evil.com",
        "http://127.0.0.1/path",
        "http://user:pass@127.0.0.1",
        "http://127.0.0.1?x=1",
    ],
)
def test_transport_rejects_nonliteral_loopback_and_ambiguous_urls(url):
    with pytest.raises(ValueError):
        Client(url)


def test_request_has_every_fixed_option_and_no_history():
    value = generation_request(config.MODELS[0], "question", 0)
    assert value["options"] == {
        "temperature": 0,
        "seed": 1729,
        "num_predict": 768,
        "num_ctx": 4096,
        "num_thread": 8,
        "num_gpu": 0,
        "stop": [],
    }
    assert value["system"] == config.SYSTEM_PROMPT
    assert value["keep_alive"] == 0 and value["stream"] is False
    assert "context" not in value and "messages" not in value


@pytest.mark.parametrize("field", config.OLLAMA_RESPONSE_FIELDS)
@pytest.mark.parametrize("invalid", [None, True, -1, 1.5, "12"])
def test_bad_native_measurements_fail_closed(field, invalid):
    with pytest.raises(ValueError):
        decode_response(envelope(response(**{field: invalid})), generation=True)


def test_zero_cached_prompt_work_is_valid():
    assert (
        decode_response(
            envelope(response(prompt_eval_count=0, prompt_eval_duration=0)), generation=True
        )["prompt_eval_count"]
        == 0
    )


def test_transport_preserves_non_json_error_body(monkeypatch):
    class Reply:
        status = 500

        def __init__(self):
            self.parts = iter([b"not json\xff", b""])

        def read1(self, size):
            return next(self.parts)

    class Connection:
        sock = None

        def __init__(self, *args, **kwargs):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            return Reply()

        def close(self):
            pass

    monkeypatch.setattr(ollama.http.client, "HTTPConnection", Connection)
    raw = Client().exchange("/api/generate", {"prompt": "x"})
    assert base64.b64decode(raw["body_base64"]) == b"not json\xff"
    assert raw["http_status"] == 500
    with pytest.raises(ValueError, match="HTTP 500"):
        decode_response(raw)


def test_timeout_is_an_auditable_transport_record(monkeypatch):
    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, *args, **kwargs):
            raise TimeoutError("fixture deadline")

        def close(self):
            pass

    monkeypatch.setattr(ollama.http.client, "HTTPConnection", Connection)
    raw = Client().exchange("/api/generate", {"prompt": "x"})
    assert raw["error"]["type"] == "timeout"
    assert raw["body_base64"] == "" and raw["http_status"] is None


TASK = Task(
    "fixture",
    'def answer():\n    """Return one."""',
    "",
    "def check(candidate):\n    assert candidate() == 1",
    "answer",
)


@pytest.mark.parametrize(
    ("text", "changes", "expected"),
    [
        ("", {}, "no_code"),
        ("No thanks", {}, "no_code"),
        ("def other():\n    return 1", {}, "no_code"),
        ("def answer(:", {}, "syntax_error"),
        ("def answer():\n    return 1", {"done_reason": "length"}, "truncated"),
        ("def answer():\n    return 1", {"eval_count": 768}, "truncated"),
    ],
)
def test_failure_precedence_does_not_execute_invalid_output(monkeypatch, text, changes, expected):
    monkeypatch.setattr(evaluation, "run_solution", lambda *a: pytest.fail("Must not execute"))
    assert evaluation.evaluate(TASK, response(text, **changes))[0] == expected


@pytest.mark.parametrize(
    ("source", "failure"),
    [
        ("def answer():\n    return 1", ""),
        ("def answer():\n    return 2", "test_failed"),
        ("import os\ndef answer():\n    return 1", "policy_rejected"),
    ],
)
def test_live_sandbox_outcome_mapping(source, failure):
    assert evaluation.evaluate(TASK, response(source))[0] == failure


@pytest.mark.parametrize("status", ["timeout", "memory_limit", "infrastructure_error"])
def test_resource_status_mapping(monkeypatch, status):
    outcome = SandboxResult(status, "fixture reason", 1, 0, 1729)
    monkeypatch.setattr(evaluation, "run_solution", lambda *a: outcome)
    failure, reason, detail = evaluation.evaluate(TASK, response())
    assert (failure, reason, detail) == (status, "fixture reason", asdict(outcome))


def test_native_counts_rates_and_schema(monkeypatch):
    metadata = host_metadata()
    manifest = {"runtime": {"version": "fixture", "models": {"m": {"digest": "hash"}}}}
    job = {"run_id": "id", "model": "m", "task_id": "fixture", "prompt_id": "P0", "repeat": 1}
    monkeypatch.setattr(runner, "evaluate", lambda *a: ("", "", {}))
    record = runner.make_result(job, envelope(response(), session="s"), manifest, TASK, metadata)
    row = record["row"]
    assert list(row) == FIELDS
    assert row["input_tokens"] == 31 and row["output_tokens"] == 12
    assert row["tokens_per_second"] == 6 and row["wall_seconds"] == 3.1
    assert all(row[key] == "" for key in ENERGY_FIELDS)
    assert row["passed"] and row["difficulty_group"] == ""


def test_schema_matches_spec():
    text = (runner.DATA_DIR.parent / "docs/SPEC.md").read_text(encoding="utf-8")
    assert ", ".join(FIELDS) in text


def test_journal_reuses_response_without_a_second_call(tmp_path):
    client = FakeClient()
    journal = runner.Journal(tmp_path, client, "first")
    request = generation_request(config.MODELS[0], "question", -1)
    saved = journal.request("id", "scored", "/api/generate", request)
    restored = runner.Journal(tmp_path, client, "second")
    assert restored.request("id", "scored", "/api/generate", request) == saved
    assert len(client.calls) == 1
    with pytest.raises(ValueError, match="Changed request"):
        restored.request("id", "scored", "/api/generate", {})


def test_uncertain_inflight_request_never_regenerated(tmp_path):
    append_json(tmp_path / "requests.jsonl", {"request_id": "id"})
    with pytest.raises(RuntimeError, match="Uncertain in-flight"):
        runner.Journal(tmp_path, FakeClient(), "second")


@pytest.mark.parametrize("content", ['{"a":1}', "{bad}\n", "null\n"])
def test_damaged_journal_is_not_repaired(tmp_path, content):
    path = tmp_path / "raw.jsonl"
    path.write_text(content)
    with pytest.raises(ValueError):
        read_jsonl(path)
    assert path.read_text() == content


def test_immutable_file_and_concurrent_directory_lock(tmp_path):
    path = tmp_path / "manifest.json"
    write_once(path, {"seed": 1729})
    with pytest.raises(FileExistsError):
        write_once(path, {"seed": 1})
    with directory_lock(tmp_path), pytest.raises(RuntimeError, match="Another runner"):
        with directory_lock(tmp_path):
            pass


def test_schedule_covers_all_pairs_once_and_is_seeded():
    jobs = runner.smoke_schedule()
    assert jobs == runner.smoke_schedule()
    assert len(jobs) == 35
    assert len({(j["task_id"], j["prompt_id"]) for j in jobs}) == 35
    assert {j["model"] for j in jobs} == {config.MODELS[1]}


def test_offline_full_smoke_and_noop_resume(tmp_path):
    client = FakeClient()
    outcome = runner.run_smoke(tmp_path, client)
    assert outcome == {"completed": 35, "new_requests": 35, "keep_alive": 0}
    before = {p.name: p.read_bytes() for p in tmp_path.glob("*.json*")}
    calls = len(client.calls)
    assert runner.run_smoke(tmp_path, client) == {"completed": 35, "new_requests": 0}
    assert len(client.calls) == calls
    assert before == {p.name: p.read_bytes() for p in tmp_path.glob("*.json*")}
    raws = read_jsonl(tmp_path / "raw.jsonl")
    kinds = Counter(row["kind"] for row in raws)
    assert kinds["scored"] == 35 and kinds["determinism"] == 4 and kinds["warmup"] == 2
    assert all(row["request"]["keep_alive"] == 0 for row in raws if row["kind"] == "scored")
    rows = list(csv.DictReader((tmp_path / "results.csv").open(newline="")))
    assert len(rows) == 35 and all(row["failure_type"] == "no_code" for row in rows)
    assert all(row[key] == "" for row in rows for key in ENERGY_FIELDS)


def test_resume_after_saved_raw_does_not_regenerate(tmp_path, monkeypatch):
    original = runner.make_result
    counter = 0

    def interrupt(*args):
        nonlocal counter
        counter += 1
        if counter == 3:
            raise KeyboardInterrupt()
        return original(*args)

    client = FakeClient()
    monkeypatch.setattr(runner, "make_result", interrupt)
    with pytest.raises(KeyboardInterrupt):
        runner.run_smoke(tmp_path, client)
    assert len(result_index(tmp_path)) == 2
    monkeypatch.setattr(runner, "make_result", original)
    assert runner.run_smoke(tmp_path, client)["new_requests"] == 32
    scored = [row for row in read_jsonl(tmp_path / "raw.jsonl") if row["kind"] == "scored"]
    assert len(scored) == 35 and len(result_index(tmp_path)) == 35


def test_cache_policy_records_text_difference_and_reuse(tmp_path):
    client = FakeClient()
    journal = runner.Journal(tmp_path, client, "session")
    tasks = {task.task_id: task for task in runner.load_tasks()}
    policy = runner.resolve_cache(journal, tasks)
    assert policy["keep_alive"] == 0
    assert all(row["text_identical"] for row in policy["observations"])
    assert all(row["prompt_eval_count"] == [31, 1] for row in policy["observations"])
    calls = len(client.calls)
    assert runner.resolve_cache(journal, tasks)["keep_alive"] == 0
    assert len(client.calls) == calls
