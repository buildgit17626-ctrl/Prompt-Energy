"""Build the owner-reviewed P4 PDF with the separate bundled PDF runtime."""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#17324d")
BLUE = colors.HexColor("#2563eb")
LIGHT = colors.HexColor("#eef3f8")


def build(source: Path, target: Path) -> None:
    """Compose a fixed four-page review brief; all quantitative values come from evidence."""
    info = json.loads((source / "evidence.json").read_text())
    font_dir = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("Study", str(font_dir / "arial.ttf")))
    pdfmetrics.registerFont(TTFont("StudyBold", str(font_dir / "arialbd.ttf")))
    pdfmetrics.registerFontFamily("Study", normal="Study", bold="StudyBold", italic="Study")
    body = ParagraphStyle(
        "StudyBody", fontName="Study", fontSize=9.2, leading=12.2, textColor=NAVY, spaceAfter=6
    )
    small = ParagraphStyle("StudySmall", parent=body, fontSize=7.8, leading=10, spaceAfter=4)
    title = ParagraphStyle(
        "StudyTitle", parent=body, fontName="StudyBold", fontSize=23, leading=27, spaceAfter=10
    )
    heading = ParagraphStyle(
        "StudyHeading",
        parent=body,
        fontName="StudyBold",
        fontSize=13,
        leading=16,
        spaceBefore=6,
        spaceAfter=8,
    )
    eyebrow = ParagraphStyle(
        "StudyEyebrow", parent=small, textColor=BLUE, fontName="StudyBold", spaceAfter=9
    )
    width = A4[0] - 80
    story = []

    def p(text: str, style=body) -> Paragraph:
        return Paragraph(text, style)

    def add(text: str, style=body) -> None:
        story.append(p(text, style))

    def table(rows: list, widths: list[float]) -> None:
        data = [[p(str(cell), small) for cell in row] for row in rows]
        obj = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
        obj.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#a8b6c5")),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.25, LIGHT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(obj)
        story.append(Spacer(1, 8))

    def fig(name: str, ratio: float, caption: str) -> None:
        story.append(Image(str(source / f"{name}.png"), width=width, height=width * ratio))
        add(caption, small)

    def row(model: str, arm: str) -> dict:
        return next(
            r
            for r in info["tables"]["summary"]
            if r["model"].endswith(model) and r["prompt_id"] == arm
        )

    p1, few = row("1.5b", "P1"), row("1.5b", "P3_1")
    add("P4 BASELINE EXPERIMENT  |  DESCRIPTIVE REVIEW DRAFT", eyebrow)
    add("Prompt design and the energy<br/>cost of correct code", title)
    add(
        "Dhruv Brahmbhatt | Prepared for professor discussion | "
        + datetime.now(timezone(timedelta(minutes=330))).strftime("%d %B %Y"),
        small,
    )
    story.append(HRFlowable(width="100%", color=BLUE, thickness=1.5, spaceAfter=12))
    add(
        f"<b>Main trade-off:</b> on the 1.5B model, code-only P1 passed "
        f"{p1['successes']}/40 tasks; one-example P3_1 passed {few['successes']}/40. "
        f"P1 used {p1['cpu_pkg_energy_wh_mean'] * 1000:.2f} mWh net per attempt versus "
        f"{few['cpu_pkg_energy_wh_mean'] * 1000:.2f} mWh. One additional correct task "
        f"is not evidence of a reliable accuracy advantage."
    )
    table(
        [
            ["Registered design", "Execution and measurement"],
            [
                "Stage 1: 40 tasks x 7 arms x 2 models = 560 attempts. One repeat each.",
                "Python 3.13.7; Ollama 0.40.6; qwen2.5-coder 0.5B/1.5B, Q4_K_M; "
                "i5-13420H, 16 GB RAM, CPU only.",
            ],
            [
                "Stage 2: 10 seeded tasks x 7 arms x 2 models x 2 extra repeats = "
                "280. Noise diagnostics only.",
                "Temperature 0; seed 1729; context 4096; output cap 768; 8 CPU "
                "threads; cache-avoiding unloads.",
            ],
            [
                "Correctness: fixed extraction plus restricted subprocess tests. "
                "Failures and truncations retained.",
                "HWiNFO 500 ms CPU Package Power; trapezoidal integration. "
                "Approximate post-load window; gross and block-start-idle-adjusted net.",
            ],
        ],
        [width / 2] * 2,
    )
    add("Measurement quality limits the strength of conclusions", heading)
    q1, q2 = info["quality"]["1"], info["quality"]["2"]
    add(
        f"All {q1['rows']} stage-1 energy estimates exist, but all carry baseline "
        f"drift: idle power fell from 17.55 to 11.52 W. {q1['low_resolution']} short "
        f"windows are excluded in the registered sensitivity view (490 remain). Stage "
        f"2 has {q2['energy_available']}/280 energy values and "
        f"{info['complete_energy_pairs']}/140 complete repeat pairs; 148 rows lack an "
        f"end baseline. Missing values remain missing. No input/output phase-energy attribution."
    )
    add("Registered expectations and bounded readings", heading)
    table(
        [
            ["ID", "Expectation (shortened)", "Descriptive reading"],
            [
                "H1",
                "Output tokens explain much energy/time variation.",
                "Strong association; joint OLS is not an isolated contribution or causal test.",
            ],
            [
                "H2",
                "Concise output saves cost; group-dependent accuracy.",
                "Cost reductions observed; success is model/group-dependent.",
            ],
            [
                "H3",
                "Examples add input cost and may improve verified yield.",
                "Mixed: 1.5B gains with one example; 0.5B loses successes.",
            ],
            [
                "H4",
                "Step-by-step output raises cost; benefits on harder tasks.",
                "High output/cost observed; no universal accuracy advantage established.",
            ],
            [
                "H5",
                "Longer code-only demand raises prompt cost, little total change.",
                "P5/P1 outputs and whole energies are close; phase-energy cost unmeasurable.",
            ],
        ],
        [27, 211, width - 238],
    )
    add(
        "H1-H5 remain as registered in SPEC. Later owner expectations are exploratory "
        "unless prior dated evidence exists. This draft combines owner notes with "
        "verified corrections; it is not a formal significance claim.",
        small,
    )

    story.append(PageBreak())
    add("01 / Correctness and verified yield", title)
    fig(
        "01_accuracy",
        3.8 / 10.5,
        "Figure 1. Stage-1 pass rates with 95% task-bootstrap intervals (2,000 draws, "
        "seed 1729). Counts inside bars use all 40 attempts. Intervals do not account "
        "for systematic measurement error.",
    )
    fig(
        "03_verified_cost",
        3.8 / 10.5,
        "Figure 2. Estimated CPU package energy per correct solution, gross and net. "
        "Numerator includes every attempted solution, including failures. These "
        "aggregate ratios have no uncertainty intervals in this packet.",
    )
    add("Corrections to the initial expectations", heading)
    add(
        "<b>P1 is efficient, not best in every metric.</b> P3_1 has the largest 1.5B "
        "pass count (30 versus 29). For 0.5B, P3_3 has the lowest mean energy but the "
        "lowest pass count (19/40); its cost per correct exceeds P1's. P2/P4 are "
        "expensive without being uniformly least accurate."
    )
    add(
        "<b>Model size is not a universal energy ranking.</b> The 1.5B model has "
        "higher pass counts for every arm, yet energy direction depends on the "
        "prompt. Across matched task/arm cases, only 0.5B passed in 21 cases and only "
        "1.5B in 60. More parameters do not imply fewer generation steps, and smaller "
        "models do not invoke extra networks to reach a conclusion."
    )

    story.append(PageBreak())
    add("02 / Output length and energy", title)
    fig(
        "02_output_energy",
        6.7 / 10.5,
        "Figure 3. Mean generated tokens and gross/net energy per attempt with "
        "registered bootstrap intervals. Output length varies; 768 is a ceiling. All "
        "560 stage-1 energies have baseline drift.",
    )
    fig(
        "04_token_energy",
        4.0 / 10.5,
        "Figure 4. Each point is one stage-1 request, including failures. Strong "
        "association does not establish that token length is the only energy "
        "determinant. The 280 requests per model reuse 40 tasks.",
    )
    fits = [r for r in info["tables"]["regression"] if r["energy_column"] == "cpu_pkg_energy_wh"]
    add(
        "Joint OLS on input and output token counts: "
        + "; ".join(
            f"{r['model'].split(':')[-1]} net R-squared {r['r_squared']:.3f} (n={r['n']})"
            for r in fits
        )
        + ". These are in-sample fits; they do not separately quantify input/output energy "
        "or establish output dominance.",
        small,
    )

    story.append(PageBreak())
    add("03 / Robustness and limitations", title)
    fig(
        "05_resolution_sensitivity",
        3.8 / 10.5,
        "Figure 5. Registered exclusion of post-load windows shorter than 3 seconds. "
        "Per-arm counts differ, so changes reflect a different task mix as well as "
        "removal of short windows. All-attempt correctness stays in Figure 1.",
    )
    fig(
        "06_frozen_groups",
        6.7 / 10.5,
        "Figure 6. Frozen calibration groups (26 solved / 14 failed) and "
        "reference-length groups (21 short / 19 long; median six lines). P0 excluded. "
        "Small groups and single-run labels support descriptive comparisons only.",
    )
    add(
        "Stage 2: only 64/140 complete energy pairs; missingness followed interrupted "
        "blocks. Repeat spread mixes output variation, block conditions and sensor "
        "noise. The separate repeat-variability figure retains available-pair counts. "
        "One machine, small task set, possible benchmark contamination and "
        "approximate load boundaries limit generalisation.",
        small,
    )
    add(
        "Sources: SPEC and frozen config; original P4 journals and full.csv; "
        "registered summary/group tables. Context: Schwartz et al., Green AI (2020); "
        "Poddar et al., Towards Sustainable NLP (NAACL 2025); Chen et al., Evaluating "
        "Large Language Models Trained on Code (2021). Full citations in "
        "docs/REFERENCES.md. Reproduction and all seven PNG/SVG figures are included "
        "in the companion packet.",
        small,
    )
    add("Evidence SHA-256: " + info["source_sha256"], small)

    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=35,
        bottomMargin=35,
        title="Prompt design and energy: P4 baseline experiment",
        author="Dhruv Brahmbhatt",
        pageCompression=1,
    )

    def footer(canvas, document) -> None:
        canvas.saveState()
        canvas.setFont("Study", 7)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(
            40, 18, "P4 baseline experiment | Owner review draft | Estimated CPU package energy"
        )
        canvas.drawRightString(A4[0] - 40, 18, str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("results/p4-presentation"))
    parser.add_argument("--output", type=Path, default=Path("output/pdf/P4_baseline_brief.pdf"))
    args = parser.parse_args()
    build(args.source, args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
