"""Pilot acceptance is simulated: no model, real tracker, or real sensor is contacted."""

import base64
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from experiments import config
from experiments.run_p3 import main
from prompt_energy import pilot
from prompt_energy.carbon import CarbonMeter, MeasuredClient, carbon_adjusted
from prompt_energy.energy_report import energy_rows, export_energy, spread
from prompt_energy.hwinfo import LogFormat
from prompt_energy.records import read_jsonl, result_index


class Clock:
    def __init__(self, path):
        self.path = path
        self.value = 1792400000.0
        self.origin = self.value - 5
        self.sleeps = []
        self.write()

    def write(self):
        lines = ["Date,Time,CPU Package Power [W]"]
        for i in range(round((self.value - self.origin) * 2) + 1):
            instant = datetime.fromtimestamp(self.origin + i / 2, UTC)
            lines.append(instant.strftime("%d.%m.%Y,%H:%M:%S.%f") + ",10")
        self.path.write_text("\n".join(lines) + "\n")

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.value += seconds
        self.write()

    def now(self):
        return self.value


class FakeAPI:
    def __init__(self, clock):
        self.clock, self.calls = clock, []

    def exchange(self, path, payload=None):
        self.calls.append((path, payload))
        start = self.clock.now()
        if path == "/api/version":
            body = {"version": config.P3_PILOT["expected_runtime_version"]}
        elif path == "/api/tags":
            body = {
                "models": [
                    {"name": m, "digest": d, "details": {}}
                    for m, d in config.P3_PILOT["expected_model_digests"].items()
                ]
            }
        elif path == "/api/show":
            body = {"license": "fixture"}
        elif path == "/api/ps":
            body = {"models": []}
        elif "prompt" not in payload:
            body = {"done": True}
        else:
            self.clock.sleep(4)
            body = {
                "response": "No code",
                "done": True,
                "prompt_eval_count": 10,
                "eval_count": 2,
                "load_duration": 1_000_000_000,
                "prompt_eval_duration": 1_000_000_000,
                "eval_duration": 2_000_000_000,
                "total_duration": 4_000_000_000,
                "prompt_eval_cached_count": 0,
            }
        return {
            "path": path,
            "request": payload,
            "started_at": datetime.fromtimestamp(start, UTC).isoformat(),
            "ended_at": datetime.fromtimestamp(self.clock.now(), UTC).isoformat(),
            "wall_seconds": self.clock.now() - start,
            "http_status": 200,
            "error": None,
            "body_base64": base64.b64encode(json.dumps(body).encode()).decode(),
        }


class FakeMeter:
    def __init__(self, clock):
        self.clock, self.names = clock, []

    def start(self):
        pass

    def begin(self, name):
        self.names.append(name)
        self.beginning = self.clock.now()

    def end(self):
        seconds = self.clock.now() - self.beginning
        return {
            "raw_wh": seconds * 10 / 3600,
            "raw_co2e_kg": seconds * 0.0001,
            "seconds": seconds,
            "native": {"fixture": True},
        }

    def close(self):
        pass


@pytest.fixture
def simulation(tmp_path, monkeypatch):
    log = tmp_path / "sensor.csv"
    clock = Clock(log)
    api = FakeAPI(clock)
    meter = FakeMeter(clock)
    host = {
        "python": "3.13.7",
        "bits": 64,
        "ac_line_status": 1,
        "power_mode": "Best performance",
        "cpu_model": "fixture",
        "os": "Windows",
        "libraries": {"codecarbon": "3.0.4"},
    }
    monkeypatch.setattr(pilot, "host_metadata", lambda: host)
    monkeypatch.setattr(
        pilot,
        "P3_PILOT",
        {
            **config.P3_PILOT,
            "models": config.MODELS[:1],
            "task_ids": config.TASK_IDS[:1],
            "prompt_ids": ("P0",),
        },
    )
    args = dict(
        root=tmp_path / "pilot",
        log=log,
        fmt=LogFormat(utc_offset_minutes=0),
        hwinfo_version="fixture",
        owner_approved=True,
        client_factory=lambda: api,
        meter_factory=lambda: meter,
        sleep=clock.sleep,
        now=clock.now,
    )
    return args, api, meter, clock


def test_registered_sample_and_320_schedule():
    expected = tuple(
        sorted(random.Random(1729).sample(config.TASK_IDS, 20), key=lambda t: int(t.split("/")[1]))
    )
    assert config.P3_PILOT["task_ids"] == expected
    jobs = pilot.pilot_schedule()
    assert len(jobs) == 320 and jobs == pilot.pilot_schedule()
    assert len({(j["model"], j["prompt_id"], j["task_id"], j["repeat"]) for j in jobs}) == 320
    assert config.ENERGY["poll_seconds"] == 0.5
    assert config.ENERGY["phase_tolerance_seconds"] == 0.1
    assert config.ENERGY["phase_tolerance_fraction"] == 0.05


def test_approval_gate_before_any_side_effect(tmp_path):
    def forbidden():
        pytest.fail("Must not construct client or meter")

    with pytest.raises(PermissionError):
        pilot.run_pilot(
            tmp_path / "no-create",
            tmp_path / "absent",
            LogFormat(),
            "",
            client_factory=forbidden,
            meter_factory=forbidden,
        )
    assert not (tmp_path / "no-create").exists()


