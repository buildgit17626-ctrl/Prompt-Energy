"""One source-selection rule for all arms; parsing here never executes code."""

import ast
import re

from experiments.config import EXTRACTION
from prompt_energy.tasks import Task


def _defines_entry(source: str, entry_point: str) -> bool:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return False
    return any(isinstance(node, ast.FunctionDef) and node.name == entry_point for node in tree.body)


def extract_code(response: str, entry_point: str) -> str:
    """Choose the last complete eligible block defining the entry, else all text.

    Track even unsupported fences so their closing delimiters cannot become
    spurious openings. Never merge, repair or execute response fragments.
    """
    selected = None
    fence_size = 0
    label = ""
    body: list[str] = []
    for line in response.splitlines(keepends=True):
        if not fence_size:
            opening = re.fullmatch(r"[ \t]*(`{3,})([^`\r\n]*)[\r\n]*", line)
            if opening:
                fence_size = len(opening[1])
                label = opening[2].strip().lower()
                body = []
        elif re.fullmatch(r"[ \t]*`{" + str(fence_size) + r",}[ \t]*[\r\n]*", line):
            candidate = "".join(body).strip()
            if label in EXTRACTION["fence_labels"] and _defines_entry(candidate, entry_point):
                selected = candidate
            fence_size = 0
        else:
            body.append(line)
    return selected if selected is not None else response.strip()


def task_prelude(task: Task) -> str:
    """Return unchanged prompt text before the target's definition/decorators."""
    tree = ast.parse(task.prompt)
    target = next(
        (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == task.entry_point),
        None,
    )
    if target is None:
        raise ValueError(f"Task prompt lacks target function: {task.task_id}")
    first_line = min([target.lineno] + [n.lineno for n in target.decorator_list])
    return "".join(task.prompt.splitlines(keepends=True)[: first_line - 1])


def prepare_source(task: Task, extracted_code: str) -> str:
    """Prepend the task's imports/helpers; the runner checks the combined module."""
    return task_prelude(task) + extracted_code
