"""One-page supplementary comparisons and numerical audit for the professor packet."""

import base64
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.comparisons import FAMILIES, check_summary, summarize
from analysis.full_analysis import GROSS, NET, load_full
from experiments.config import MODELS, PROMPTS

OUT = Path("results/p4-professor")
COLORS = ("#2063a5", "#b46b16")
ARMS = ["P0", "P1", "P2", "P3_1", "P3_3", "P4", "P5"]


def audit_sources(full: pd.DataFrame, summary: pd.DataFrame) -> dict:
    """Cross-check primary results, reviewed text hashes and retained source digests."""
    checks = {}
    expected_hashes = json.loads(Path("results/p4-revision/provenance.json").read_text())
    for name, digest in expected_hashes["source_sha256"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Changed source: {name}")
    stage = full[full.stage == 1]
    if len(stage) != 560 or len(full) != 840 or int(stage.passed.sum()) != 347:
        raise ValueError("Unexpected stage counts")
    check_summary(summary, pd.read_csv("results/p4-analysis/all_rows/summary.csv"))
    reviewed = pd.read_csv("docs/analysis/P4_FAILURE_REVIEW.csv")
    raw = {
        r["request_id"]: r
        for r in map(json.loads, Path("results/p4-full/raw.jsonl").read_text().splitlines())
    }
    for row in reviewed.itertuples():
        response = json.loads(base64.b64decode(raw[row.run_id]["body_base64"]))["response"]
        if hashlib.sha256(response.encode()).hexdigest() != row.raw_text_sha256:
            raise ValueError(f"Review text mismatch: {row.run_id}")
    contrasts = pd.read_csv("results/p4-revision/paired_contrasts.csv")
    for row in contrasts.itertuples():
        group = stage[stage.model == row.model]
        pairs = group.pivot(index="task_id", columns="prompt_id", values="passed")
        delta = pairs[row.a].astype(int) - pairs[row.b].astype(int)
        if int(delta.eq(1).sum()) != row.a_only_pass or int(delta.eq(-1).sum()) != row.b_only_pass:
            raise ValueError("Paired discordance mismatch")
    checks.update(
        stage_1_rows=560,
        stage_2_rows=280,
        stage_1_successes=347,
        reviewed_response_hashes=len(reviewed),
        validated_paired_contrasts=len(contrasts),
        raw_sources_unchanged=True,
        summaries_match_registered=True,
    )
    manuscript = Path("docs/analysis/P4_MANUSCRIPT.md").read_text(encoding="utf-8")
    for prompt in PROMPTS.values():
        if prompt["instruction"] not in manuscript:
            raise ValueError("Manuscript does not contain an exact registered instruction")
    table = manuscript.split("| Model | Arm | Pass / 40 |")[1].split("\n\n")[0]
    rows = [
        line for line in table.splitlines() if line.startswith("| 0.") or line.startswith("| 1.")
    ]
    if len(rows) != 14:
        raise ValueError("Manuscript summary table incomplete")
    for line in rows:
        size, arm, passes, tokens, net, gross = [v.strip() for v in line.strip("|").split("|")]
        record = summary[
            (summary.model == f"qwen2.5-coder:{size}") & (summary.prompt_id == arm)
        ].iloc[0]
        expected = [
            str(int(record.successes)),
            f"{record.output_tokens_mean:.1f}",
            f"{record[f'{NET}_mean'] * 1000:.2f}",
            f"{record[f'{GROSS}_mean'] * 1000:.2f}",
        ]
        if [passes, tokens, net, gross] != expected:
            raise ValueError(f"Manuscript table mismatch: {size}/{arm}")
    checks.update(manuscript_summary_rows_checked=14, exact_instructions_checked=7)
    return checks


def build_sheet(summary: pd.DataFrame) -> list[dict]:
    """Show all missing requested views once; families retain separate prompt arms."""
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.size": 14,
            "axes.titlesize": 16,
            "axes.labelsize": 14,
            "xtick.labelsize": 14,
            "ytick.labelsize": 14,
            "legend.fontsize": 12,
            "svg.fonttype": "none",
        }
    )
    # A1 landscape is a zoomable foldout: 30 full-size panels cannot be legible on A4.
    fig, axes = plt.subplots(5, 6, figsize=(33.1, 21.5))
    axes = iter(axes.flat)
    panels = []

    def panel(title: str) -> plt.Axes:
        ax = next(axes)
        panels.append({"panel": f"S{len(panels) + 1}", "title": title})
        ax.set_title(f"{panels[-1]['panel']}. {title}", pad=10)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.15)
        ax.set_axisbelow(True)
        return ax

    def group(model: str, arms: list[str] = ARMS) -> pd.DataFrame:
        return summary[summary.model == model].set_index("prompt_id").loc[arms]

    def bars(
        ax: plt.Axes, field: str, label: str, arms: list[str] = ARMS, scale: float = 1
    ) -> None:
        x = np.arange(len(arms))
        for i, model in enumerate(MODELS):
            ax.bar(
                x + (i - 0.5) * 0.36,
                group(model, arms)[field] * scale,
                0.34,
                color=COLORS[i],
                label=model.split(":")[-1],
            )
        ax.set(xticks=x, xticklabels=arms, ylabel=label, ylim=(0, None))
        if field == "passed_mean":
            ax.set_ylim(0, 115)
        else:
            maximum = max(group(model, arms)[field].max() * scale for model in MODELS)
            ax.set_ylim(0, maximum * 1.25)
        ax.legend(ncol=2, loc="upper right")

    def scatter(
        model: str, xfield: str, yfield: str, xlabel: str, ylabel: str, scale: float = 1
    ) -> None:
        ax = panel(f"{model.split(':')[-1]}: {ylabel}\nversus {xlabel.lower()}")
        g = group(model)
        for i, arm in enumerate(ARMS):
            ax.scatter(
                g.loc[arm, xfield],
                g.loc[arm, yfield] * scale,
                color=plt.get_cmap("tab10")(i),
                marker=["o", "s", "^", "D", "v", "o", "P"][i],
                facecolors="none" if arm == "P4" else plt.get_cmap("tab10")(i),
                s=100 if arm == "P4" else 65,
                label=arm,
            )
        ax.set(xlabel=xlabel, ylabel=ylabel)
        ax.margins(0.15)
        # A compact legend avoids moving or jittering coincident points.
        ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.02), fontsize=11)
        low, high = ax.get_ylim()
        ax.set_ylim(low, high + (high - low) * 0.4)

    for model in MODELS:
        ax = panel(f"{model.split(':')[-1]}: success and failure")
        g = group(model)
        x = np.arange(7)
        ax.bar(x - 0.18, g.passed_mean * 100, 0.34, color="#27744e", label="Passed")
        ax.bar(x + 0.18, (1 - g.passed_mean) * 100, 0.34, color="#a8adb3", label="Did not pass")
        ax.set(xticks=x, xticklabels=ARMS, ylabel="Attempts (%)", ylim=(0, 115))
        ax.legend(ncol=2)
    bars(panel("Input tokens by prompt"), "input_tokens_mean", "Input tokens / attempt")
    for model in MODELS:
        ax = panel(f"{model.split(':')[-1]}: output tokens by prompt")
        ax.bar(ARMS, group(model).output_tokens_mean, color=COLORS[MODELS.index(model)])
        ax.set(ylabel="Output tokens / attempt", ylim=(0, None))
    for yfield, ylabel, scale in [
        (f"{NET}_mean", "Net energy (mWh)", 1000),
        ("passed_mean", "Success rate (%)", 100),
        ("output_tokens_mean", "Output tokens", 1),
    ]:
        for model in MODELS:
            scatter(model, "input_tokens_mean", yfield, "Input tokens", ylabel, scale)
    for model in MODELS:
        scatter(
            model, "output_tokens_mean", f"{NET}_mean", "Output tokens", "Net energy (mWh)", 1000
        )
    for model in MODELS:
        ax = panel(f"{model.split(':')[-1]}: gross and net energy")
        g = group(model)
        x = np.arange(7)
        ax.bar(x - 0.18, g[f"{NET}_mean"] * 1000, 0.34, color="#2063a5", label="Net")
        ax.bar(x + 0.18, g[f"{GROSS}_mean"] * 1000, 0.34, color="#b46b16", label="Gross")
        ax.set(xticks=x, xticklabels=ARMS, ylabel="Post-load mWh / attempt", ylim=(0, None))
        ax.set_ylim(0, g[f"{GROSS}_mean"].max() * 1300)
        ax.legend(ncol=2, loc="upper right")
    for model in MODELS:
        ax = panel(f"{model.split(':')[-1]}: output tokens per correct")
        ax.bar(ARMS, group(model).output_tokens_per_correct, color=COLORS[MODELS.index(model)])
        ax.set(ylabel="All output tokens / successes", ylim=(0, None))
    names = [
        "A: instruction + generation",
        "B: examples + generation",
        "C: explanation + generation",
    ]
    for name, arms in zip(names, FAMILIES.values(), strict=True):
        for field, label, scale in [
            ("output_tokens_mean", "Output tokens / attempt", 1),
            (f"{NET}_mean", "Net mWh / attempt", 1000),
            ("passed_mean", "Success rate (%)", 100),
        ]:
            bars(panel(f"{name}\n{label}"), field, label, arms, scale)
    for field, label, scale in [
        ("output_tokens_mean", "Output tokens / attempt", 1),
        (f"{NET}_mean", "Net mWh / attempt", 1000),
        (f"{NET}_per_correct", "Net mWh / correct", 1000),
        ("output_tokens_per_correct", "Output tokens / correct", 1),
    ]:
        bars(panel(f"P1 / P3_3 / P2\n{label}"), field, label, ["P1", "P3_3", "P2"], scale)
    if len(panels) != 30:
        raise ValueError("Missing comparison panels")
    fig.suptitle(
        "Supplementary comparisons: individual prompts within the three categories",
        fontsize=28,
        y=0.995,
    )
    fig.text(
        0.5,
        0.012,
        "Stage 1: 40 tasks per model/arm. Point estimates; no category pooling. "
        "HWiNFO CPU Package Power, trapezoidal, approximate post-load.\n"
        "Net uses block-start idle 17.553 W; gross is unsubtracted. All rows have baseline drift. "
        "Per-correct ratios include failed-attempt costs; "
        "main Figure 2 has energy-ratio intervals.",
        ha="center",
        fontsize=17,
    )
    fig.subplots_adjust(left=0.035, right=0.987, top=0.95, bottom=0.065, wspace=0.36, hspace=0.60)
    for ext in ["png", "svg"]:
        fig.savefig(OUT / f"comparison_sheet.{ext}", dpi=180, facecolor="white")
    plt.close(fig)
    return panels


def main() -> None:
    """Read, validate, plot and emit coverage for the attached single-page appendix."""
    full, _ = load_full(Path("results/p4-full"))
    summary = summarize(full)
    checks = audit_sources(full, summary)
    OUT.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT / "verified_summary.csv", index=False)
    panels = build_sheet(summary)
    (OUT / "coverage.json").write_text(json.dumps(panels, indent=2) + "\n")
    (OUT / "audit.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
