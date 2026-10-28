"""Public exports must preserve raw response bytes and numerical evidence."""

import json

from experiments.export_public import export_file, redact


def test_redaction_preserves_opaque_response_bytes() -> None:
    value = {
        "path": "C:\\Users\\Someone\\study\\results",
        "request": {"prompt": "Complete the function."},
        "body_base64": "EXACT_SAVED_BYTES",
    }
    output = redact(value)
    assert output["path"] == "<USER_HOME>\\study\\results"
    assert output["request"] == value["request"]
    assert output["body_base64"] == value["body_base64"]
    assert value["path"].startswith("C:")


def test_numeric_csv_is_byte_identical(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("experiments.export_public.ROOT", tmp_path)
    source = tmp_path / "full.csv"
    source.write_bytes(b"passed,energy\r\nFalse,\r\nTrue,0.01234\r\n")
    target = tmp_path / "public/full.csv"
    record = export_file(source, target)
    assert target.read_bytes() == source.read_bytes()
    assert record["source_sha256"] == record["export_sha256"]
    assert not record["changed"]


def test_journal_redaction_retains_failures_and_nulls(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("experiments.export_public.ROOT", tmp_path)
    source = tmp_path / "results.jsonl"
    row = {"passed": False, "energy": None, "path": "C:/Users/Someone/x"}
    source.write_text(json.dumps(row) + "\n", encoding="utf-8")
    target = tmp_path / "public/results.jsonl"
    record = export_file(source, target)
    result = json.loads(target.read_text())
    assert result == {"passed": False, "energy": None, "path": "<USER_HOME>/x"}
    assert json.loads(source.read_text()) == row
    assert record["changed"]
