"""Read a recorded run without generating, executing, or modifying anything."""

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path


def _one(rows: list[dict], field: str, value: str) -> dict:
    matches = [row for row in rows if row.get(field) == value]
    if len(matches) != 1:
        raise ValueError(f"Expected one {field}={value}; found {len(matches)}")
    return matches[0]


def render_run(root: Path, run_id: str) -> str:
    """Show saved evidence and a labelled reconstruction; never run the solution."""
    from prompt_energy.extraction import extract_code, prepare_source, task_prelude
    from prompt_energy.records import read_jsonl
    from prompt_energy.tasks import DATA_DIR, load_tasks

    raw = _one(read_jsonl(root / "raw.jsonl"), "request_id", run_id)
    results = read_jsonl(root / "results.jsonl")
    matches = [record for record in results if record["row"]["run_id"] == run_id]
    if len(matches) > 1:
        raise ValueError(f"Duplicate result: {run_id}")
    result = matches[0] if matches else None
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    job = _one(manifest["schedule"], "run_id", run_id)
    task = load_tasks((job["task_id"],))[0]
    request = raw.get("request") or {}
    body = base64.b64decode(raw["body_base64"], validate=True)
    try:
        response = json.loads(body)
    except (ValueError, UnicodeError):
        response = None
    text = response.get("response") if isinstance(response, dict) else None
    parts = [
        f"Run: {run_id} | {job['task_id']} | {job['prompt_id']} | {job['model']}",
        "READ ONLY: no model call, candidate execution or file modification.",
    ]

    def section(title: str, content: str) -> None:
        parts.extend([f"\n=== {title} ===", content])

    watched = (
        "experiments/config.py",
        "src/prompt_energy/extraction.py",
        "src/prompt_energy/tasks.py",
    )
    mismatched = [
        name
        for name in watched
        if manifest["registration"].get(name)
        != hashlib.sha256((DATA_DIR.parent / name).read_bytes()).hexdigest()
    ]
    if mismatched:
        section(
            "RECONSTRUCTION WARNING",
            "Current files differ from registration: "
            + ", ".join(mismatched)
            + ". Extracted/combined code below is a current reconstruction.",
        )
    section("SAVED SYSTEM PROMPT", request.get("system", "<not present>"))
    section("SAVED USER PROMPT", request.get("prompt", "<not present>"))
    section("SAVED OPTIONS", json.dumps(request.get("options"), indent=2))
    section(
        "SAVED HTTP STATUS / ERROR",
        json.dumps(
            {
                "http_status": raw["http_status"],
                "error": raw["error"],
            },
            indent=2,
        ),
    )
    section(
        "RAW RESPONSE TEXT",
        text
        if isinstance(text, str)
        else "<No response string; HTTP body follows>\n"
        + body.decode("utf-8", errors="backslashreplace"),
    )
    if isinstance(text, str):
        extracted = extract_code(text, task.entry_point)
        section("EXTRACTED CODE (reconstructed)", extracted)
        section("TRUSTED TASK PRELUDE", task_prelude(task))
        section("COMBINED SANDBOX SOURCE (reconstructed)", prepare_source(task, extracted))
    section(
        "SAVED TEST RESULT (not rerun)",
        json.dumps(result, indent=2) if result else "<No saved result; raw response was retained>",
    )
    section("BENCHMARK CHECKS (display only)", task.test)
    return "\n".join(parts) + "\n"


def main() -> int:
    """Print one saved scored run from the default smoke folder or --output."""
    repository = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repository / "src"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--output", type=Path, default=repository / "results" / "p2-smoke")
    args = parser.parse_args()
    try:
        print(render_run(args.output, args.run_id), end="")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Cannot show run: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
