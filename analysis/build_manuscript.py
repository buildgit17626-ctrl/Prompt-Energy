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
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build(source: Path, output: Path, *, append_comparisons: bool = True) -> None:
    """Render paragraphs, tables and figures without recalculating study outcomes."""
    fonts = Path("C:/Windows/Fonts")
    for name, file in [("Paper", "times.ttf"), ("PaperBold", "timesbd.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(fonts / file)))
    pdfmetrics.registerFontFamily("Paper", normal="Paper", bold="PaperBold", italic="Paper")
    body = ParagraphStyle(
        "Body",
        fontName="Paper",
        fontSize=14,
        leading=16.5,
        spaceAfter=6,
        splitLongWords=True,
        allowWidows=0,
        allowOrphans=0,
    )
    title = ParagraphStyle(
        "Title", parent=body, fontName="PaperBold", fontSize=21, leading=24, spaceAfter=12
    )
    head = ParagraphStyle(
        "Heading",
        parent=body,
        fontName="PaperBold",
        fontSize=17,
        leading=20,
        spaceBefore=7,
        spaceAfter=8,
        keepWithNext=True,
    )
    small = ParagraphStyle("Small", parent=body, fontSize=14, leading=16.5, spaceAfter=6)
    cell = ParagraphStyle("Cell", parent=small, fontSize=14, leading=16)
    width = A4[0] - 68
    story = []
    text = source.read_text(encoding="utf-8")
    document_title = next(line[2:].strip() for line in text.splitlines() if line.startswith("# "))
    main_text = text.split("---COMPARISON_SHEET---")[0]
    lines = main_text.splitlines()
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
            caption_index = i + 1
            while caption_index < len(lines) and not lines[caption_index].strip():
                caption_index += 1
            if caption_index < len(lines) and lines[caption_index].startswith("Figure "):
                group = [figure, Spacer(1, 5), Paragraph(escape(lines[caption_index]), small)]
                # Keep a section heading with its opening figure after text reflows.
                if story and isinstance(story[-1], Paragraph) and story[-1].style is head:
                    group.insert(0, story.pop())
                story.append(KeepTogether(group))
                i = caption_index
            else:
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
        str(output.with_suffix(".body.pdf")),
        pagesize=A4,
        leftMargin=34,
        rightMargin=34,
        topMargin=30,
        bottomMargin=32,
        title=document_title,
        author="",
    )

    def footer(canvas, document) -> None:
        canvas.saveState()
        canvas.setFont("Paper", 8)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(34, 17, "Prompt-energy report | 28 October 2026")
        canvas.drawRightString(A4[0] - 34, 17, str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    if not append_comparisons:
        output.with_suffix(".body.pdf").replace(output)
        return
    # Keep the 30-panel comparison on a single native-size page, with readable labels.
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import A1, landscape
    from reportlab.pdfgen.canvas import Canvas

    sheet = BytesIO()
    size = landscape(A1)
    canvas = Canvas(sheet, pagesize=size)
    canvas.setTitle("Supplementary prompt-category comparisons")
    image = Image(str(Path("results/p4-professor/comparison_sheet.png")))
    available_width = size[0] - 64
    height = image.imageHeight * available_width / image.imageWidth
    canvas.drawImage(
        str(Path("results/p4-professor/comparison_sheet.png")),
        32,
        size[1] - height - 28,
        width=available_width,
        height=height,
    )
    canvas.setFont("Paper", 14)
    canvas.drawString(32, 24, "Supplementary comparison sheet | Stage 1 | 28 October 2026")
    canvas.drawRightString(size[0] - 32, 24, "Single-page large-format appendix")
    canvas.showPage()
    canvas.save()
    sheet.seek(0)
    writer = PdfWriter()
    writer.append(PdfReader(output.with_suffix(".body.pdf")))
    writer.append(PdfReader(sheet))
    writer.add_metadata(
        {
            "/Title": document_title,
            "/Subject": "CPU experiment with supplementary category comparisons",
        }
    )
    with output.open("wb") as stream:
        writer.write(stream)
    output.with_suffix(".body.pdf").unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("docs/analysis/P4_MANUSCRIPT.md"))
    parser.add_argument("--output", type=Path, default=Path("output/pdf/P4_revised_manuscript.pdf"))
    parser.add_argument("--no-comparison-sheet", action="store_true")
    args = parser.parse_args()
    build(args.source, args.output, append_comparisons=not args.no_comparison_sheet)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
