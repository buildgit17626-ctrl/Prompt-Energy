"""Additional owner-requested P4 views; numerical evidence, not approved conclusions."""

import argparse
import hashlib
import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.full_analysis import GROSS, NET, per_correct
from analysis.presentation import ARMS, COLORS, evidence, finish, interval, ordered
from experiments.config import MODELS

FAMILIES = {
    "Task-completion instructions": ["P0", "P1", "P5"],
    "Example-guided generation": ["P3_1", "P3_3"],
    "Explanation / step-by-step requests": ["P2", "P4"],
}


def summarize(data: pd.DataFrame) -> pd.DataFrame:
    """Keep stage 2 out; incomplete cost coverage never becomes a complete-cost ratio."""
    part = data.loc[data.stage.eq(1)]
    if part.duplicated(["model", "prompt_id", "task_id"]).any():
        raise ValueError("Duplicate task within stage-1 model/arm")
    rows = []
    for (model, arm), group in part.groupby(["model", "prompt_id"]):
        row = {
            "model": model,
            "prompt_id": arm,
            "rows": len(group),
            "successes": int(group.passed.sum()),
            "failures": int((~group.passed).sum()),
            "passed_mean": float(group.passed.mean()),
        }
        for field in ("input_tokens", "output_tokens", NET, GROSS):
            values = group[field].to_numpy(dtype=float)
            finite = values[np.isfinite(values)]
            row[f"{field}_n"] = len(finite)
            row[f"{field}_mean"] = float(finite.mean()) if len(finite) else np.nan
            ratio = per_correct(values, group.passed.to_numpy())
            row[f"{field}_per_correct"] = ratio if ratio is not None else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def check_summary(actual: pd.DataFrame, registered: pd.DataFrame) -> None:
    """Verify independently recomputed values against the existing registered output."""
    keys = ["model", "prompt_id"]
    a, b = actual.set_index(keys).sort_index(), registered.set_index(keys).sort_index()
    if not a.index.equals(b.index):
        raise ValueError("Summary groups differ")
    for field in actual.columns.difference(keys + ["failures"]):
        if field in b and not np.allclose(a[field], b[field], equal_nan=True):
            raise ValueError(f"Registered summary mismatch: {field}")


def success_failure(summary: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 7), sharex=True, sharey=True)
    x = np.arange(len(ARMS))
    for i, (model, ax) in enumerate(zip(MODELS, axes, strict=True)):
        g = ordered(summary, model)
        for shift, values, color, label in (
            (-0.18, g.passed_mean * 100, COLORS[i], "Passed"),
            (0.18, (1 - g.passed_mean) * 100, "#b8c1cc", "Did not pass"),
        ):
            bars = ax.bar(x + shift, values, 0.34, color=color, label=label)
            ax.bar_label(bars, labels=[f"{v:.1f}%" for v in values], fontsize=8, padding=3)
        ax.set(title=model, ylabel="Attempts (%)", ylim=(0, 100))
        ax.legend(loc="upper right", fontsize=9)
    axes[-1].set(xticks=x, xticklabels=ARMS, xlabel="Prompt")
    finish(
        fig,
        output,
        "08_success_failure",
        "Stage 1: 40 tasks/arm. Point estimates; all failure types included.",
    )


def input_profile(summary: pd.DataFrame, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 4))
    x = np.arange(len(ARMS))
    for i, model in enumerate(MODELS):
        g = ordered(summary, model)
        ax.bar(x + (i - 0.5) * 0.36, g.input_tokens_mean, 0.34, color=COLORS[i], label=model)
        interval(ax, x + (i - 0.5) * 0.36, g, "input_tokens")
    ax.set(xticks=x, xticklabels=ARMS, ylabel="Mean input tokens", title="Input length by prompt")
    ax.legend(fontsize=9)
    finish(
        fig,
        output,
        "09_input_by_prompt",
        "Stage 1; n=40/arm. 95% task-bootstrap intervals. Model means coincide here.",
    )