def test_cli_default_and_unapproved_pilot(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["run_p3"])
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["request_count"] == 320
    monkeypatch.setattr("sys.argv", ["run_p3", "pilot"])
    assert main() == 1 and "not approved" in capsys.readouterr().err


def test_simulated_pilot_energy_journals_gaps_and_noop_resume(simulation):
    args, api, meter, clock = simulation
    assert pilot.run_pilot(**args) == {"completed": 2, "new_requests": 2}
    rows = energy_rows(args["root"])
    assert len(rows) == 2
    assert all(r["failure_type"] == "no_code" and r["cpu_pkg_energy_wh"] == 0 for r in rows)
    assert all(r["record_kind"] == "pilot" and not r["include_in_main_analysis"] for r in rows)
    assert all(r["energy_tool"] == "HWiNFO" and r["load_seconds"] == 1 for r in rows)
    assert 60 in clock.sleeps and clock.sleeps.count(5) >= 3
    assert len(meter.names) == 3  # baseline + two requests, never warm-up
    before = {p.name: p.read_bytes() for p in args["root"].glob("*.json*")}
    calls = len(api.calls)
    assert pilot.run_pilot(**args) == {"completed": 2, "new_requests": 0}
    assert len(api.calls) == calls
    assert before == {p.name: p.read_bytes() for p in args["root"].glob("*.json*")}
    summary = export_energy(args["root"])
    assert summary["repeat_noise_primary_post_load_wh"][0]["complete_pair"]


def test_saved_raw_is_reused_after_interruption(simulation, monkeypatch):
    args, api, _, _ = simulation
    original = pilot._finish_run
    monkeypatch.setattr(
        pilot, "_finish_run", lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt())
    )
    with pytest.raises(KeyboardInterrupt):
        pilot.run_pilot(**args)
    assert len(result_index(args["root"])) == 0
    monkeypatch.setattr(pilot, "_finish_run", original)
    assert pilot.run_pilot(**args)["new_requests"] == 1
    raw = read_jsonl(args["root"] / "raw.jsonl")
    assert sum(r["kind"] == "pilot_scored" for r in raw) == 2


def test_bad_preflight_makes_no_model_call(simulation):
    args, api, _, _ = simulation
    args["log"].write_text("bad csv\n")
    with pytest.raises(ValueError):
        pilot.run_pilot(**args)
    assert api.calls == []


def test_sensor_loss_retains_answer_and_missing_energy(simulation, monkeypatch):
    args, _, _, _ = simulation
    original = pilot.capture_log
    calls = 0

    def fail_after_baseline(*a, **kw):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise ValueError("fixture sensor stopped")
        return original(*a, **kw)

    monkeypatch.setattr(pilot, "capture_log", fail_after_baseline)
    with pytest.raises(RuntimeError, match="sensor"):
        pilot.run_pilot(**args)
    rows = energy_rows(args["root"])
    assert len(rows) == 1 and rows[0]["cpu_pkg_energy_wh"] is None
    assert "sensor_unavailable" in rows[0]["energy_flags"]


def test_report_rejects_smoke(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"milestone": "P2 smoke"}))
    with pytest.raises(ValueError, match="smoke"):
        energy_rows(tmp_path)


def test_dispersion_sample_sd_and_missing_values():
    assert spread([1, 3])["sd"] == pytest.approx(2**0.5)
    assert spread([])["mean"] is None
    assert spread([2])["sd"] is None


def test_carbon_units_and_own_baseline():
    value = carbon_adjusted(
        {"raw_wh": 3, "raw_co2e_kg": 0.3, "seconds": 30},
        {"raw_wh": 2, "raw_co2e_kg": 0.2, "seconds": 60},
    )
    assert value["adjusted_wh"] == 2 and value["idle_w"] == 120
    assert value["co2e_kg"] == pytest.approx(0.2)
    assert carbon_adjusted(None, None)["adjusted_wh"] is None


def test_carbon_adapter_is_offline_machine_mode_and_keeps_native_data():
    @dataclass
    class Data:
        energy_consumed: float = 0.001
        emissions: float = 0.2
        duration: float = 10

    class Tracker:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def start(self):
            pass

        def start_task(self, name):
            pass

        def stop_task(self, name):
            return Data()

        def stop(self):
            pass

    meter = CarbonMeter(Tracker)
    assert meter.tracker.kwargs["tracking_mode"] == "machine"
    assert not meter.tracker.kwargs["save_to_api"]
    assert not meter.tracker.kwargs["save_to_logfire"]
    assert type(meter.tracker.kwargs["pue"]) is float
    meter.start()
    meter.begin("a")
    result = meter.end()
    meter.close()
    assert result["raw_wh"] == 1 and result["native"]["energy_consumed"] == 0.001


def test_secondary_failure_does_not_lose_raw_response(simulation):
    _, api, meter, _ = simulation

    def fail(_):
        raise RuntimeError("fixture")

    meter.begin = fail
    client = MeasuredClient(api, meter)
    client.next_task = "test"
    raw = client.exchange("/api/generate", {"prompt": "test"})
    assert raw["body_base64"] and "fixture" in raw["codecarbon_error"]
