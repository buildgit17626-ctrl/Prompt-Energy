"""Offline P4 acceptance: synthetic sensors and fake API only."""

import builtins
import json
import random

import pytest
from test_p3 import Clock, FakeAPI

from experiments import config
from experiments.run_p4 import main
from prompt_energy import full_run
from prompt_energy.full_energy import drift, full_rows
from prompt_energy.hwinfo import LogFormat
from prompt_energy.records import read_jsonl


@pytest.fixture
def full_simulation(tmp_path, monkeypatch):
    monkeypatch.setitem(config.P4_GROUPING, "calibration", dict.fromkeys(config.TASK_IDS, "solved"))
    clock = Clock(tmp_path / "power.csv")
    api = FakeAPI(clock)
    host = {
        "python": "3.13.7",
        "bits": 64,
        "ac_line_status": 1,
        "power_mode": "Best performance",
        "cpu_model": "fixture",
        "os": "Windows",
        "libraries": {"codecarbon": "3.0.4"},
    }
    monkeypatch.setattr(full_run, "host_metadata", lambda: host)
    jobs = [
        {
            "run_id": f"full-{i:04d}",
            "model": config.MODELS[0],
            "task_id": config.TASK_IDS[0],
            "prompt_id": "P0",
            "repeat": i + 1,
            "stage": 1 if i == 0 else 2,
        }
        for i in range(3)
    ]
    monkeypatch.setattr(full_run, "full_schedule", lambda: jobs)
    return (
        {
            "root": tmp_path / "full",
            "log": clock.path,
            "fmt": LogFormat(utc_offset_minutes=0),
            "hwinfo_version": "fixture",
            "owner_approved": True,
            "client_factory": lambda: api,
            "sleep": clock.sleep,
            "now": clock.now,
            "monotonic": clock.now,
        },
        clock,
        api,
    )


def test_schedule_registered_560_plus_280():
    jobs = full_run.full_schedule()
    assert len(jobs) == 840
    assert sum(j["stage"] == 1 for j in jobs) == 560
    assert all(j["stage"] == 1 for j in jobs[:560])
    assert len({(j["model"], j["task_id"], j["prompt_id"], j["repeat"]) for j in jobs}) == 840
    assert jobs == full_run.full_schedule()
    subset = tuple(
        sorted(random.Random(1729).sample(config.TASK_IDS, 10), key=lambda s: int(s.split("/")[1]))
    )
    assert config.P4["stage2_task_ids"] == subset
    assert set(j["task_id"] for j in jobs[560:]) == set(subset)


def test_gate_and_safe_default(tmp_path, monkeypatch, capsys):
    def forbidden():
        pytest.fail("Unapproved must not construct client")

    with pytest.raises(PermissionError):
        full_run.run_block(
            tmp_path / "absent", tmp_path / "log", LogFormat(), "", client_factory=forbidden
        )
    assert not (tmp_path / "absent").exists()
    monkeypatch.setattr("sys.argv", ["run_p4"])
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["request_count"] == 840
    monkeypatch.setattr("sys.argv", ["run_p4", "run-block"])
    assert main() == 1 and "not approved" in capsys.readouterr().err


