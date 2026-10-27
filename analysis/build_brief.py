"""Compatibility entry point: the revised manuscript supersedes the old P4 brief."""

import argparse
from pathlib import Path

from analysis.build_manuscript import build


def main() -> None:
    """Render the current manuscript at the historical brief path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("docs/analysis/P4_MANUSCRIPT.md"))
    parser.add_argument("--output", type=Path, default=Path("output/pdf/P4_baseline_brief.pdf"))
    args = parser.parse_args()
    if args.source.is_dir():
        parser.error("Use the editable manuscript Markdown as --source, not old evidence directory")
    build(args.source, args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
