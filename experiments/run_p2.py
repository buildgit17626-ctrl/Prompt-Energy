"""Run the approved P2 smoke; the output directory is also the resume identifier."""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    """Expose only the P2 smoke, with no automatic full study or energy run."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from prompt_energy.runner import run_smoke

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/p2-smoke"))
    args = parser.parse_args()
    try:
        print(json.dumps(run_smoke(args.output.resolve()), indent=2), flush=True)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"P2 stopped: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
