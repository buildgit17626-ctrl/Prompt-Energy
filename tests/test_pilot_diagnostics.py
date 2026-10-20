import numpy as np
import pandas as pd
import pytest

from analysis.pilot_diagnostics import (
    GROSS,
    NET,
    diagnose,
    linear_fit,
    matched_contrasts,
    repeat_differences,
)


def test_linear_fit_and_missing_values():
    fit = linear_fit(np.array([1, 2, 3, 4.0]), np.array([3, 5, 7, np.nan]))
    assert fit["n"] == 3
    assert fit["slope"] == pytest.approx(2)
    assert fit["intercept"] == pytest.approx(1)
    assert fit["r_squared"] == pytest.approx(1)
    assert linear_fit(np.ones(3), np.arange(3.0))["slope"] is None


def test_repeat_and_task_matched_contrast():
    frame = pd.DataFrame(
        [
            {"model": "a", "task_id": "t", "prompt_id": arm, "repeat": repeat, NET: energy}
            for arm, repeat, energy in (("P0", 1, 1), ("P0", 2, 3), ("P1", 1, 5), ("P1", 2, 7))
        ]
    )
    assert repeat_differences(frame) == [2, 2]
    assert matched_contrasts(frame)[0]["mean_signed_b_minus_a_wh"] == 4
    frame.loc[0, NET] = np.nan
    assert repeat_differences(frame) == [2]
    assert matched_contrasts(frame) == []


def test_sensitivity_uses_primary_flag_and_preserves_missing_counts():
    frame = pd.DataFrame(
        [
            {
                "model": "a",
                "task_id": "t",
                "prompt_id": "P0",
                "repeat": i + 1,
                "output_tokens": 10 * (i + 1),
                NET: energy,
                GROSS: energy,
                "energy_flags": flags,
            }
            for i, (energy, flags) in enumerate(
                [
                    (1.0, "prompt_eval:low_resolution"),
                    (2.0, "post_load:low_resolution"),
                    (np.nan, "post_load:sensor_gap"),
                ]
            )
        ]
    )
    report = diagnose(frame)
    assert report["all_available"]["a"]["rows"] == 3
    assert report["exclude_primary_low_resolution"]["a"]["rows"] == 2
    assert report["exclude_primary_low_resolution"]["a"]["missing_net"] == 1
