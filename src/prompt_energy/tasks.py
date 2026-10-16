"""Read the pinned benchmark as data; loading never executes its Python strings."""

import gzip
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from experiments.config import TASK_IDS

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class Task:
    task_id: str
    prompt: str
    canonical_solution: str
    test: str
    entry_point: str

    @property
    def reference_source(self) -> str:
        """HumanEval references are function-body continuations of the prompt."""
        return self.prompt + self.canonical_solution


def load_tasks(
    task_ids: tuple[str, ...] = TASK_IDS,
    data_dir: Path = DATA_DIR,
) -> tuple[Task, ...]:
    """Verify the dataset and return tasks in registered order, failing on omissions."""
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    archive = data_dir / "HumanEval.jsonl.gz"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest["sha256"]:
        raise ValueError("HumanEval checksum mismatch")
    records: dict[str, Task] = {}
    with gzip.open(archive, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if set(row) != set(Task.__dataclass_fields__):
                raise ValueError("Unexpected HumanEval fields")
            if not all(isinstance(value, str) and value for value in row.values()):
                raise ValueError("Empty or non-string HumanEval field")
            task = Task(**row)
            if task.task_id in records or not task.entry_point.isidentifier():
                raise ValueError("Duplicate task or invalid entry point")
            records[task.task_id] = task
    if set(records) != {f"HumanEval/{i}" for i in range(164)}:
        raise ValueError("Unexpected HumanEval population")
    if len(set(task_ids)) != len(task_ids):
        raise ValueError("Duplicate requested task")
    if missing := set(task_ids) - records.keys():
        raise ValueError(f"Missing task IDs: {sorted(missing)}")
    return tuple(records[key] for key in task_ids)
