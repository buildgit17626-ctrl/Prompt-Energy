"""Test research-relevant aggregation rules, not plotting implementation details."""

import numpy as np
import pandas as pd
import pytest

from analysis.comparisons import check_summary, leaders, summarize


def sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "stage": [1, 1, 2],
            "task_id": ["a", "b", "a"],
            "model": ["small"] * 3,
            "prompt_id": ["P1"] * 3,
            "passed": [True, False, True],
            "input_tokens": [10, 20, 1000],
            "output_tokens": [5, 25, 1000],
            "cpu_pkg_energy_wh": [1.0, 3.0, 999.0],
            "cpu_pkg_post_load_raw_wh": [2.0, 5.0, 999.0],
        }
    )


def test_summary_separates_stages_and_includes_failed_cost() -> None:
    row = summarize(sample()).iloc[0]
    assert row.rows == 2
    assert row.successes == row.failures == 1
    assert row.passed_mean == 0.5
    assert row.cpu_pkg_energy_wh_per_correct == 4
    assert row.output_tokens_per_correct == 30


def test_missing_cost_and_zero_success_have_no_per_correct_ratio() -> None:
    data = sample()
    data.loc[0, "cpu_pkg_energy_wh"] = np.nan
    row = summarize(data).iloc[0]
    assert row.cpu_pkg_energy_wh_n == 1
    assert np.isnan(row.cpu_pkg_energy_wh_per_correct)
    data["passed"] = False
    assert np.isnan(summarize(data).iloc[0].output_tokens_per_correct)


def test_duplicate_task_and_changed_registered_summary_rejected() -> None:
    data = sample()
    with pytest.raises(ValueError, match="Duplicate"):
        summarize(pd.concat([data, data.iloc[[0]]]))
    result = summarize(data)
    changed = result.copy()
    changed["output_tokens_mean"] += 1
    with pytest.raises(ValueError, match="mismatch"):
        check_summary(result, changed)


def test_metric_leaders_retain_ties_and_pending_approval() -> None:
    a = summarize(sample())
    b = a.assign(prompt_id="P5")
    table = leaders(pd.concat([a, b]))
    assert table.arms.eq("P1, P5").all()
    assert table.status.eq("OWNER REVIEW PENDING").all()
