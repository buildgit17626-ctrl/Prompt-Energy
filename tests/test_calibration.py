"""Calibration correctness and resume without contacting Ollama."""

from types import SimpleNamespace

import pytest
from test_p3 import Clock, FakeAPI

from experiments import config
from prompt_energy import calibration
from prompt_energy.records import read_jsonl


def test_frozen_reference_lengths_and_schedule():
    result = calibration.reference_lengths()
    assert result["labels"] == config.P4_GROUPING["reference_length"]
    assert result["counts"] == config.P4_GROUPING["reference_length_counts"]
    assert result["median"] == 6
    assert list(result["labels"].values()).count("short") == 21
    jobs = calibration.schedule()
    assert len(jobs) == 40 and [j["task_id"] for j in jobs] == list(config.TASK_IDS)
    assert all(j["prompt_id"] == "P0" and j["repeat"] == 1 for j in jobs)


def test_length_comments_and_median_ties(monkeypatch):
    tasks = [
        SimpleNamespace(task_id="a", canonical_solution="\n # comment\n return 1 # inline\n"),
        SimpleNamespace(task_id="b", canonical_solution="x = 1\nreturn x\n"),
        SimpleNamespace(task_id="c", canonical_solution="x = 1\nreturn x\n"),
    ]
    monkeypatch.setattr(calibration, "load_tasks", lambda: tasks)
    result = calibration.reference_lengths()
    assert result["counts"] == {"a": 1, "b": 2, "c": 2}
    assert set(result["labels"].values()) == {"short"}


@pytest.fixture
def simulated(tmp_path, monkeypatch):
    api = FakeAPI(Clock(tmp_path / "unused-synthetic-clock.csv"))
    jobs = calibration.schedule()[:2]
    monkeypatch.setattr(calibration, "schedule", lambda: jobs)
    monkeypatch.setattr(
        calibration,
        "host_metadata",
        lambda: {
            "python": "3.13.7",
            "bits": 64,
            "ac_line_status": 1,
            "power_mode": "Best performance",
            "cpu_model": "fixture",
            "os": "Windows",
            "libraries": {"codecarbon": "3.0.4"},
        },
    )
    return tmp_path / "run", api


def test_gate_no_side_effects(tmp_path):
    with pytest.raises(PermissionError):
        calibration.run(tmp_path / "absent")
    assert not (tmp_path / "absent").exists()


def test_main_run_requires_frozen_calibration(tmp_path, monkeypatch):
    from prompt_energy.full_run import run_block
    from prompt_energy.hwinfo import LogFormat

    monkeypatch.setitem(config.P4_GROUPING, "calibration", {})
    with pytest.raises(ValueError, match="both complete"):
        run_block(
            tmp_path / "absent",
            tmp_path / "missing.csv",
            LogFormat(),
            "fixture",
            owner_approved=True,
        )
    assert not (tmp_path / "absent").exists()


def test_complete_resume_labels_and_no_energy(simulated):
    root, api = simulated
    assert calibration.run(root, approved=True, client_factory=lambda: api)["new_requests"] == 2
    result = calibration.labels(root)
    assert set(result["labels"].values()) == {"failed"}
    before = (root / "raw.jsonl").read_bytes()
    api.calls.clear()
    assert calibration.run(root, approved=True, client_factory=lambda: api)["new_requests"] == 0
    assert not api.calls and (root / "raw.jsonl").read_bytes() == before
    assert all(a["row"]["cpu_pkg_energy_wh"] == "" for a in read_jsonl(root / "results.jsonl"))
    assert not (root / "measurements.jsonl").exists()


def test_recovery_after_raw_response(simulated, monkeypatch):
    root, api = simulated
    original = calibration.make_result

    def interrupt(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(calibration, "make_result", interrupt)
    with pytest.raises(KeyboardInterrupt):
        calibration.run(root, approved=True, client_factory=lambda: api)
    with pytest.raises(ValueError, match="incomplete"):
        calibration.labels(root)
    monkeypatch.setattr(calibration, "make_result", original)
    assert calibration.run(root, approved=True, client_factory=lambda: api)["new_requests"] == 1
    raw = [r for r in read_jsonl(root / "raw.jsonl") if r["kind"] == "calibration"]
    assert len(raw) == 2


def test_changed_registration_rejected(simulated, monkeypatch):
    root, api = simulated
    calibration.run(root, approved=True, client_factory=lambda: api)
    api.calls.clear()
    monkeypatch.setattr(calibration, "registration", lambda: {})
    with pytest.raises(ValueError, match="registration"):
        calibration.run(root, approved=True, client_factory=lambda: api)
    assert not api.calls
