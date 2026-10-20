import json

import numpy as np
import pandas as pd
import pytest

from analysis.full_analysis import (
    GROSS,
    NET,
    analyze,
    bootstrap_mean,
    grouped_summaries,
    load_full,
    noise_rows,
    per_correct,
    regression,
    summarize_stage1,
)


def fixture_rows():
    return pd.DataFrame(
        [
            {
                "run_id": f"f{i}",
                "task_id": f"t{i}",
                "stage": 1,
                "repeat": 1,
                "model": "fixture",
                "prompt_id": "P0" if i % 2 else "P1",
                "record_kind": "full",
                "passed": i % 2 == 0,
                "failure_type": "" if i % 2 == 0 else "test_failed",
                "input_tokens": i * i,
                "output_tokens": i,
                "load_seconds": 0.5 + i / 10,
                NET: 1 + 2 * i * i + 3 * i,
                GROSS: 2 + 3 * i * i + 4 * i,
                "energy_flags": "",
            }
            for i in range(8)
        ]
    )


def test_bootstrap_reproducible_missing_and_zero_success():
    result = bootstrap_mean(np.array([1.0, 2.0, 3.0, np.nan]), seed=1729, draws=100)
    assert result == bootstrap_mean(np.array([1.0, 2.0, 3.0, np.nan]), seed=1729, draws=100)
    assert result["n"] == 3 and result["mean"] == 2
    assert bootstrap_mean(np.array([np.nan]), seed=1, draws=10)["mean"] is None
    assert per_correct(np.array([1, 2]), np.array([True, False])) == 3
    assert per_correct(np.array([1, 2]), np.array([False, False])) is None
    assert per_correct(np.array([1, np.nan]), np.array([True, False])) is None


def test_joint_regression_and_rank_deficiency():
    frame = fixture_rows()
    fit, residual = regression(frame)
    assert fit["r_squared"] == pytest.approx(1)
    assert fit["input_token_coefficient"] == pytest.approx(2)
    assert fit["output_token_coefficient"] == pytest.approx(3)
    assert np.max(np.abs(residual["residual_wh"])) < 1e-10
    frame["input_tokens"] = frame["output_tokens"]
    assert regression(frame)[0]["status"] == "insufficient_data_or_rank"


def test_stage_separation_and_groups():
    frame = fixture_rows()
    grouped, status = grouped_summaries(frame, {}, 20)
    assert grouped == {} and "unavailable" in status["calibration"]
    labels = dict.fromkeys(frame["task_id"], "easy")
    grouped, _ = grouped_summaries(frame, {"calibration": labels}, 20)
    assert set(grouped["calibration"]["prompt_id"]) == {"P1"}
    frame.loc[0, "stage"] = 2
    with pytest.raises(ValueError, match="pool"):
        summarize_stage1(frame, draws=20)


def test_noise_only_extra_repeats():
    frame = fixture_rows().iloc[:2].copy()
    frame["stage"] = 2
    frame["task_id"] = "same"
    frame["prompt_id"] = "P1"
    frame["repeat"] = [2, 3]
    assert noise_rows(frame).iloc[0]["absolute_repeat_difference_wh"] == 5
    frame.loc[frame.index[0], NET] = np.nan
    assert noise_rows(frame).iloc[0]["energy_available"] == 1


def test_analysis_rejects_pilot(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"milestone": "P3 pilot"}))
    with pytest.raises(ValueError, match="excluded"):
        load_full(tmp_path)


def test_scaffolds_use_synthetic_full_data_without_mutation(tmp_path, monkeypatch):
    from analysis import full_analysis

    root = tmp_path / "run"
    root.mkdir()
    frame = fixture_rows()
    frame.to_csv(root / "full.csv", index=False)
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "milestone": "P4 full",
                "schedule": frame.to_dict("records"),
                "grouping": {},
            }
        )
    )
    before = (root / "full.csv").read_bytes()
    monkeypatch.setattr(full_analysis, "figures", lambda *a: None)
    report = analyze(root, tmp_path / "analysis", draws=20)
    assert report["stage1_rows"] == 8 and report["stage2_rows"] == 0
    assert (root / "full.csv").read_bytes() == before
    assert (tmp_path / "analysis/all_rows/summary.csv").exists()
    loads = pd.read_csv(tmp_path / "analysis/load-duration-summary.csv")
    assert loads["available"].sum() == 8
    assert loads["mean"].mean() == pytest.approx(0.85)
