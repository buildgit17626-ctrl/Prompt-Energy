"""Classify a saved generation without ever executing candidate code in the parent."""

import ast
import re
from dataclasses import asdict

from experiments.config import OLLAMA
from prompt_energy.extraction import extract_code, prepare_source
from prompt_energy.sandbox import run_solution
from prompt_energy.tasks import Task


def evaluate(task: Task, response: dict) -> tuple[str, str, dict]:
    """Apply the pre-registered failure precedence and preserve sandbox details."""
    if response.get("done_reason") == "length" or response["eval_count"] >= OLLAMA["num_predict"]:
        return "truncated", "Output limit reached", {}
    code = extract_code(response["response"], task.entry_point)
    if not code:
        return "no_code", "Empty response", {}
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError) as exc:
        failure = "syntax_error" if re.search(r"\bdef\s+\w+", code) else "no_code"
        return failure, str(exc), {}
    if not any(isinstance(n, ast.FunctionDef) and n.name == task.entry_point for n in tree.body):
        return "no_code", "No required top-level function", {}
    result = run_solution(task, prepare_source(task, code))
    mapping = {
        "passed": "",
        "failed": "test_failed",
        "runtime_error": "test_failed",
        "rejected": "policy_rejected",
        "timeout": "timeout",
        "memory_limit": "memory_limit",
        "infrastructure_error": "infrastructure_error",
    }
    return mapping[result.status], result.reason, asdict(result)
