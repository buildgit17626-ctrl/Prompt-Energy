"""P4 analysis scaffolds; the owner supplies interpretation, never the script."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.config import P4_ANALYSIS

NET = "cpu_pkg_energy_wh"
GROSS = "cpu_pkg_post_load_raw_wh"
MODE = "HWiNFO CPU Package Power; trapezoidal; approximate post-load gross/net"


def bootstrap_mean(values: np.ndarray, *, seed: int, draws: int) -> dict:
    """Resample task rows including missing values; expose finite observations."""
    data = np.asarray(values, dtype=float)
    finite = data[np.isfinite(data)]
    if not len(finite):
        return {"n": 0, "mean": None, "low": None, "high": None}
    samples = np.random.default_rng(seed).choice(data, (draws, len(data)), replace=True)
    counts = np.isfinite(samples).sum(axis=1)
    averages = np.divide(
        np.nansum(samples, axis=1),
        counts,
        out=np.full(draws, np.nan),
        where=counts != 0,
    )
    valid = averages[np.isfinite(averages)]
    tail = (1 - P4_ANALYSIS["confidence"]) / 2
    return {
        "n": len(finite),
        "mean": float(finite.mean()),
        "low": float(np.quantile(valid, tail)),
        "high": float(np.quantile(valid, 1 - tail)),
    }


def per_correct(values: np.ndarray, passed: np.ndarray) -> float | None:
    """Failures cost energy too; missing costs or zero successes make the ratio unknown."""
    values = np.asarray(values, dtype=float)
    successes = np.asarray(passed, dtype=bool).sum()
    if not successes or not np.isfinite(values).all():
        return None
    return float(values.sum() / successes)


def regression(frame: pd.DataFrame, energy: str = NET) -> tuple[dict, pd.DataFrame]:
    """OLS with both token predictors; rank deficiency is reported, not disguised."""
    good = (
        frame[["input_tokens", "output_tokens", energy]].replace([np.inf, -np.inf], np.nan).dropna()
    )
    x = np.column_stack([np.ones(len(good)), good["input_tokens"], good["output_tokens"]])
    y = good[energy].to_numpy()
    empty = pd.DataFrame(columns=["run_id", "fitted_wh", "residual_wh"])
    if len(y) < 4 or np.linalg.matrix_rank(x) < 3:
        return {"n": len(y), "status": "insufficient_data_or_rank"}, empty
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    prediction = x @ beta
    total = np.sum((y - y.mean()) ** 2)
    stats = {
        "n": len(y),
        "status": "ok",
        "intercept": float(beta[0]),
        "input_token_coefficient": float(beta[1]),
        "output_token_coefficient": float(beta[2]),
        "r_squared": float(1 - np.sum((y - prediction) ** 2) / total) if total > 0 else None,
    }
    return stats, pd.DataFrame(
        {
            "run_id": frame.loc[good.index, "run_id"].to_numpy(),
            "fitted_wh": prediction,
            "residual_wh": y - prediction,
        }
    )


def load_full(root: Path) -> tuple[pd.DataFrame, dict]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("milestone") != "P4 full":
        raise ValueError("Smoke/pilot data excluded from hypothesis scaffolds")
    data = pd.read_csv(root / "full.csv")
    if set(data["record_kind"]) != {"full"} or data["run_id"].duplicated().any():
        raise ValueError("Invalid or duplicate full-run rows")
    schedule = {j["run_id"]: j for j in manifest["schedule"]}
    if set(data["run_id"]) - schedule.keys():
        raise ValueError("Unexpected full-run row")
    for row in data.to_dict("records"):
        if any(
            row[k] != schedule[row["run_id"]][k]
            for k in ("stage", "model", "prompt_id", "task_id", "repeat")
        ):
            raise ValueError("Row differs from registered schedule")
    if not data["stage"].isin([1, 2]).all():
        raise ValueError("Invalid stage")
    if not data.loc[data.stage == 1, "repeat"].eq(1).all():
        raise ValueError("Stage 1 requires repeat 1 only")
    if not data["passed"].isin([True, False]).all():
        raise ValueError("Invalid pass indicators")
    return data, manifest


def summarize_stage1(frame: pd.DataFrame, *, draws: int) -> pd.DataFrame:
    """Each arm/model group has one outcome per task; stage 2 never enters."""
    if not frame["stage"].eq(1).all():
        raise ValueError("Do not pool stage-2 noise repeats into hypothesis estimates")
    records = []
    for (model, arm), group in frame.groupby(["model", "prompt_id"]):
        group = group.sort_values("task_id")
        if group["task_id"].duplicated().any():
            raise ValueError("Stage-1 tasks must be unique within each arm/model")
        row = {
            "model": model,
            "prompt_id": arm,
            "rows": len(group),
            "tool_mode": MODE,
            "missing_energy": int(group[NET].isna().sum()),
            "successes": int(group["passed"].sum()),
        }
        for field in ("input_tokens", "output_tokens", NET, GROSS, "passed"):
            stats = bootstrap_mean(
                group[field].to_numpy(dtype=float), seed=P4_ANALYSIS["seed"], draws=draws
            )
            row.update({f"{field}_{k}": v for k, v in stats.items()})
        for field in (NET, GROSS, "input_tokens", "output_tokens"):
            row[f"{field}_per_correct"] = per_correct(
                group[field].to_numpy(dtype=float), group["passed"].to_numpy()
            )
        records.append(row)
    return pd.DataFrame(records)


def noise_rows(data: pd.DataFrame) -> pd.DataFrame:
    """Stage-2 repeats 2/3 only; include missing count and variation in output length."""
    records = []
    for key, group in data[data.stage == 2].groupby(["model", "prompt_id", "task_id"]):
        if group["repeat"].duplicated().any() or not group["repeat"].isin([2, 3]).all():
            raise ValueError("Invalid stage-2 repeats")
        values = group[NET].dropna()
        records.append(
            {
                "model": key[0],
                "prompt_id": key[1],
                "task_id": key[2],
                "tool_mode": MODE,
                "rows": len(group),
                "energy_available": len(values),
                "energy_mean_wh": values.mean() if len(values) else None,
                "energy_sd_wh": values.std(ddof=1) if len(values) > 1 else None,
                "absolute_repeat_difference_wh": abs(values.iloc[0] - values.iloc[1])
                if len(values) == 2
                else None,
                "output_token_sd": group["output_tokens"].std(ddof=1) if len(group) > 1 else None,
            }
        )
    return pd.DataFrame(records)


def grouped_summaries(frame: pd.DataFrame, grouping: dict, draws: int) -> tuple[dict, dict]:
    """Only use frozen manifest labels; never derive groups from scored correctness."""
    tables, status = {}, {}
    for name in ("calibration", "reference_length"):
        labels = grouping.get(name, {})
        if not labels:
            status[name] = "unavailable: owner has not supplied frozen labels/rule"
            continue
        if not set(frame["task_id"]).issubset(labels):
            raise ValueError(f"Incomplete frozen {name} labels")
        if name == "reference_length" and not grouping.get("reference_length_rule"):
            raise ValueError("Frozen reference-length rule missing")
        eligible = frame[frame.prompt_id != "P0"].copy()
        eligible["group_label"] = eligible["task_id"].map(labels)
        pieces = []
        for label, part in eligible.groupby("group_label"):
            table = summarize_stage1(part, draws=draws)
            table["difficulty_group"] = label
            pieces.append(table)
        tables[name] = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
        status[name] = "frozen labels; P0 excluded"
    return tables, status


def figures(
    summary: pd.DataFrame, residuals: pd.DataFrame, output: Path, title_prefix: str = ""
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if summary.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for model, group in summary.groupby("model"):
        ax.scatter(group[f"{NET}_mean"], group["passed_mean"], label=model)
        for row in group.to_dict("records"):
            if row[f"{NET}_mean"] is not None and np.isfinite(row[f"{NET}_mean"]):
                ax.annotate(
                    row["prompt_id"],
                    (row[f"{NET}_mean"], row["passed_mean"]),
                    xytext=(4, 4),
                    textcoords="offset points",
                    fontsize=8,
                )
    ax.set(
        xlabel="Mean net post-load energy (Wh)",
        ylabel="Pass rate",
        title=title_prefix + "Stage 1: verified yield / Pareto scaffold",
    )
    ax.legend()
    fig.text(0.5, 0.01, MODE, ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(output / "pareto.png", dpi=160)
    plt.close(fig)
    if not residuals.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        for model, part in residuals.groupby("model"):
            ax.scatter(part["fitted_wh"], part["residual_wh"], s=15, alpha=0.6, label=model)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set(
            xlabel="Fitted net post-load energy (Wh)",
            ylabel="Residual (Wh)",
            title=title_prefix + "Stage 1: input/output-token OLS residual scaffold",
        )
        ax.legend()
        fig.text(0.5, 0.01, MODE, ha="center", fontsize=8)
        fig.tight_layout(rect=(0, 0.05, 1, 1))
        fig.savefig(output / "residuals.png", dpi=160)
        plt.close(fig)


def analyze(root: Path, output: Path, *, draws: int = P4_ANALYSIS["bootstrap_draws"]) -> dict:
    """Write separate derived scaffolds; leave model responses and source CSV unchanged."""
    if output.resolve() == root.resolve() or root.resolve() in output.resolve().parents:
        raise ValueError("Write analysis outside the raw run directory")
    source = (root / "full.csv").read_bytes()
    data, manifest = load_full(root)
    stage1 = data[data.stage == 1].copy()
    flags = stage1["energy_flags"].fillna("").str.split(";")
    low = flags.apply(lambda f: "post_load:low_resolution" in f)
    report = {
        "tool_mode": MODE,
        "analysis_settings": {**P4_ANALYSIS, "bootstrap_draws": draws},
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "record_kind": "full",
        "stage1_rows": len(stage1),
        "stage2_rows": int((data.stage == 2).sum()),
        "planned_stage1_rows": sum(j["stage"] == 1 for j in manifest["schedule"]),
        "interpretation": "OWNER TO WRITE; partial batches are provisional",
        "limitations": [
            "No input/output phase-energy attribution; pilot prompt windows low resolution.",
            "CodeCarbon constant-power estimate was unsuitable and is absent from scored runs.",
            "Estimated CPU package energy, approximate post-load boundary, one machine.",
            "Missing energy is not zero; negative net energy retained; failures included.",
            "Benchmark contamination possible; repeats include output variability.",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    # Loading overhead remains visible separately from the primary energy window.
    data.groupby(["stage", "model", "prompt_id"])["load_seconds"].agg(
        rows="size", available="count", mean="mean", sd="std", minimum="min", maximum="max"
    ).to_csv(output / "load-duration-summary.csv")
    noise_rows(data).to_csv(output / "stage2-noise.csv", index=False)
    all_low = (
        data["energy_flags"]
        .fillna("")
        .str.split(";")
        .apply(lambda f: "post_load:low_resolution" in f)
    )
    noise_rows(data[~all_low]).to_csv(
        output / "stage2-noise-without-primary-low-resolution.csv", index=False
    )
    for name, subset in (("all_rows", stage1), ("without_primary_low_resolution", stage1[~low])):
        destination = output / name
        destination.mkdir(exist_ok=True)
        summary = summarize_stage1(subset, draws=draws)
        summary.to_csv(destination / "summary.csv", index=False)
        fits, residuals = [], []
        for model, group in subset.groupby("model"):
            for field in (NET, GROSS):
                fit, residual = regression(group, field)
                fits.append({"model": model, "energy_column": field, **fit, "tool_mode": MODE})
                if field == NET and not residual.empty:
                    residual["model"] = model
                    residuals.append(residual)
        pd.DataFrame(fits).to_csv(destination / "regression.csv", index=False)
        combined = pd.concat(residuals, ignore_index=True) if residuals else pd.DataFrame()
        combined["tool_mode"] = MODE
        combined.to_csv(destination / "residuals.csv", index=False)
        grouped, status = grouped_summaries(subset, manifest.get("grouping", {}), draws)
        for grouping_name, table in grouped.items():
            table.to_csv(destination / f"{grouping_name}-groups.csv", index=False)
        report[name] = {
            "rows": len(subset),
            "energy_available": int(subset[NET].notna().sum()),
            "grouping": status,
        }
        figures(
            summary,
            combined,
            destination,
            "SYNTHETIC FIXTURE — " if manifest.get("synthetic_fixture") else "",
        )
    # Pass rate with all attempted outcomes remains visible even in a sensitivity report.
    data.groupby(["stage", "model", "prompt_id", "failure_type"], dropna=False).size().rename(
        "count"
    ).to_csv(output / "all-outcomes.csv")
    report["baseline_flag_counts"] = (
        data["energy_flags"].fillna("").str.split(";").explode().value_counts().to_dict()
    )
    (output / "report-scaffold.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    assert (root / "full.csv").read_bytes() == source
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path("results/p4-full"))
    parser.add_argument("--output", type=Path, default=Path("results/p4-analysis"))
    args = parser.parse_args()
    print(json.dumps(analyze(args.run, args.output), indent=2))


if __name__ == "__main__":
    main()
