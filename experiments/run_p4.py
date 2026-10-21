"""Prepare, preflight or explicitly run one P4 block; default makes no model calls."""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from prompt_energy.full_energy import export_full
    from prompt_energy.full_run import preflight, prepare, run_block
    from prompt_energy.hwinfo import LogFormat

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("prepare", "preflight", "run-block", "report", "calibrate"),
        nargs="?",
        default="prepare",
    )
    parser.add_argument("--owner-approved", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--hwinfo-log", type=Path)
    parser.add_argument("--hwinfo-version", default="")
    parser.add_argument("--encoding", default="cp1252")
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--decimal", default=".")
    parser.add_argument("--date-format", default="%d.%m.%Y")
    parser.add_argument("--time-format", default="%H:%M:%S.%f")
    parser.add_argument("--utc-offset-minutes", type=int, default=330)
    parser.add_argument("--power-column", default="CPU Package Power [W]")
    parser.add_argument("--power-index", type=int)
    args = parser.parse_args()
    if args.output is None:
        args.output = Path(
            "results/p4-calibration-2026-10-21"
            if args.command == "calibrate"
            else "results/p4-full"
        )
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
            result = prepare()
        elif args.command == "calibrate":
            from prompt_energy.calibration import run

            result = run(args.output.resolve(), approved=args.owner_approved)
        elif args.command == "report":
            result = {"rows": export_full(args.output.resolve())}
        else:
            if args.command == "run-block" and not args.owner_approved:
                raise PermissionError("Full run not approved; no requests made")
            if args.hwinfo_log is None:
                raise ValueError("Supply --hwinfo-log")
            result = (
                preflight(args.hwinfo_log, fmt)
                if args.command == "preflight"
                else run_block(
                    args.output.resolve(),
                    args.hwinfo_log,
                    fmt,
                    args.hwinfo_version,
                    owner_approved=args.owner_approved,
                )
            )
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"P4 stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
