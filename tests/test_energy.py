"""Synthetic analytic signals test units, interpolation, baseline and phase flags."""

from datetime import UTC, datetime

import pytest

from prompt_energy.energy import idle_baseline, integrate, request_energy
from prompt_energy.hwinfo import Sample


def signal(seconds=80, watts=10):
    return [Sample(i / 2, watts) for i in range(seconds * 2 + 1)]


def raw(start=1, end=10):
    return {
        "started_at": datetime.fromtimestamp(start, UTC).isoformat(),
        "ended_at": datetime.fromtimestamp(end, UTC).isoformat(),
        "wall_seconds": end - start,
    }


def durations(load=1, prompt=2, decode=6, total=9):
    return {
        "load_duration": int(load * 1e9),
        "prompt_eval_duration": int(prompt * 1e9),
        "eval_duration": int(decode * 1e9),
        "total_duration": int(total * 1e9),
    }


def test_constant_power_and_wh_conversion():
    value = integrate(signal(), 0, 60, 4)
    assert value["raw_wh"] == pytest.approx(10 * 60 / 3600)
    assert value["adjusted_wh"] == pytest.approx(6 * 60 / 3600)
    assert value["flags"] == []


def test_linear_signal_partial_boundaries_and_irregular_cadence():
    samples = [Sample(t, 2 * t + 3) for t in (0, 0.4, 1, 1.8, 2.3, 3, 4)]
    value = integrate(samples, 0.2, 3.7)
    exact = (3.7**2 + 3 * 3.7) - (0.2**2 + 3 * 0.2)
    assert value["raw_wh"] == pytest.approx(exact / 3600)


def test_baseline_is_time_weighted():
    samples = [Sample(i / 2, i / 2) for i in range(121)]
    samples.insert(1, Sample(0.01, 0.01))
    assert idle_baseline(samples, 0, 60)["watts"] == pytest.approx(30)
    with pytest.raises(ValueError, match="60 seconds"):
        idle_baseline(samples, 0, 59)


def test_negative_corrected_energy_is_retained():
    value = integrate(signal(), 0, 10, 20)
    assert value["adjusted_wh"] < 0
    assert "negative_adjusted_energy" in value["flags"]


@pytest.mark.parametrize(
    ("start", "end", "flag"),
    [
        (-1, 3, "missing_sensor_coverage"),
        (0, 90, "missing_sensor_coverage"),
        (2, 1, "invalid_window"),
    ],
)
def test_no_extrapolation_or_bad_windows(start, end, flag):
    value = integrate(signal(), start, end)
    assert value["raw_wh"] is None and flag in value["flags"]


def test_missing_sample_gap_is_not_bridged():
    value = integrate([Sample(0, 10), Sample(2, 10), Sample(3, 10)], 0.5, 2.5)
    assert "sensor_gap" in value["flags"] and value["raw_wh"] is None


def test_zero_duration_and_low_resolution():
    zero = integrate(signal(), 1, 1)
    assert zero["raw_wh"] == 0 and "low_resolution" in zero["flags"]
    assert "low_resolution" in integrate(signal(), 1, 3.9)["flags"]
    assert "low_resolution" not in integrate(signal(), 1, 4)["flags"]


def test_phase_windows_and_primary_energy():
    value = request_energy(signal(), raw(), durations(), 4)
    assert value["flags"] == []
    assert value["windows"]["total"]["adjusted_wh"] == pytest.approx(6 * 9 / 3600)
    assert value["windows"]["post_load"]["adjusted_wh"] == pytest.approx(6 * 8 / 3600)
    assert value["windows"]["prompt_eval"]["start"] == 2
    assert value["windows"]["decode"]["start"] == 4
    assert value["windows"]["decode"]["end"] == 10
    assert value["phase_residual_seconds"] == 0


def test_phase_mismatch_flags_without_changing_durations():
    value = request_energy(signal(), raw(), durations(total=10), 0)
    assert "phase_sum_mismatch" in value["flags"]
    assert value["phase_residual_seconds"] == 1
    assert value["wall_minus_api_seconds"] == -1


def test_outside_phase_is_not_clipped():
    value = request_energy(signal(), raw(), durations(decode=10), 0)
    assert value["windows"]["decode"]["raw_wh"] is None
    assert value["windows"]["decode"]["end"] == 14
    assert "outside_request" in value["windows"]["decode"]["flags"]


@pytest.mark.parametrize("bad", [None, {}, {"load_duration": -1}])
def test_missing_durations_keep_total_request(bad):
    value = request_energy(signal(), raw(), bad, 0)
    assert "invalid_api_durations" in value["flags"]
    assert value["windows"]["total"]["raw_wh"] is not None
    assert "post_load" not in value["windows"]


def test_clock_discrepancy_and_cached_tokens():
    envelope = {**raw(), "wall_seconds": 1}
    value = request_energy(signal(), envelope, {**durations(), "prompt_eval_cached_count": 10}, 0)
    assert {"clock_discrepancy", "cached_prompt_tokens"} <= set(value["flags"])
