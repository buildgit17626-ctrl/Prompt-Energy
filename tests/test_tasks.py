import hashlib
import json
import random
import shutil

import pytest

from experiments.config import MODELS, PROMPTS, TASK_COUNT, TASK_IDS, TASK_SELECTION_SEED
from prompt_energy.tasks import DATA_DIR, load_tasks


def test_registration_and_order():
    expected = tuple(f"HumanEval/{i}" for i in sorted(
        random.Random(TASK_SELECTION_SEED).sample(range(164), TASK_COUNT)))
    assert TASK_IDS == expected
    assert tuple(task.task_id for task in load_tasks()) == expected
    assert len(set(TASK_IDS)) == 40
    assert MODELS == ("qwen2.5-coder:0.5b", "qwen2.5-coder:1.5b")
    assert set(PROMPTS) == {"P0", "P1", "P2", "P3_1", "P3_3", "P4", "P5"}
    assert PROMPTS["P3_1"]["examples"] == 1
    assert PROMPTS["P3_3"]["examples"] == 3


@pytest.mark.parametrize("ids", [("HumanEval/999",), ("HumanEval/1", "HumanEval/1")])
def test_invalid_selection_fails(ids):
    with pytest.raises(ValueError):
        load_tasks(ids)


def test_corrupt_archive_fails(tmp_path):
    shutil.copy(DATA_DIR / "manifest.json", tmp_path)
    (tmp_path / "HumanEval.jsonl.gz").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        load_tasks(data_dir=tmp_path)


def test_provenance():
    manifest = json.loads((DATA_DIR / "manifest.json").read_text())
    assert hashlib.sha256((DATA_DIR / "HumanEval.jsonl.gz").read_bytes()).hexdigest() == (
        manifest["sha256"])
    assert manifest["license"] == "MIT"
    assert "Copyright (c) OpenAI" in (DATA_DIR / "HumanEval.LICENSE").read_text()
