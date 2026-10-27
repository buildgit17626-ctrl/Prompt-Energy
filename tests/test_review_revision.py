"""Check the requested estimands and paired bootstrap safeguards."""

import numpy as np
import pandas as pd
import pytest

from analysis.review_revision import baseline_scenarios, paired_contrast, ratio_interval


def test_ratio_uses_all_attempts_and_joint_outcomes() -> None:
    result = ratio_interval(np.array([1.0, 3.0] * 20), np.array([True, False] * 20))
    assert result["value"] == 4
    assert result["low"] < 4 < result["high"]
    assert result["zero_success_draws"] == 0
    assert result == ratio_interval(np.array([1.0, 3.0] * 20), np.array([True, False] * 20))


def test_undefined_ratio_draws_and_missing_energy_not_hidden() -> None:
    result = ratio_interval(np.ones(2), np.array([True, False]))
    assert result["zero_success_draws"] > 0
    assert np.isnan(result["low"])
    assert np.isnan(ratio_interval(np.ones(2), np.zeros(2, bool))["value"])
    with pytest.raises(ValueError):
        ratio_interval(np.array([1.0, np.nan]), np.ones(2, bool))


def test_pairing_uses_task_identity_and_discordance() -> None:
    frame = pd.DataFrame(
        {
            "task_id": ["b", "a", "a", "b"],
            "prompt_id": ["P1", "P0", "P1", "P0"],
            "cpu_pkg_energy_wh": [3.0, 10.0, 11.0, 2.0],
            "passed": [False, False, True, True],
        }
    )
    result = paired_contrast(frame, "P1", "P0")
    assert result["net_low_wh"] == result["net_high_wh"] == 1
    assert result["a_only_pass"] == result["b_only_pass"] == 1
    assert result["pass_difference"] == 0
    with pytest.raises(ValueError, match="Incomplete"):
        paired_contrast(frame.iloc[:-1], "P1", "P0")
    with pytest.raises(ValueError, match="Duplicate"):
        paired_contrast(pd.concat([frame, frame.iloc[:1]]), "P1", "P0")


def test_alternative_baselines_use_post_load_and_preserve_source() -> None:
    frame = pd.DataFrame(
        {
            "post_load_seconds": [10.0],
            "cpu_pkg_post_load_raw_wh": [0.1],
            "idle_baseline_w": [20.0],
            "end_idle_baseline_w": [10.0],
        }
    )
    result = baseline_scenarios(frame)
    assert result.net_end_wh.iloc[0] == pytest.approx(0.1 - 10 * 10 / 3600)
    assert result.net_midpoint_wh.iloc[0] == pytest.approx(0.1 - 15 * 10 / 3600)
    assert "net_end_wh" not in frame
