"""Prepare or validate P3 safely; live pilot requires a separate explicit approval flag."""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    """Default preparation has no model, tracker, sensor or output-file side effects."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from prompt_energy.energy_report import export_energy
    from prompt_energy.hwinfo import LogFormat
    from prompt_energy.pilot import preflight, prepare_pilot, run_pilot

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("prepare", "preflight", "pilot", "report"), default="prepare", nargs="?"
    )
    parser.add_argument("--output", type=Path, default=Path("results/p3-pilot"))
    parser.add_argument("--hwinfo-log", type=Path)
    parser.add_argument("--hwinfo-version", default="")
    parser.add_argument(
        "--owner-approved", action="store_true", help="Use only AFTER owner approves the pilot"
    )
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--decimal", default=".")
    parser.add_argument("--date-format", default="%d.%m.%Y")
    parser.add_argument("--time-format", default="%H:%M:%S.%f")
    parser.add_argument("--utc-offset-minutes", type=int, default=330)
    parser.add_argument("--power-column", default="CPU Package Power [W]")
    parser.add_argument("--power-index", type=int)
    args = parser.parse_args()
    fmt = LogFormat(
        args.encoding,
        args.delimiter,
        args.decimal,
        args.date_format,
        args.time_format,
        args.utc_offset_minutes,
        args.power_column,
        args.power_index,
    )
    try:
        if args.command == "prepare":
            outcome = prepare_pilot()
        elif args.command == "report":
            outcome = export_energy(args.output.resolve())
        else:
            if args.command == "pilot" and not args.owner_approved:
                raise PermissionError("Owner has not approved the pilot; no calls made")
            if args.hwinfo_log is None:
                raise ValueError("Supply the actual --hwinfo-log CSV path")
            if args.command == "preflight":
                outcome = preflight(args.hwinfo_log, fmt)
            else:
                outcome = run_pilot(
                    args.output.resolve(),
                    args.hwinfo_log,
                    fmt,
                    args.hwinfo_version,
                    owner_approved=args.owner_approved,
                )
        print(json.dumps(outcome, indent=2, allow_nan=False))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"P3 stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