def test_complete_no_carbon_endpoints_and_noop(full_simulation, monkeypatch):
    args, clock, api = full_simulation
    original = builtins.__import__

    def guarded(name, *a, **kw):
        if name.startswith("codecarbon"):
            pytest.fail("P4 must not import CodeCarbon")
        return original(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", guarded)
    assert full_run.run_block(**args)["completed"] == 3
    assert clock.sleeps.count(60) == 2
    rows = full_rows(args["root"])
    assert len(rows) == 3 and all(r["cpu_pkg_energy_wh"] == 0 for r in rows)
    assert [r["include_in_main_analysis"] for r in rows] == [True, False, False]
    assert all(r["end_idle_baseline_w"] == 10 for r in rows)
    assert not any("phase" in k or "codecarbon" in k for k in rows[0])
    before = {p.name: p.read_bytes() for p in args["root"].glob("*.json*")}
    calls = len(api.calls)
    assert full_run.run_block(**args) == {"completed": 3, "new_requests": 0, "remaining": 0}
    assert len(api.calls) == calls
    assert before == {p.name: p.read_bytes() for p in args["root"].glob("*.json*")}


def test_boundary_and_drift():
    assert full_run.launch_allowed(10799)
    assert not full_run.launch_allowed(10800)
    assert not full_run.launch_allowed(14400)
    assert drift(10, 11) == (1, [])
    assert drift(10, 11.01)[1] == ["baseline_drift"]
    assert drift(20, 17)[0] == -3
    assert drift(20, None)[1] == ["end_baseline_missing"]


def test_short_block_closes_baseline_and_resume(full_simulation, monkeypatch):
    args, _, _ = full_simulation
    # Start after warm-up/baseline; launch one request, then close this short fake block.
    monkeypatch.setattr(full_run, "P4", {**config.P4, "stop_launch_seconds": 80})
    first = full_run.run_block(**args)
    assert first["block_status"] == "time_limit"
    assert first["new_requests"] == 1
    assert first["end_baseline_available"]
    monkeypatch.setattr(full_run, "P4", config.P4)
    second = full_run.run_block(**args)
    assert second["new_requests"] == 2
    assert len(read_jsonl(args["root"] / "blocks.jsonl")) == 4


def test_saved_response_recovered_no_duplicate(full_simulation, monkeypatch):
    args, _, _ = full_simulation
    original = full_run.finish_saved
    monkeypatch.setattr(
        full_run, "finish_saved", lambda *a, **kw: (_ for _ in ()).throw(KeyboardInterrupt())
    )
    with pytest.raises(KeyboardInterrupt):
        full_run.run_block(**args)
    monkeypatch.setattr(full_run, "finish_saved", original)
    result = full_run.run_block(**args)
    assert result["new_requests"] == 2
    assert sum(r["kind"] == "full_scored" for r in read_jsonl(args["root"] / "raw.jsonl")) == 3


def test_missing_end_preserves_scored_rows(full_simulation, monkeypatch):
    args, _, _ = full_simulation
    original = full_run.baseline
    calls = 0

    def missing_end(*a, **kw):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise ValueError("fixture stopped logging")
        return original(*a, **kw)

    monkeypatch.setattr(full_run, "baseline", missing_end)
    result = full_run.run_block(**args)
    assert not result["end_baseline_available"]
    assert all("end_baseline_missing" in r["energy_flags"] for r in full_rows(args["root"]))


def test_bad_preflight_no_request(full_simulation):
    args, _, api = full_simulation
    args["log"].write_text("not a csv\n")
    with pytest.raises(ValueError):
        full_run.run_block(**args)
    assert not api.calls


def test_changed_registration_rejected(full_simulation, monkeypatch):
    args, _, api = full_simulation
    full_run.run_block(**args)
    calls = len(api.calls)
    monkeypatch.setattr(full_run, "registration", lambda: {"changed": "yes"})
    with pytest.raises(ValueError, match="registration"):
        full_run.run_block(**args)
    assert len(api.calls) == calls


def test_transport_failure_saved_without_false_idle(full_simulation, monkeypatch):
    args, _, api = full_simulation
    exchange = api.exchange

    def failed(path, payload=None):
        raw = exchange(path, payload)
        if payload and "Task:" in payload.get("prompt", ""):
            raw["error"] = {"type": "timeout", "detail": "fixture HTTP deadline"}
        return raw

    monkeypatch.setattr(api, "exchange", failed)
    with pytest.raises(RuntimeError, match="Transport"):
        full_run.run_block(**args)
    rows = full_rows(args["root"])
    assert len(rows) == 1 and rows[0]["failure_type"] == "timeout"
    assert rows[0]["cpu_pkg_energy_wh"] is None
    assert "end_baseline_missing" in rows[0]["energy_flags"]
    assert api.calls[-1][1]["prompt"].find("Task:") >= 0


def test_uncertain_intent_never_regenerated(full_simulation):
    from prompt_energy.records import append_json

    args, _, api = full_simulation
    args["root"].mkdir()
    append_json(
        args["root"] / "requests.jsonl",
        {
            "request_id": "full-0000",
            "path": "/api/generate",
            "request": {},
        },
    )
    with pytest.raises(RuntimeError, match="Uncertain"):
        full_run.run_block(**args)
    assert not api.calls


def test_ceiling_overrun_stops_and_flags_missing_idle(full_simulation, monkeypatch):
    args, clock, _ = full_simulation
    original = full_run.finish_saved
    jumped = False

    def jump_after_save(*a, **kw):
        nonlocal jumped
        result = original(*a, **kw)
        jumped = True
        return result

    args["monotonic"] = lambda: clock.now() + (15000 if jumped else 0)
    monkeypatch.setattr(full_run, "finish_saved", jump_after_save)
    result = full_run.run_block(**args)
    assert result["new_requests"] == 1 and not result["end_baseline_available"]
    assert "block_ceiling_exceeded" in full_rows(args["root"])[0]["energy_flags"]
