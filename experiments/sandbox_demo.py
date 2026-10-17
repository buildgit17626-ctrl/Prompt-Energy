"""Run five authored snippets through the existing P1 subprocess restrictions."""

import sys
from pathlib import Path


def main() -> int:
    """Print each outcome and exit nonzero if the safeguards differ from expectations."""
    # Permit the documented -m command from a fresh checkout without installing
    # the src-layout library or asking the owner to configure PYTHONPATH.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from experiments.config import SANDBOX, SANDBOX_DEMO_CASES
    from prompt_energy.sandbox import run_solution
    from prompt_energy.tasks import Task

    task = Task(
        "demo/answer", "", "", "def check(candidate):\n    assert candidate() == 42", "answer"
    )
    print(f"Python {sys.version.split()[0]} | authored snippets, no model calls", flush=True)
    print(
        f"Limits: {SANDBOX['timeout_seconds']} s, {SANDBOX['memory_mb']} MiB; "
        "Python restrictions + Windows Job Object, not an OS security sandbox.",
        flush=True,
    )
    matched = 0
    for label, source, expected in SANDBOX_DEMO_CASES:
        outcome = run_solution(task, source)
        matched += outcome.status == expected
        print(
            f"{label:14} expected={expected:12} actual={outcome.status:20} "
            f"reason={outcome.reason or '-'}",
            flush=True,
        )
    print(f"{matched}/{len(SANDBOX_DEMO_CASES)} expected outcomes observed.", flush=True)
    return 0 if matched == len(SANDBOX_DEMO_CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
