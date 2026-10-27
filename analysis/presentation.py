"""Reproducible P4 figures and evidence for an owner-reviewed professor brief."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.full_analysis import GROSS, NET, load_full, noise_rows
from experiments.config import MODELS, PROMPTS

ARMS = list(PROMPTS)
COLORS = ["#2563eb", "#c87514"]
FOOTER = "HWiNFO CPU Package Power | trapezoidal | approximate post-load | idle-adjusted net"


def evidence(root: Path, summaries: Path) -> tuple[pd.DataFrame, dict]:
    """Fail closed on partial/mismatched inputs; report quality instead of hiding it."""
    data, manifest = load_full(root)
    if len(data) != 840 or data.groupby("stage").size().to_dict() != {1: 560, 2: 280}:
        raise ValueError("Require complete registered 560/280 design")
    if len(manifest["schedule"]) != 840:
        raise ValueError("Unexpected schedule")
    digest = hashlib.sha256((root / "full.csv").read_bytes()).hexdigest()
    report = json.loads((summaries / "report-scaffold.json").read_text())
    if report["source_sha256"] != digest:
        raise ValueError("Summary source hash differs; regenerate registered scaffolds")
    stage1 = data[data.stage == 1]
    groups = stage1.groupby(["model", "prompt_id"])
    if len(groups) != 14 or not groups.size().eq(40).all():
        raise ValueError("Incomplete stage-1 task coverage")
    noise = noise_rows(data)
    quality = {}
    for stage, part in data.groupby("stage"):
        flags = part.energy_flags.fillna("").str.split(";")
        quality[str(stage)] = {
            "rows": len(part),
            "passed": int(part.passed.sum()),
            "energy_available": int(part[NET].notna().sum()),
            "low_resolution": int(flags.apply(lambda f: "post_load:low_resolution" in f).sum()),
            "baseline_drift": int(flags.apply(lambda f: "baseline_drift" in f).sum()),
            "missing_end_baseline": int(flags.apply(lambda f: "end_baseline_missing" in f).sum()),
        }
    paired = stage1.pivot(index=["task_id", "prompt_id"], columns="model", values="passed")
    small, large = paired[MODELS[0]], paired[MODELS[1]]
    info = {
        "source_sha256": digest,
        "quality": quality,
        "complete_energy_pairs": int(noise.energy_available.eq(2).sum()),
        "planned_energy_pairs": len(noise),
        "model_pair_outcomes": {
            "only_0.5b_passed": int((small & ~large).sum()),
            "only_1.5b_passed": int((~small & large).sum()),
            "both_passed": int((small & large).sum()),
            "both_failed": int((~small & ~large).sum()),
        },
        "generation_commit": "041f169",
        "scope": "Completed P4 baseline experiment; descriptive review draft",
    }
    return data, info


def finish(fig: plt.Figure, output: Path, name: str, note: str) -> None:
    fig.text(0.02, 0.045, note, fontsize=9, color="#374151")
    fig.text(0.02, 0.012, FOOTER, fontsize=8.5, color="#4b5563")
    fig.tight_layout(rect=(0, 0.105, 1, 0.98))
    for ext in ("png", "svg"):
        fig.savefig(output / f"{name}.{ext}", dpi=300, facecolor="white")
    plt.close(fig)


def ordered(summary: pd.DataFrame, model: str) -> pd.DataFrame:
    return summary[summary.model == model].set_index("prompt_id").loc[ARMS]


def interval(ax: plt.Axes, x: np.ndarray, group: pd.DataFrame, field: str, scale=1.0) -> None:
    mean = group[f"{field}_mean"].to_numpy() * scale
    lo = group[f"{field}_low"].to_numpy() * scale
    hi = group[f"{field}_high"].to_numpy() * scale
    ax.errorbar(x, mean, yerr=[mean - lo, hi - mean], fmt="none", ecolor="#374151", capsize=3)


def accuracy(summary: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), sharey=True)
    for i, (model, ax) in enumerate(zip(MODELS, axes, strict=True)):
        g = ordered(summary, model)
        x = np.arange(len(ARMS))
        ax.bar(x, g.passed_mean * 100, color=COLORS[i], width=0.65, alpha=0.85)
        interval(ax, x, g, "passed", 100)
        for j, r in enumerate(g.itertuples()):
            ax.text(j, 3, f"{r.successes}/40", ha="center", color="white", fontsize=10)
        ax.set(title=model, xticks=x, xticklabels=ARMS, ylim=(0, 103))
    axes[0].set_ylabel("Pass rate (%)")
    finish(
        fig,
        output,
        "01_accuracy",
        "Stage 1: 40 tasks per arm. 95% task-bootstrap intervals; not paired significance tests.",
    )


def output_energy(summary: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.7))
    x = np.arange(len(ARMS))
    for i, model in enumerate(MODELS):
        g = ordered(summary, model)
        ax = axes[i, 0]
        ax.bar(x, g.output_tokens_mean, color=COLORS[i], alpha=0.85)
        interval(ax, x, g, "output_tokens")
        ax.set(
            title=f"{model}: generated tokens",
            ylabel="Mean output tokens",
            xticks=x,
            xticklabels=ARMS,
        )
        ax.set_ylim(bottom=0)
        ax = axes[i, 1]
        for offset, field, color, label in (
            (-0.18, GROSS, "#a8b6c5", "Gross"),
            (0.18, NET, COLORS[i], "Net"),
        ):
            ax.bar(x + offset, g[f"{field}_mean"] * 1000, width=0.34, color=color, label=label)
            interval(ax, x + offset, g, field, 1000)
        ax.set(
            title=f"{model}: energy per attempt",
            ylabel="Mean energy (mWh)",
            xticks=x,
            xticklabels=ARMS,
        )
        ax.set_ylim(bottom=0)
        ax.legend(fontsize=9)
    finish(
        fig,
        output,
        "02_output_energy",
        "Stage 1; n=40 per arm. 95% bootstrap intervals. All energy rows carry baseline drift.",
    )


def verified_cost(summary: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8))
    x = np.arange(len(ARMS))
    for i, (model, ax) in enumerate(zip(MODELS, axes, strict=True)):
        g = ordered(summary, model)
        ax.bar(x - 0.18, g[f"{GROSS}_per_correct"] * 1000, 0.34, color="#a8b6c5", label="Gross")
        ax.bar(x + 0.18, g[f"{NET}_per_correct"] * 1000, 0.34, color=COLORS[i], label="Net")
        ax.set(title=model, xticks=x, xticklabels=ARMS, ylabel="Energy per correct solution (mWh)")
        ax.set_ylim(bottom=0)
        ax.legend(fontsize=9)
    finish(
        fig,
        output,
        "03_verified_cost",
        "Total attempt energy / number correct. Failures included; point estimates only.",
    )


def association(data: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0), sharex=True)
    stage1 = data[data.stage == 1]
    palette = plt.get_cmap("tab10")
    for model, ax in zip(MODELS, axes, strict=True):
        g = stage1[stage1.model == model]
        for j, arm in enumerate(ARMS):
            part = g[g.prompt_id == arm]
            ax.scatter(
                part.output_tokens, part[NET] * 1000, s=18, alpha=0.65, color=palette(j), label=arm
            )
        ax.set(
            title=f"{model} | 280 attempts",
            xlabel="Actual output tokens",
            ylabel="Net post-load energy (mWh)",
        )
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.legend(ncol=4, fontsize=7.5, loc="upper left")
    finish(
        fig,
        output,
        "04_token_energy",
        "Stage 1 includes failures; association is not causation. Output cap: 768 tokens.",
    )


def sensitivity(summary: pd.DataFrame, filtered: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8))
    x = np.arange(len(ARMS))
    for i, (model, ax) in enumerate(zip(MODELS, axes, strict=True)):
        a, b = ordered(summary, model), ordered(filtered, model)
        ax.plot(x, a[f"{NET}_mean"] * 1000, "o-", color=COLORS[i], label="All 40 tasks")
        ax.plot(x, b[f"{NET}_mean"] * 1000, "s--", color="#64748b", label="Exclude low resolution")
        for j, count in enumerate(b.rows):
            ax.text(j, 0, f"n={count}", ha="center", va="bottom", fontsize=8)
        ax.set(title=model, xticks=x, xticklabels=ARMS, ylabel="Mean net energy (mWh)")
        ax.set_ylim(bottom=0)
        ax.legend(fontsize=8)
    finish(
        fig,
        output,
        "05_resolution_sensitivity",
        "Filtered: 490/560 rows; different task mix. Connecting lines are not a linear fit.",
    )


def groups(calibration: pd.DataFrame, length: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.7), sharey=True)
    eligible = [a for a in ARMS if a != "P0"]
    x = np.arange(len(eligible))
    for i, model in enumerate(MODELS):
        for j, (frame, names, title) in enumerate(
            (
                (calibration, ("solved", "failed"), "Frozen calibration"),
                (length, ("short", "long"), "Reference length"),
            )
        ):
            ax = axes[i, j]
            for k, name in enumerate(names):
                g = (
                    frame[(frame.model == model) & (frame.difficulty_group == name)]
                    .set_index("prompt_id")
                    .loc[eligible]
                )
                ax.bar(
                    x + (k - 0.5) * 0.36,
                    g.passed_mean * 100,
                    0.34,
                    color=[COLORS[i], "#a8b6c5"][k],
                    label=f"{name} (n={g.rows.iloc[0]})",
                )
            ax.set(
                title=f"{model}: {title}",
                xticks=x,
                xticklabels=eligible,
                ylabel="Pass rate (%)",
                ylim=(0, 105),
            )
            ax.legend(fontsize=8)
    finish(
        fig,
        output,
        "06_frozen_groups",
        "Stage 1; P0 excluded. Calibration groups are model-dependent, not intrinsic difficulty.",
    )


def repeat_noise(data: pd.DataFrame, output: Path) -> None:
    noise = noise_rows(data)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), sharey=True)
    for i, (model, ax) in enumerate(zip(MODELS, axes, strict=True)):
        for j, arm in enumerate(ARMS):
            g = noise[(noise.model == model) & (noise.prompt_id == arm)]
            values = g.absolute_repeat_difference_wh.dropna().to_numpy() * 1000
            ax.scatter(np.full(len(values), j), values, color=COLORS[i], alpha=0.65, s=24)
            ax.text(j, 0, f"{len(values)}/10", ha="center", va="bottom", fontsize=8)
        ax.set(
            title=model,
            xticks=range(len(ARMS)),
            xticklabels=ARMS,
            ylabel="Absolute repeat difference (mWh)",
        )
        ax.set_ylim(bottom=0)
    finish(
        fig,
        output,
        "07_repeat_variability",
        "Stage 2: 64/140 complete pairs. Output variation + machine/measurement noise.",
    )


def render(root: Path, summaries: Path, output: Path) -> dict:
    data, info = evidence(root, summaries)
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.axisbelow": True,
            "axes.grid": True,
            "grid.alpha": 0.15,
            "svg.fonttype": "none",
        }
    )
    tables = {}
    for key, path in {
        "summary": summaries / "all_rows/summary.csv",
        "filtered": summaries / "without_primary_low_resolution/summary.csv",
        "calibration": summaries / "all_rows/calibration-groups.csv",
        "length": summaries / "all_rows/reference_length-groups.csv",
        "regression": summaries / "all_rows/regression.csv",
    }.items():
        tables[key] = pd.read_csv(path)
        tables[key].to_csv(output / f"{key}.csv", index=False)
    summary = tables["summary"]
    accuracy(summary, output)
    output_energy(summary, output)
    verified_cost(summary, output)
    association(data, output)
    sensitivity(summary, tables["filtered"], output)
    groups(tables["calibration"], tables["length"], output)
    repeat_noise(data, output)
    info["tables"] = {k: json.loads(v.to_json(orient="records")) for k, v in tables.items()}
    (output / "evidence.json").write_text(
        json.dumps(info, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    if hashlib.sha256((root / "full.csv").read_bytes()).hexdigest() != info["source_sha256"]:
        raise RuntimeError("Source changed during plotting")
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path("results/p4-full"))
    parser.add_argument("--summaries", type=Path, default=Path("results/p4-analysis"))
    parser.add_argument("--output", type=Path, default=Path("results/p4-presentation"))
    args = parser.parse_args()
    info = render(args.run, args.summaries, args.output)
    print(json.dumps({k: v for k, v in info.items() if k != "tables"}, indent=2))


if __name__ == "__main__":
    main()
