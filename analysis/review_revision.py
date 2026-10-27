"""Post-hoc owner-requested P4 diagnostics; never modify saved observations."""

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.full_analysis import GROSS, NET, load_full
from experiments.config import MODELS, PROMPTS

CONTRASTS = (("P1", "P0"), ("P2", "P1"), ("P4", "P1"), ("P3_1", "P0"), ("P5", "P1"))
ARMS = list(PROMPTS)
SEED, DRAWS = 1729, 2000
OUT = Path("results/p4-revision")
LABEL = "HWiNFO CPU Package Power | trapezoidal | approximate post-load | stage 1"


def ratio_interval(cost: np.ndarray, passed: np.ndarray) -> dict:
    """Bootstrap the ratio of totals, retaining zero-success draws as undefined."""
    cost, passed = np.asarray(cost, float), np.asarray(passed, bool)
    if len(cost) != len(passed) or not len(cost) or not np.isfinite(cost).all():
        raise ValueError("Require complete equal-length cost and outcome arrays")
    idx = np.random.default_rng(SEED).integers(0, len(cost), (DRAWS, len(cost)))
    denominator = passed[idx].sum(axis=1)
    zero = int((denominator == 0).sum())
    # Do not condition intervals on successful resamples when undefined draws occur.
    if zero or not passed.sum():
        return {
            "value": cost.sum() / passed.sum() if passed.sum() else np.nan,
            "low": np.nan,
            "high": np.nan,
            "zero_success_draws": zero,
        }
    ratios = cost[idx].sum(axis=1) / denominator
    low, high = np.quantile(ratios, [0.025, 0.975])
    return {
        "value": cost.sum() / passed.sum(),
        "low": low,
        "high": high,
        "zero_success_draws": zero,
    }


def paired_contrast(frame: pd.DataFrame, a: str, b: str) -> dict:
    """Align one row per task and arm before resampling within-task differences."""
    part = frame[frame.prompt_id.isin([a, b])]
    if part.duplicated(["task_id", "prompt_id"]).any():
        raise ValueError("Duplicate task/arm")
    energy = part.pivot(index="task_id", columns="prompt_id", values=NET).sort_index()
    success = part.pivot(index="task_id", columns="prompt_id", values="passed").sort_index()
    if set(energy.columns) != {a, b} or energy.isna().any().any() or success.isna().any().any():
        raise ValueError("Incomplete paired tasks")
    delta = np.column_stack(
        [
            (energy[a] - energy[b]).to_numpy(),
            (success[a].astype(int) - success[b].astype(int)).to_numpy(),
        ]
    )
    idx = np.random.default_rng(SEED).integers(0, len(delta), (DRAWS, len(delta)))
    low, high = np.quantile(delta[idx].mean(axis=1), [0.025, 0.975], axis=0)
    return {
        "a": a,
        "b": b,
        "n": len(delta),
        "net_difference_wh": delta[:, 0].mean(),
        "net_low_wh": low[0],
        "net_high_wh": high[0],
        "pass_difference": delta[:, 1].mean(),
        "pass_low": low[1],
        "pass_high": high[1],
        "a_only_pass": int((delta[:, 1] == 1).sum()),
        "b_only_pass": int((delta[:, 1] == -1).sum()),
        "both_pass": int((success[a] & success[b]).sum()),
        "both_fail": int((~success[a] & ~success[b]).sum()),
    }


def baseline_scenarios(frame: pd.DataFrame) -> pd.DataFrame:
    """Change only the constant idle assumption, retaining signed estimates."""
    result = frame.copy()
    duration = result.post_load_seconds
    if (duration <= 0).any():
        raise ValueError("Invalid post-load duration")
    result["net_end_wh"] = result[GROSS] - result.end_idle_baseline_w * duration / 3600
    midpoint = (result.idle_baseline_w + result.end_idle_baseline_w) / 2
    result["net_midpoint_wh"] = result[GROSS] - midpoint * duration / 3600
    return result


