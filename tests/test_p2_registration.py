from dataclasses import asdict

import pytest

from experiments.config import CACHE_POLICY, OLLAMA, PROMPTS, SYSTEM_PROMPT
from prompt_energy.extraction import extract_code, prepare_source, task_prelude
from prompt_energy.prompts import build_prompt
from prompt_energy.sandbox import run_solution
from prompt_energy.tasks import DATA_DIR, Task, load_tasks

LONG_INSTRUCTION = (
    "Please read the following Python function signature and docstring carefully. "
    "Complete the function so that it satisfies the docstring and handles edge cases "
    "correctly. Return only the code for the completed function, with no explanation."
)


def test_owner_registration_and_document_match():
    assert PROMPTS["P5"] == {"instruction": LONG_INSTRUCTION, "examples": 0}
    assert {k: OLLAMA[k] for k in ("num_thread", "num_ctx", "num_predict", "seed")} == {
        "num_thread": 8,
        "num_ctx": 4096,
        "num_predict": 768,
        "seed": 1729,
    }
    assert OLLAMA["temperature"] == 0
    doc = (DATA_DIR.parent / "docs" / "PROMPTS.md").read_text(encoding="utf-8")
    assert SYSTEM_PROMPT in doc
    for arm in PROMPTS.values():
        assert arm["instruction"] in doc
    assert CACHE_POLICY["on_reuse_keep_alive"] == 0
    assert CACHE_POLICY["compare_fields"] == (
        "response",
        "prompt_eval_count",
        "prompt_eval_duration",
    )


def test_exact_minimal_and_long_prompt_whitespace():
    task = Task("synthetic", 'def answer():\n    """Return 1."""\n\n', "SECRET", "SECRET", "answer")
    suffix = '\n\nTask:\ndef answer():\n    """Return 1."""\n'
    assert build_prompt(task, "P0") == "Complete the Python function." + suffix
    assert build_prompt(task, "P5") == LONG_INSTRUCTION + suffix
    assert "SECRET" not in build_prompt(task, "P3_3")
    assert build_prompt(task, "P3_1").count("Example task:\n") == 1
    assert build_prompt(task, "P3_3").count("Example task:\n") == 3


@pytest.mark.parametrize("label", ["python", "py", "", "Python"])
def test_last_relevant_block_not_last_arbitrary_block(label):
    source = "def answer():\n    return 2"
    response = (
        "```python\ndef answer():\n    return 1\n```\n"
        f"```{label}\n{source}\n```\n"
        "```python\ndef helper():\n    return 3\n```\n"
        "```javascript\ndef answer():\n    return 4\n```\n"
    )
    assert extract_code(response, "answer") == source


@pytest.mark.parametrize(
    "response",
    [
        "  def answer():\n    return 1  ",
        "prose only",
        "```python\ndef helper():\n    return 1\n```",
        "```python\ndef answer():\n    return 1",  # Unclosed fence.
        "```python\ndef answer(:\n    return 1\n```",  # Invalid block.
        '```python\ntext = "def answer():"\n```',  # Definition only inside string.
        "```python\ndef outer():\n    def answer():\n        return 1\n```",
    ],
)
def test_fallback_is_exact_whole_stripped_response(response):
    assert extract_code(response, "answer") == response.strip()


def test_prelude_preserves_imports_helpers_and_comments():
    prelude = "# trusted prompt\nimport math\n\ndef helper(x):\n    return math.ceil(x)\n\n"
    task = Task("synthetic", prelude + 'def answer():\n    """Return 2."""\n', "", "", "answer")
    source = "def answer():\n    return helper(1.5)"
    assert task_prelude(task) == prelude
    assert prepare_source(task, source) == prelude + source
    checked = Task(
        task.task_id,
        task.prompt,
        "",
        "def check(candidate):\n    assert candidate() == 2",
        "answer",
    )
    assert run_solution(checked, prepare_source(task, source)).passed


@pytest.mark.parametrize("task", load_tasks(), ids=lambda t: t.task_id)
def test_all_references_through_extraction_and_prelude(task):
    # Remove the reference prelude so the new path must restore its imports.
    prelude = task_prelude(task)
    reference_module = task.reference_source[len(prelude) :]
    response = f"```python\n{reference_module.rstrip()}\n```\n```py\nx = 1\n```"
    source = prepare_source(task, extract_code(response, task.entry_point))
    assert source == task.reference_source.rstrip()
    result = run_solution(task, source)
    assert result.passed, asdict(result)
