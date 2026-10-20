"""Read-only pilot diagnostics; no hypothesis testing or modification of source data."""

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

NET = "cpu_pkg_energy_wh"
GROSS = "cpu_pkg_post_load_raw_wh"
LOW_RES = "post_load:low_resolution"


def linear_fit(x: np.ndarray, y: np.ndarray) -> dict:
    """Descriptive least squares with an intercept; undefined fits remain missing."""
    good = np.isfinite(x) & np.isfinite(y)
    x, y = x[good], y[good]
    result = {"n": len(x), "slope": None, "intercept": None, "r_squared": None}
    if len(x) < 2 or np.ptp(x) == 0:
        return result
    slope, intercept = np.linalg.lstsq(np.column_stack([x, np.ones(len(x))]), y, rcond=None)[0]
    residual = np.sum((y - (slope * x + intercept)) ** 2)
    total = np.sum((y - y.mean()) ** 2)
    return {
        **result,
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(1 - residual / total) if total > 0 else None,
    }


def distribution(values: list[float]) -> dict:
    """Finite-only descriptive spread, with explicit counts and no inference."""
    data = np.asarray(values, dtype=float)
    data = data[np.isfinite(data)]
    return {
        "n": len(data),
        "median": float(np.median(data)) if len(data) else None,
        "p90": float(np.quantile(data, 0.9)) if len(data) else None,
    }


def repeat_differences(frame: pd.DataFrame) -> list[float]:
    """Use complete repeat 1/2 pairs, preserving missingness instead of zero filling."""
    values = []
    for _, group in frame.groupby(["model", "prompt_id", "task_id"]):
        if len(group) == 2 and set(group["repeat"]) == {1, 2} and group[NET].notna().all():
            values.append(float(abs(group[NET].iloc[1] - group[NET].iloc[0])))
    return values


def matched_contrasts(frame: pd.DataFrame) -> list[dict]:
    """Compare arm means on matched tasks with two available repeats in each arm."""
    grouped = frame.groupby(["task_id", "prompt_id"])[NET].agg(["count", "mean"])
    complete = grouped[grouped["count"] == 2]["mean"].unstack("prompt_id")
    output = []
    for a, b in combinations(sorted(frame["prompt_id"].unique()), 2):
        if a not in complete or b not in complete:
            continue
        pairs = complete[[a, b]].dropna()
        delta = pairs[b] - pairs[a]
        output.append(
            {
                "arms": [a, b],
                "matched_tasks": len(delta),
                "mean_signed_b_minus_a_wh": float(delta.mean()) if len(delta) else None,
                "absolute_task_contrast_wh": distribution(delta.abs().tolist()),
            }
        )
    return output


def diagnose(frame: pd.DataFrame) -> dict:
    """Retain failures; show all-available and primary-resolution sensitivity separately."""
    result = {}
    low = frame["energy_flags"].fillna("").str.split(";").apply(lambda f: LOW_RES in f)
    for name, subset in (("all_available", frame), ("exclude_primary_low_resolution", frame[~low])):
        models = {}
        for model, group in subset.groupby("model"):
            models[model] = {
                "rows": len(group),
                "missing_net": int(group[NET].isna().sum()),
                "net_vs_output": linear_fit(
                    group["output_tokens"].to_numpy(), group[NET].to_numpy()
                ),
                "gross_vs_output": linear_fit(
                    group["output_tokens"].to_numpy(), group[GROSS].to_numpy()
                ),
                "absolute_repeat_difference_wh": distribution(repeat_differences(group)),
                "matched_arm_contrasts": matched_contrasts(group),
            }
        result[name] = models
    return result


def plot(frame: pd.DataFrame, destination: Path) -> None:
    """Export shareable scientific figures, labelled diagnostic and measurement mode."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    models = sorted(frame["model"].unique())
    fig, axes = plt.subplots(2, len(models), figsize=(11, 7.6), squeeze=False)
    colors = {"P0": "#0072B2", "P1": "#009E73", "P2": "#D55E00", "P4": "#CC79A7"}
    for column, model in enumerate(models):
        group = frame[frame["model"] == model]
        for row, (field, label) in enumerate(((NET, "Net"), (GROSS, "Gross"))):
            ax = axes[row, column]
            for arm, points in group.groupby("prompt_id"):
                ax.scatter(
                    points["output_tokens"],
                    points[field],
                    s=20,
                    alpha=0.65,
                    color=colors[arm],
                    label=arm,
                    edgecolors="none",
                )
            fit = linear_fit(group["output_tokens"].to_numpy(), group[field].to_numpy())
            if fit["slope"] is not None:
                x = np.array([group["output_tokens"].min(), group["output_tokens"].max()])
                ax.plot(x, fit["slope"] * x + fit["intercept"], color="#333333", linewidth=1)
            r2 = fit["r_squared"]
            ax.set_title(f"{model}\n{label}: n={fit['n']}, descriptive R²={r2:.3f}")
            ax.set_xlabel("Output tokens (Ollama API)")
            ax.set_ylabel(f"{label} post-load CPU package energy (Wh)")
            ax.grid(alpha=0.15)
    axes[0, 0].legend(title="Prompt arm", fontsize=8)
    fig.suptitle("Pilot, diagnostic — energy versus output tokens", fontsize=16)
    fig.text(
        0.5,
        0.015,
        "HWiNFO CPU Package Power • trapezoidal integration • approximate post-load window\n"
        "Net subtracts measured idle 15.4201 W; gross does not. "
        "319/320 available; low-resolution rows retained; failures included.\n"
        "Pilot excluded from hypothesis tests. Lines are descriptive, not causal.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.105, 1, 0.94))
    for extension in ("png", "pdf"):
        fig.savefig(destination / f"energy-vs-output.{extension}", dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, default=Path("results/p3-pilot-2026-10-20/energy.csv")
    )
    parser.add_argument("--output", type=Path, default=Path("results/p3-diagnostics"))
    args = parser.parse_args()
    data = args.source.read_bytes()
    frame = pd.read_csv(args.source)
    if set(frame["record_kind"]) != {"pilot"} or frame["run_id"].duplicated().any():
        raise ValueError("Require unique pilot rows")
    args.output.mkdir(parents=True, exist_ok=True)
    result = {
        "label": "pilot, diagnostic; excluded from hypothesis tests",
        "tool": "HWiNFO CPU Package Power; trapezoidal; approximate post-load gross/net",
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "rows": len(frame),
        "statistics": diagnose(frame),
    }
    (args.output / "diagnostics.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    plot(frame, args.output)
    assert args.source.read_bytes() == data
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