def repeat_summary(frame: pd.DataFrame, repeats: set[int], label: str) -> pd.DataFrame:
    """Report complete-pair spread without imputing missing energy or pooling studies."""
    rows = []
    for (model, arm), group in frame.groupby(["model", "prompt_id"]):
        gaps, token_gaps, expected, identical = [], [], 0, 0
        for _, pair in group.groupby("task_id"):
            expected += 1
            if len(pair) != 2 or set(pair.repeat) != repeats:
                raise ValueError("Unexpected repeat structure")
            if pair[NET].notna().all():
                gaps.append(abs(float(pair[NET].iloc[1] - pair[NET].iloc[0])))
                tg = abs(int(pair.output_tokens.iloc[1] - pair.output_tokens.iloc[0]))
                token_gaps.append(tg)
                identical += tg == 0
        rows.append(
            {
                "study": label,
                "model": model,
                "prompt_id": arm,
                "planned_pairs": expected,
                "complete_pairs": len(gaps),
                "median_abs_net_difference_wh": np.median(gaps) if gaps else np.nan,
                "p90_abs_net_difference_wh": np.quantile(gaps, 0.9) if gaps else np.nan,
                "median_abs_output_difference": np.median(token_gaps) if gaps else np.nan,
                "equal_output_count_pairs": identical,
            }
        )
    return pd.DataFrame(rows)


def save(fig: plt.Figure, name: str, note: str) -> None:
    """Write standalone labelled figures in both raster and vector formats."""
    fig.text(0.02, 0.045, note, fontsize=8)
    fig.text(0.02, 0.012, LABEL, fontsize=8)
    fig.tight_layout(rect=(0, 0.11, 1, 0.96))
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=200, facecolor="white")
    plt.close(fig)