def mean_association(
    summary: pd.DataFrame, output: Path, xfield: str, yfields: list, name: str
) -> None:
    fig, axes = plt.subplots(len(yfields), 2, figsize=(10.5, 4 * len(yfields)), squeeze=False)
    for i, model in enumerate(MODELS):
        g = ordered(summary, model)
        for j, (yfield, ylabel, scale) in enumerate(yfields):
            ax = axes[j, i]
            x, y = g[xfield], g[yfield] * scale
            ax.scatter(x, y, c=np.arange(len(ARMS)), cmap="tab10", vmin=0, vmax=9, s=55)
            for arm, xv, yv in zip(ARMS, x, y, strict=True):
                # P2/P4 share input means; separate label offsets, never change data positions.
                offset = (5, -13) if arm == "P4" else (5, 5)
                if xfield == "output_tokens_mean":
                    offsets = {
                        "P0": (5, 5),
                        "P1": (-20, -20),
                        "P5": (12, -5),
                        "P3_3": (-32, 16),
                        "P3_1": (10, 20),
                        "P2": (5, 8),
                        "P4": (-24, 8),
                    }
                    offset = offsets[arm]
                elif yfield == "passed_mean":
                    offset = {"P0": (-26, 12), "P1": (6, 12), "P2": (-30, -15), "P4": (6, -24)}.get(
                        arm, (5, 5)
                    )
                if model == MODELS[1] and arm in ("P2", "P4"):
                    offset = (-28, -17) if arm == "P2" else (6, 10)
                ax.annotate(
                    arm,
                    (xv, yv),
                    xytext=offset,
                    textcoords="offset points",
                    fontsize=9,
                    arrowprops={"arrowstyle": "-", "color": "#94a3b8", "lw": 0.6},
                )
            xlabel = "Mean input tokens" if xfield == "input_tokens_mean" else "Mean output tokens"
            ax.set(title=model, xlabel=xlabel, ylabel=ylabel)
            ax.margins(x=0.20, y=0.24)
    finish(
        fig,
        output,
        name,
        "Stage 1: each point = one arm mean, 40 tasks. Descriptive, not causal; no fitted line.",
    )


