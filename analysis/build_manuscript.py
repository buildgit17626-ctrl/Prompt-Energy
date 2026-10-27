"""Render the editable manuscript with the separate bundled PDF runtime."""

import argparse
import re
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build(source: Path, output: Path) -> None:
    """Render paragraphs, tables and figures without recalculating study outcomes."""
    fonts = Path("C:/Windows/Fonts")
    for name, file in [("Paper", "times.ttf"), ("PaperBold", "timesbd.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(fonts / file)))
    pdfmetrics.registerFontFamily("Paper", normal="Paper", bold="PaperBold", italic="Paper")
    body = ParagraphStyle(
        "Body", fontName="Paper", fontSize=10.5, leading=13.4, spaceAfter=8, splitLongWords=True
    )
    title = ParagraphStyle(
        "Title", parent=body, fontName="PaperBold", fontSize=21, leading=24, spaceAfter=12
    )
    head = ParagraphStyle(
        "Heading",
        parent=body,
        fontName="PaperBold",
        fontSize=13,
        leading=16,
        spaceBefore=7,
        spaceAfter=8,
        keepWithNext=True,
    )
    small = ParagraphStyle("Small", parent=body, fontSize=8.6, leading=10.5, spaceAfter=6)
    cell = ParagraphStyle("Cell", parent=small, fontSize=8.3, leading=10)
    width = A4[0] - 84
    story = []
    lines = source.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line == "---PAGE---":
            story.append(PageBreak())
        elif line.startswith("!["):
            match = re.fullmatch(r"!\[.*\]\((.*)\)", line)
            if match is None:
                raise ValueError("Invalid image reference")
            path = (source.parent / match[1]).resolve()
            figure = Image(str(path))
            figure.drawHeight *= width / figure.drawWidth
            figure.drawWidth = width
            story.extend([figure, Spacer(1, 5)])
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append([Paragraph(escape(c), cell) for c in cells])
                i += 1
            n = len(rows[0])
            fractions = {
                3: [0.12, 0.75, 0.13],
                5: [0.1, 0.13, 0.29, 0.31, 0.17],
                6: [0.1, 0.12, 0.14, 0.2, 0.22, 0.22],
            }.get(n, [1 / n] * n)
            table = Table(
                rows, colWidths=[width * f for f in fractions], repeatRows=1, hAlign="LEFT"
            )
            table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf1f4")),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.black),
                        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.black),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.extend([table, Spacer(1, 8)])
            continue
        elif line.startswith("# "):
            story.append(Paragraph(escape(line[2:]), title))
        elif line.startswith("## "):
            story.append(Paragraph(escape(line[3:]), head))
        else:
            style = small if line.startswith(("Figure ", "Table ", "[")) else body
            story.append(Paragraph(escape(line), style))
        i += 1
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=42,
        rightMargin=42,
        topMargin=35,
        bottomMargin=38,
        title="Explicit code-only instructions and the energy cost of correct code",
        author="Dhruv Brahmbhatt",
    )

    def footer(canvas, document) -> None:
        canvas.saveState()
        canvas.setFont("Paper", 8)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(
            42, 21, "Prompt-energy experiment | Author-review draft | 27 October 2026"
        )
        canvas.drawRightString(A4[0] - 42, 21, str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("docs/analysis/P4_MANUSCRIPT.md"))
    parser.add_argument("--output", type=Path, default=Path("output/pdf/P4_revised_manuscript.pdf"))
    args = parser.parse_args()
    build(args.source, args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
