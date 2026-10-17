"""Parent-side supervision; generated Python is never executed in this process."""

import json
import math
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from experiments.config import EXECUTION_SEED, SANDBOX
from prompt_energy.policy import check_source
from prompt_energy.tasks import Task
from prompt_energy.windows_job import WindowsJob

STATUSES = frozenset(
    {
        "passed",
        "failed",
        "rejected",
        "runtime_error",
        "timeout",
        "memory_limit",
        "infrastructure_error",
    }
)


@dataclass(frozen=True)
class TestResult:
    status: str
    reason: str
    wall_seconds: float
    peak_memory_bytes: int
    seed: int

    @property
    def passed(self) -> bool:
        return self.status == "passed"


@contextmanager
def _temporary_directory() -> Iterator[str]:
    temporary = tempfile.TemporaryDirectory(prefix="prompt-energy-")
    try:
        yield temporary.name
    finally:
        # Windows can briefly retain file locks after a worker has been reaped.
        # Retry only our own generated temp directory; never hide permanent errors.
        deadline = time.monotonic() + SANDBOX["cleanup_timeout_seconds"]
        while True:
            try:
                temporary.cleanup()
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(SANDBOX["cleanup_poll_seconds"])


def run_solution(
    task: Task,
    source: str,
    *,
    timeout_seconds: float = SANDBOX["timeout_seconds"],
    memory_mb: int = SANDBOX["memory_mb"],
    seed: int = EXECUTION_SEED,
) -> TestResult:
    """Test a complete function module; report every rejection or execution failure."""
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0 or memory_mb < 32:
        raise ValueError("Require a positive finite timeout and at least 32 MiB")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed must be an integer in [0, 2**32)")
    start = time.monotonic()
    peak = 0

    def result(status: str, reason: str = "") -> TestResult:
        return TestResult(status, reason, time.monotonic() - start, peak, seed)

    try:
        check_source(source, SANDBOX["max_source_bytes"])
    except ValueError as exc:
        return result("rejected", str(exc))
    process = None
    job = None
    try:
        with _temporary_directory() as directory:
            root = Path(directory)
            payload = {
                "source": source,
                "test": task.test,
                "entry_point": task.entry_point,
                "seed": seed,
            }
            (root / "input.json").write_text(json.dumps(payload), encoding="utf-8")
            (root / "candidate.py").write_text(source, encoding="utf-8")
            (root / "checks.py").write_text(task.test, encoding="utf-8")
            env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR") if key in os.environ}
            # -I ignores PYTHONHASHSEED; safe-path flags plus an explicit environment
            # keep imports isolated while fixing Python's hash randomization.
            env.update({"TEMP": directory, "TMP": directory, "PYTHONHASHSEED": str(seed)})
            job = WindowsJob(memory_mb * 1024**2)
            try:
                # Windows venv python.exe is a redirector which spawns a child.
                # Launch its base interpreter directly so the one-process cap
                # applies to the actual worker and cannot race that redirector.
                executable = getattr(sys, "_base_executable", sys.executable)
                process = subprocess.Popen(
                    [
                        executable,
                        "-P",
                        "-s",
                        "-S",
                        "-B",
                        str(Path(__file__).with_name("worker.py")),
                    ],
                    cwd=root,
                    env=env,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                job.assign(process.pid)
                process.stdin.write(b"G")
                process.stdin.close()
                while process.poll() is None:
                    peak = max(peak, job.peak_memory())
                    if time.monotonic() - start >= timeout_seconds:
                        return result("timeout", "wall_deadline_exceeded")
                    if peak >= memory_mb * 1024**2:
                        return result("memory_limit", "parent_memory_limit")
                    time.sleep(SANDBOX["poll_seconds"])
                peak = max(peak, job.peak_memory())
                output = root / "outcome.json"
                if process.returncode != 0 or not output.exists():
                    return result("infrastructure_error", f"worker_exit:{process.returncode}")
                if output.stat().st_size > 4096:
                    return result("infrastructure_error", "invalid_worker_output")
                outcome = json.loads(output.read_text(encoding="utf-8"))
                if (
                    not isinstance(outcome, dict)
                    or outcome.get("status")
                    not in {"passed", "failed", "runtime_error", "memory_limit"}
                    or not isinstance(outcome.get("reason"), str)
                ):
                    return result("infrastructure_error", "invalid_worker_output")
                return result(outcome["status"], outcome["reason"])
            finally:
                # Reap before deleting files; on timeout close kills the whole job.
                job.close()
                if process is not None:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
                    if process.stdin is not None:
                        process.stdin.close()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return result("infrastructure_error", f"{type(exc).__name__}:{exc}")