def output_cost(summary: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    for i, (model, ax) in enumerate(zip(MODELS, axes, strict=True)):
        g = ordered(summary, model)
        ax.bar(ARMS, g.output_tokens_per_correct, color=COLORS[i])
        ax.set(title=model, ylabel="Output tokens per correct solution")
    finish(
        fig,
        output,
        "12_output_per_correct",
        "Total output tokens of ALL attempts / number passing. Aggregate ratios; no intervals.",
    )


def family_comparison(summary: pd.DataFrame, output: Path) -> None:
    metrics = [
        ("output_tokens_mean", "Mean output tokens", 1),
        (f"{NET}_mean", "Mean net energy (mWh)", 1000),
        ("passed_mean", "Pass rate (%)", 100),
    ]
    fig, axes = plt.subplots(3, 3, figsize=(13, 10))
    for r, (family, arms) in enumerate(FAMILIES.items()):
        for c, (field, label, scale) in enumerate(metrics):
            ax = axes[r, c]
            x = np.arange(len(arms))
            for i, model in enumerate(MODELS):
                g = ordered(summary, model).loc[arms]
                ax.bar(x + (i - 0.5) * 0.36, g[field] * scale, 0.34, color=COLORS[i], label=model)
            ax.set(xticks=x, xticklabels=arms, ylabel=label, title=family, ylim=(0, None))
            if field == "passed_mean":
                ax.set_ylim(0, 100)
            if r == 0 and c == 0:
                ax.legend(fontsize=8)
    finish(
        fig,
        output,
        "14_within_families",
        "Post-collection presentation families; separate arms. Point estimates, n=40 each.",
    )


def representatives(summary: pd.DataFrame, output: Path) -> None:
    arms = ["P1", "P3_3", "P2"]
    metrics = [
        ("output_tokens_mean", "Output tokens / attempt", 1),
        (f"{NET}_mean", "Net mWh / attempt", 1000),
        (f"{NET}_per_correct", "Net mWh / correct", 1000),
        ("output_tokens_per_correct", "Output tokens / correct", 1),
    ]
    fig, axes = plt.subplots(2, 4, figsize=(13, 7))
    for i, model in enumerate(MODELS):
        g = ordered(summary, model).loc[arms]
        for j, (field, label, scale) in enumerate(metrics):
            ax = axes[i, j]
            bars = ax.bar(arms, g[field] * scale, color=["#2563eb", "#339781", "#c87514"])
            ax.bar_label(bars, fmt="%.1f", fontsize=8, padding=3)
            ax.set(
                title=f"{model.split(':')[-1]}: {label}", ylim=(0, g[field].max() * scale * 1.25)
            )
    finish(
        fig,
        output,
        "15_representative_tradeoffs",
        "P1 / P3_3 / P2 contrast; not a category average or proof of a universal best prompt.",
    )


def leaders(summary: pd.DataFrame) -> pd.DataFrame:
    """Return all tied sample leaders; approvals and population claims are outside this helper."""
    rows = []
    metrics = {
        "Success rate": ("passed_mean", "max", 100, "%"),
        "Input tokens / attempt": ("input_tokens_mean", "min", 1, "tokens"),
        "Output tokens / attempt": ("output_tokens_mean", "min", 1, "tokens"),
        "Net energy / attempt": (f"{NET}_mean", "min", 1000, "mWh"),
        "Gross energy / attempt": (f"{GROSS}_mean", "min", 1000, "mWh"),
        "Net energy / correct": (f"{NET}_per_correct", "min", 1000, "mWh"),
        "Gross energy / correct": (f"{GROSS}_per_correct", "min", 1000, "mWh"),
        "Output tokens / correct": ("output_tokens_per_correct", "min", 1, "tokens"),
    }
    for model, group in summary.groupby("model"):
        for metric, (field, direction, scale, unit) in metrics.items():
            best = getattr(group[field], direction)()
            arms = group.loc[group[field].eq(best), "prompt_id"].tolist()
            rows.append(
                {
                    "model": model,
                    "metric": metric,
                    "arms": ", ".join(arms),
                    "value": best * scale,
                    "unit": unit,
                    "status": "OWNER REVIEW PENDING",
                }
            )
    return pd.DataFrame(rows)


def gallery(output: Path) -> None:
    """Portable review: copy existing figures, rather than drawing duplicate charts."""
    import shutil

    reused = ["02_output_energy", "03_verified_cost", "05_resolution_sensitivity"]
    existing = output / "existing"
    existing.mkdir(exist_ok=True)
    for name in reused:
        shutil.copyfile(Path("results/p4-presentation") / f"{name}.png", existing / f"{name}.png")
    chunks = [
        "<!doctype html><html><meta charset='utf-8'><title>P4 comparison review</title>",
        "<style>body{font:17px Arial;max-width:1100px;margin:40px auto;color:#17324d}"
        "img{width:100%}section{break-inside:avoid}p{line-height:1.5}</style>",
        "<h1>P4 supplementary comparisons</h1><p>Owner review draft. Stage 1: 560 attempts, "
        "40 tasks per model/arm. All stage-1 energy rows have baseline drift; 70 are "
        "low resolution. New views are descriptive; no new significance tests. "
        "HWiNFO CPU Package Power excludes whole-laptop electricity.</p>",
        "<p><a href='REVIEW.md'>Expectations and observations</a> | "
        "<a href='SETUP.md'>Full setup and methods</a>. Conclusions await owner approval.</p>",
    ]
    paths = sorted(output.glob("*.png")) + sorted(existing.glob("*.png"))
    for path in paths:
        prefix = "Existing figure: " if path.parent == existing else "New supplementary figure: "
        label = prefix + html.escape(path.stem.replace("_", " "))
        chunks.append(
            f"<section><h2>{label}</h2><img src='{path.relative_to(output).as_posix()}'></section>"
        )
    chunks.append("</html>")
    (output / "index.html").write_text("\n".join(chunks), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/p4-comparisons"))
    args = parser.parse_args()
    root, summaries = Path("results/p4-full"), Path("results/p4-analysis")
    data, info = evidence(root, summaries)
    actual = summarize(data)
    registered = pd.read_csv(summaries / "all_rows/summary.csv")
    check_summary(actual, registered)
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
        }
    )
    success_failure(registered, args.output)
    input_profile(registered, args.output)
    mean_association(
        registered,
        args.output,
        "input_tokens_mean",
        [(f"{NET}_mean", "Mean net energy (mWh)", 1000)],
        "10_input_energy",
    )
    mean_association(
        registered,
        args.output,
        "input_tokens_mean",
        [("passed_mean", "Pass rate (%)", 100), ("output_tokens_mean", "Mean output tokens", 1)],
        "11_input_relationships",
    )
    output_cost(registered, args.output)
    mean_association(
        registered,
        args.output,
        "output_tokens_mean",
        [(f"{NET}_mean", "Mean net energy (mWh)", 1000)],
        "13_output_mean_energy",
    )
    family_comparison(registered, args.output)
    representatives(registered, args.output)
    actual.to_csv(args.output / "summary.csv", index=False)
    leaders(actual).to_csv(args.output / "candidate_metric_leaders.csv", index=False)
    info["families"] = FAMILIES
    info["interpretation_status"] = "Owner approval required; descriptive review only"
    (args.output / "provenance.json").write_text(
        json.dumps(info, indent=2) + "\n", encoding="utf-8"
    )
    import shutil

    for name, dest in [
        ("P4_EXPECTATIONS_OBSERVATIONS.md", "REVIEW.md"),
        ("P4_SETUP.md", "SETUP.md"),
    ]:
        shutil.copyfile(Path("docs/analysis") / name, args.output / dest)
    gallery(args.output)
    if hashlib.sha256((root / "full.csv").read_bytes()).hexdigest() != info["source_sha256"]:
        raise RuntimeError("Source changed")
    print(f"Eight new figures and tables: {args.output.resolve()}")


if __name__ == "__main__":
    main()
