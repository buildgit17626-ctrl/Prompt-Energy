"""Exact registered prompt assembly; reference solutions/tests are never included."""

from experiments.config import FEW_SHOT_EXAMPLES, PROMPT_ASSEMBLY, PROMPTS
from prompt_energy.tasks import Task


def build_prompt(task: Task, prompt_id: str) -> str:
    """Build the reviewed user prompt with explicit LF separators."""
    arm = PROMPTS[prompt_id]
    sections = [arm["instruction"]]
    for prompt, solution in FEW_SHOT_EXAMPLES[: arm["examples"]]:
        sections.append(
            PROMPT_ASSEMBLY["example_template"].format(
                example_prompt=prompt,
                example_solution=solution,
            )
        )
    sections.append(PROMPT_ASSEMBLY["task_template"].format(task_prompt=task.prompt.rstrip()))
    return PROMPT_ASSEMBLY["separator"].join(sections) + PROMPT_ASSEMBLY["final_newline"]