def plots(
    contrasts: pd.DataFrame,
    ratios: pd.DataFrame,
    metrics: pd.DataFrame,
    machine: pd.DataFrame,
    review: pd.DataFrame,
) -> None:
    """Central forest and complementary diagnostics with explicit denominators."""
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.1))
    for i, model in enumerate(MODELS):
        g = contrasts[contrasts.model == model]
        for j, (mean, lo, hi, scale, xlabel) in enumerate(
            [
                (
                    "net_difference_wh",
                    "net_low_wh",
                    "net_high_wh",
                    1000,
                    "Net energy difference (mWh/attempt)",
                ),
                (
                    "pass_difference",
                    "pass_low",
                    "pass_high",
                    100,
                    "Pass-rate difference (percentage points)",
                ),
            ]
        ):
            ax = axes[i, j]
            x = g[mean].to_numpy() * scale
            y = np.arange(len(g))
            ax.hlines(y, g[lo] * scale, g[hi] * scale, color="#2563a6", lw=2)
            ax.scatter(x, y, color="#2563a6", s=32)
            ax.axvline(0, color="gray", lw=0.8)
            labels = [
                f"{r.a} - {r.b}" + (f"  [{r.a_only_pass}/{r.b_only_pass}]" if j else "")
                for r in g.itertuples()
            ]
            ax.set(yticks=y, yticklabels=labels, xlabel=xlabel, title=model.split(":")[-1])
            ax.invert_yaxis()
            ax.grid(axis="x", alpha=0.15)
    save(
        fig,
        "01_paired_contrasts",
        "Post hoc: 40 paired tasks; 2,000 task draws, seed 1729; pointwise 95% intervals.\n"
        "Right labels [A-only passes/B-only passes]. No multiplicity adjustment or causal "
        "mechanism claim.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, model in zip(axes, MODELS, strict=True):
        for k, metric in enumerate([NET, GROSS]):
            g = (
                ratios[(ratios.model == model) & (ratios.metric == metric)]
                .set_index("prompt_id")
                .loc[ARMS]
            )
            x = np.arange(7) + (k - 0.5) * 0.22
            ax.vlines(x, g.low * 1000, g.high * 1000, color=["#2563a6", "#ba6b14"][k])
            ax.scatter(x, g.value * 1000, label=["Net", "Gross"][k], s=20)
        ax.set(xticks=np.arange(7), xticklabels=ARMS, title=model.split(":")[-1], ylim=(0, None))
        ax.legend()
    axes[0].set_ylabel("Energy per correct solution (mWh)")
    save(
        fig,
        "02_cost_per_correct",
        "Post hoc 95% task-bootstrap ratio intervals: total attempted energy / total "
        "successes.\n"
        "Failures remain in numerator; 40 tasks per arm. Intervals do not cover systematic "
        "sensor/baseline bias.",
    )
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for col, model in enumerate(MODELS):
        g = metrics[metrics.model == model].set_index("prompt_id").loc[ARMS]
        x = np.arange(7)
        for k, field in enumerate(["failed_net_share", "failed_gross_share"]):
            axes[0, col].bar(
                x + (k - 0.5) * 0.32, g[field] * 100, width=0.3, label=["Net", "Gross"][k]
            )
        axes[0, col].set(
            title=model.split(":")[-1],
            xticks=x,
            xticklabels=ARMS,
            ylabel="Energy on failed attempts (%)",
        )
        axes[0, col].legend()
        axes[1, col].plot(x, g.net_wh_per_output_token * 1000, "o-", label="Net")
        axes[1, col].plot(x, g.gross_wh_per_output_token * 1000, "s-", label="Gross")
        axes[1, col].set(xticks=x, xticklabels=ARMS, ylabel="Energy / generated token (mWh)")
        axes[1, col].legend()
    save(
        fig,
        "03_failure_energy_tokens",
        "Failed-attempt share includes truncations/timeouts; it is not avoidable-energy "
        "savings.\n"
        "Energy/token = sum energy / sum output tokens; includes input/overhead energy, not "
        "decode-only cost.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, model in zip(axes, MODELS, strict=True):
        g = metrics[metrics.model == model].set_index("prompt_id").loc[ARMS]
        for field, label in [
            ("net_start_mean_wh", "Registered start"),
            ("net_mid_mean_wh", "Post hoc midpoint"),
            ("net_end_mean_wh", "Post hoc end"),
        ]:
            ax.plot(ARMS, g[field] * 1000, "o-", label=label)
        ax.set(title=model.split(":")[-1], ylabel="Mean net energy (mWh/attempt)")
        ax.legend(fontsize=8)
    save(
        fig,
        "04_baseline_scenarios",
        "Same 560 requests; constant baseline scenarios: start 17.553 W, midpoint 14.535 W, "
        "end 11.516 W.\n"
        "No inferred time-varying baseline; these scenarios do not correct the registered "
        "measurements.",
    )
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    categories = [
        "wrong_logic",
        "missing_helper",
        "extraction_problem",
        "truncation",
        "no_code",
        "timeout",
    ]
    for col, model in enumerate(MODELS):
        for row, frame, cats, title in [
            (
                0,
                machine,
                ["test_failed", "truncated", "timeout", "no_code"],
                "All 40 attempts per arm",
            ),
            (1, review, categories, "Selected review sample only"),
        ]:
            g = frame[frame.model == model]
            bottom = np.zeros(7)
            for category in cats:
                values = [len(g[(g.prompt_id == a) & (g.category == category)]) for a in ARMS]
                axes[row, col].bar(ARMS, values, bottom=bottom, label=category.replace("_", " "))
                bottom += values
            axes[row, col].set(title=f"{model.split(':')[-1]}: {title}", ylabel="Failure count")
            axes[row, col].legend(fontsize=6.5, ncol=2)
    save(
        fig,
        "05_failure_taxonomy",
        "Top: machine outcomes for every stage-1 failure. Bottom: 64 selected failures, "
        "AI-assisted reading.\n"
        "Zero observed extraction problems in sample is not a complete extraction audit; no "
        "outcomes changed.",
    )


def main() -> None:
    """Build post-hoc evidence from immutable full and pilot sources."""
    paths = [
        Path("results/p4-full") / n
        for n in ["full.csv", "raw.jsonl", "results.jsonl", "measurements.jsonl", "manifest.json"]
    ]
    paths += [Path("results/p3-pilot-2026-10-20/energy.csv")]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    full, _ = load_full(Path("results/p4-full"))
    stage = full[full.stage == 1].copy()
    if len(stage) != 560 or not stage.groupby(["model", "prompt_id"]).size().eq(40).all():
        raise ValueError("Require complete stage 1")
    OUT.mkdir(parents=True, exist_ok=True)
    contrasts = []
    ratios = []
    metrics = []
    for model, g in stage.groupby("model"):
        for a, b in CONTRASTS:
            contrasts.append({"model": model, **paired_contrast(g, a, b)})
    measurements = [
        json.loads(line)
        for line in Path("results/p4-full/measurements.jsonl").read_text().splitlines()
    ]
    seconds = {
        r["run_id"]: r["energy"]["windows"]["post_load"]["seconds"]
        for r in measurements
        if r.get("energy")
        and r["energy"].get("windows", {}).get("post_load", {}).get("seconds") is not None
    }
    stage["post_load_seconds"] = stage.run_id.map(seconds)
    if stage.post_load_seconds.isna().any():
        raise ValueError("Missing saved measurement duration")
    expected = stage[GROSS] - stage.idle_baseline_w * stage.post_load_seconds / 3600
    if not np.allclose(expected, stage[NET], rtol=0, atol=1e-12):
        raise ValueError("Registered baseline reconstruction differs")
    scenario = baseline_scenarios(stage)
    for (model, arm), g in scenario.groupby(["model", "prompt_id"]):
        for metric in [NET, GROSS]:
            ratios.append(
                {
                    "model": model,
                    "prompt_id": arm,
                    "metric": metric,
                    **ratio_interval(g[metric].to_numpy(), g.passed.to_numpy()),
                }
            )
        metrics.append(
            {
                "model": model,
                "prompt_id": arm,
                "n": len(g),
                "successes": int(g.passed.sum()),
                "input_mean": g.input_tokens.mean(),
                "output_mean": g.output_tokens.mean(),
                "net_start_mean_wh": g[NET].mean(),
                "gross_mean_wh": g[GROSS].mean(),
                "net_mid_mean_wh": g.net_midpoint_wh.mean(),
                "net_end_mean_wh": g.net_end_wh.mean(),
                "failed_net_share": g.loc[~g.passed, NET].sum() / g[NET].sum(),
                "failed_gross_share": g.loc[~g.passed, GROSS].sum() / g[GROSS].sum(),
                "net_wh_per_output_token": g[NET].sum() / g.output_tokens.sum(),
                "gross_wh_per_output_token": g[GROSS].sum() / g.output_tokens.sum(),
                "cap_count": int(g.output_tokens.ge(768).sum()),
                "low_resolution": int(
                    g.energy_flags.fillna("").str.contains("post_load:low_resolution").sum()
                ),
            }
        )
    contrasts, ratios, metrics = map(pd.DataFrame, (contrasts, ratios, metrics))
    pilot = pd.read_csv(paths[-1])
    repeats = pd.concat(
        [
            repeat_summary(full[full.stage == 2], {2, 3}, "P4 stage 2"),
            repeat_summary(pilot, {1, 2}, "P3 pilot diagnostic"),
        ],
        ignore_index=True,
    )
    machine = stage[~stage.passed].rename(columns={"failure_type": "category"})
    review = pd.read_csv("docs/analysis/P4_FAILURE_REVIEW.csv")
    if review.run_id.duplicated().any() or not set(review.run_id) <= set(machine.run_id):
        raise ValueError("Invalid review IDs")
    for name, table in [
        ("paired_contrasts", contrasts),
        ("ratio_intervals", ratios),
        ("metrics", metrics),
        ("repeat_noise", repeats),
        ("baseline_scenarios_rows", scenario),
        (
            "machine_failure_counts",
            machine.groupby(["model", "prompt_id", "category"]).size().reset_index(name="count"),
        ),
        (
            "review_failure_counts",
            review.groupby(["model", "prompt_id", "category"]).size().reset_index(name="count"),
        ),
    ]:
        table.to_csv(OUT / f"{name}.csv", index=False)
    plots(contrasts, ratios, metrics, machine, review)
    if hashes != {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}:
        raise ValueError("Source changed")
    (OUT / "provenance.json").write_text(
        json.dumps(
            {
                "post_hoc": True,
                "seed": SEED,
                "draws": DRAWS,
                "source_sha256": hashes,
                "reviewed_failures": len(review),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(contrasts.to_string(index=False))
    print(repeats.to_string(index=False))


if __name__ == "__main__":
    main()
