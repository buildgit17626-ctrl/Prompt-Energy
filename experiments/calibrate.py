"""Prepare or run the separate owner-registered P4 calibration (no energy)."""

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from prompt_energy.calibration import labels, reference_lengths, run, schedule

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("prepare", "run", "labels"), default="prepare", nargs="?"
    )
    parser.add_argument("--output", type=Path, default=Path("results/p4-calibration-2026-10-21"))
    parser.add_argument("--owner-approved", action="store_true")
    args = parser.parse_args()
    if args.action == "prepare":
        result = {"schedule": schedule(), "reference_length": reference_lengths()}
    elif args.action == "labels":
        result = labels(args.output)
    else:
        result = run(args.output, approved=args.owner_approved)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
