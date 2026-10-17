import os
import time
from dataclasses import asdict

import pytest

from experiments.config import FEW_SHOT_EXAMPLES
from prompt_energy.sandbox import STATUSES, run_solution
from prompt_energy.tasks import Task, load_tasks

TASKS = load_tasks()
SIMPLE = Task("synthetic", "", "", "def check(candidate):\n    assert candidate() == 1", "answer")


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.task_id)
def test_reference_passes(task):
    result = run_solution(task, task.reference_source)
    assert result.passed, asdict(result)
    assert result.peak_memory_bytes > 0


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.task_id)
def test_wrong_solution_fails(task):
    source = f"def {task.entry_point}(*args, **kwargs):\n    return None\n"
    result = run_solution(task, source)
    assert result.status in {"failed", "runtime_error"}, asdict(result)


def test_runaway_killed_and_next_run_succeeds():
    start = time.monotonic()
    result = run_solution(SIMPLE, "def answer():\n    while True: pass", timeout_seconds=0.5)
    assert result.status == "timeout"
    assert time.monotonic() - start < 5
    assert run_solution(SIMPLE, "def answer():\n    return 1").passed


def test_memory_cap():
    result = run_solution(SIMPLE, "def answer():\n    return [0] * (10**9)", memory_mb=64)
    assert result.status == "memory_limit", asdict(result)


@pytest.mark.parametrize(
    "source",
    [
        "import os",
        "import socket",
        "import subprocess",
        "import ctypes",
        "from pathlib import Path",
        "import typing.io",
        "from math import *",
        "from . import math",
        "x = open('secret')",
        "x = exec('1')",
        "x = ().__class__",
        "x = getattr(1, 'real')",
        "x = __builtins__",
        "def answer():\n    return globals()",
        "import math as __builtins__",
    ],
)
def test_unsafe_source_rejected(source):
    assert run_solution(SIMPLE, source).status == "rejected"


def test_candidate_cannot_replace_check():
    source = "def check(candidate):\n    pass\ndef answer():\n    return 2"
    assert run_solution(SIMPLE, source).status == "failed"


def test_syntax_error_is_separate():
    result = run_solution(SIMPLE, "def broken(")
    assert result.status == "rejected"
    assert result.reason == "invalid_syntax"


def test_job_setup_fails_closed(monkeypatch):
    def denied(self, pid):
        raise OSError("simulated assignment failure")

    monkeypatch.setattr("prompt_energy.sandbox.WindowsJob.assign", denied)
    result = run_solution(SIMPLE, "def answer():\n    while True: pass")
    assert result.status == "infrastructure_error"
    assert "simulated assignment failure" in result.reason


def test_result_schema_and_seed():
    result = run_solution(SIMPLE, "def answer():\n    return 1", seed=123)
    assert set(asdict(result)) == {"status", "reason", "wall_seconds", "peak_memory_bytes", "seed"}
    assert result.status in STATUSES
    assert result.seed == 123
    assert result.wall_seconds >= 0


@pytest.mark.parametrize("runaway", [False, True])
def test_minimal_environment_and_temp_cleanup(monkeypatch, runaway):
    import prompt_energy.sandbox as sandbox

    actual_popen = sandbox.subprocess.Popen
    observed = {}

    def inspect(*args, **kwargs):
        observed.update(kwargs)
        observed["process"] = actual_popen(*args, **kwargs)
        return observed["process"]

    monkeypatch.setenv("STUDY_SECRET", "must-not-reach-child")
    monkeypatch.setattr(sandbox.subprocess, "Popen", inspect)
    body = "while True: pass" if runaway else "return 1"
    result = run_solution(SIMPLE, f"def answer():\n    {body}", timeout_seconds=1 if runaway else 5)
    assert result.status == ("timeout" if runaway else "passed")
    assert observed["process"].poll() is not None
    assert "STUDY_SECRET" not in observed["env"]
    assert set(observed["env"]) <= {"SystemRoot", "WINDIR", "TEMP", "TMP", "PYTHONHASHSEED"}
    assert observed["env"]["PYTHONHASHSEED"] == "1729"
    assert not os.path.exists(observed["cwd"])


def test_eval_is_arithmetic_only():
    assert run_solution(SIMPLE, "def answer():\n    return eval('2**3 - 7')").passed
    result = run_solution(SIMPLE, "def answer():\n    return eval('open(\"secret\")')")
    assert result.status == "runtime_error"
    assert result.reason == "ValueError"


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_invalid_deadline(timeout):
    with pytest.raises(ValueError):
        run_solution(SIMPLE, "pass", timeout_seconds=timeout)


@pytest.mark.parametrize("seed", [-1, 2**32, 0.5, True])
def test_invalid_seed(seed):
    with pytest.raises(ValueError, match="seed"):
        run_solution(SIMPLE, "pass", seed=seed)


def test_random_seed_is_repeatable():
    import random

    expected = random.Random(1729).randint(0, 1_000_000)
    task = Task(
        "seed", "", "", f"def check(candidate):\n    assert candidate() == {expected}", "answer"
    )
    source = "import random\ndef answer():\n    return random.randint(0, 1000000)"
    assert run_solution(task, source).passed
    assert run_solution(task, source).passed


@pytest.mark.parametrize("operation", ["socket.socket()", "socket.getaddrinfo('localhost', 80)"])
def test_network_operations_denied_even_from_trusted_checks(operation):
    # Deliberately bypass the candidate import policy to test the independent
    # audit layer, without opening a connection or relying on an external host.
    checks = (
        "import socket\ndef check(candidate):\n"
        "    try:\n"
        f"        {operation}\n"
        "    except PermissionError as error:\n"
        "        assert str(error) == 'network_access_denied'\n"
        "    else:\n"
        "        raise AssertionError('network operation was allowed')\n"
        "    assert candidate() == 1\n"
    )
    task = Task("network_probe", "", "", checks, "answer")
    result = run_solution(task, "def answer():\n    return 1")
    assert result.passed, asdict(result)


@pytest.mark.parametrize(
    "index,entry,checks",
    [
        (
            0,
            "lookup_status",
            "assert candidate({'a': 'ready'}, 'a') == 'ready'\n"
            "assert candidate({}, 'a') == 'unknown'",
        ),
        (1, "wrap_label", "assert candidate('hi') == '[hi]'\nassert candidate('') == '[]'"),
        (2, "count_tabs", "assert candidate('a\\tb\\t') == 2\nassert candidate(' ') == 0"),
    ],
)
def test_original_demonstrations_pass(index, entry, checks):
    test = "def check(candidate):\n" + "\n".join("    " + line for line in checks.splitlines())
    task = Task("original_demo", "", "", test, entry)
    result = run_solution(task, FEW_SHOT_EXAMPLES[index][1])
    assert result.passed, asdict(result)
