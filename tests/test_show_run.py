"""A viewer must display evidence, never generate, execute, or modify it."""

import base64
import json

import pytest

from experiments.show_run import main, render_run
from prompt_energy.records import append_json, write_once
from prompt_energy.runner import registration


@pytest.fixture
def batch(tmp_path):
    request = {"system": "system sentinel", "prompt": "prompt sentinel", "options": {"seed": 1729}}
    # This intentionally dangerous text must only be displayed, never executed.
    response = (
        "```python\ndef has_close_elements(numbers, threshold):\n"
        '    raise RuntimeError("display only")\n```'
    )
    raw = {
        "request_id": "smoke-026",
        "request": request,
        "http_status": 200,
        "error": None,
        "body_base64": base64.b64encode(json.dumps({"response": response}).encode()).decode(),
    }
    append_json(tmp_path / "raw.jsonl", raw)
    append_json(
        tmp_path / "results.jsonl",
        {"row": {"run_id": "smoke-026"}, "reason": "saved failure sentinel"},
    )
    write_once(
        tmp_path / "manifest.json",
        {
            "registration": registration(),
            "schedule": [
                {
                    "run_id": "smoke-026",
                    "task_id": "HumanEval/0",
                    "model": "fixture",
                    "prompt_id": "P2",
                }
            ],
        },
    )
    return tmp_path


def test_display_all_stages_without_execution_or_mutation(batch, monkeypatch):
    from prompt_energy import ollama, sandbox

    monkeypatch.setattr(ollama.Client, "exchange", lambda *a: pytest.fail("No model calls"))
    monkeypatch.setattr(sandbox, "run_solution", lambda *a: pytest.fail("No execution"))
    before = {p.name: p.read_bytes() for p in batch.iterdir()}
    text = render_run(batch, "smoke-026")
    for section in (
        "SAVED SYSTEM PROMPT",
        "SAVED USER PROMPT",
        "RAW RESPONSE TEXT",
        "EXTRACTED CODE",
        "TRUSTED TASK PRELUDE",
        "COMBINED SANDBOX SOURCE",
        "SAVED TEST RESULT",
        "BENCHMARK CHECKS",
    ):
        assert section in text
    assert 'raise RuntimeError("display only")' in text
    assert "system sentinel" in text and "prompt sentinel" in text
    assert "saved failure sentinel" in text and "RECONSTRUCTION WARNING" not in text
    assert before == {p.name: p.read_bytes() for p in batch.iterdir()}


def test_missing_and_duplicate_ids_fail(batch):
    with pytest.raises(ValueError, match="found 0"):
        render_run(batch, "missing")
    raw = json.loads((batch / "raw.jsonl").read_text())
    append_json(batch / "raw.jsonl", raw)
    with pytest.raises(ValueError, match="found 2"):
        render_run(batch, "smoke-026")


def test_missing_result_is_labelled_not_invented(batch):
    (batch / "results.jsonl").unlink()
    assert "No saved result" in render_run(batch, "smoke-026")


def test_non_json_http_error_body_is_visible(batch):
    raw = json.loads((batch / "raw.jsonl").read_text())
    raw.update(http_status=500, body_base64=base64.b64encode(b"upstream failure\xff").decode())
    (batch / "raw.jsonl").write_text(json.dumps(raw) + "\n")
    text = render_run(batch, "smoke-026")
    assert "500" in text and "upstream failure\\xff" in text
    assert "EXTRACTED CODE" not in text


def test_source_drift_warns_about_reconstruction(batch):
    manifest = json.loads((batch / "manifest.json").read_text())
    manifest["registration"]["src/prompt_energy/extraction.py"] = "different"
    (batch / "manifest.json").write_text(json.dumps(manifest))
    text = render_run(batch, "smoke-026")
    assert "RECONSTRUCTION WARNING" in text and "extraction.py" in text


def test_cli_success_and_missing_id_exit_codes(batch, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["show_run", "smoke-026", "--output", str(batch)])
    assert main() == 0
    assert "SAVED TEST RESULT" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["show_run", "missing", "--output", str(batch)])
    assert main() == 1
    assert "Cannot show run" in capsys.readouterr().err
