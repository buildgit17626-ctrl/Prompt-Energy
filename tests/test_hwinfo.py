"""Synthetic CSVs cover explicit formats, clocks, malformed data and growing logs."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from prompt_energy.hwinfo import LogFormat, capture_log, parse_log, preflight_log


def log_text(rows, header="Date,Time,CPU Package Power [W]"):
    return (header + "\n" + "\n".join(rows) + "\n").encode()


ROWS = ["19.10.2026,12:00:00.000,10", "19.10.2026,12:00:00.500,20"]
FMT = LogFormat()


def test_millisecond_timezone_conversion():
    samples = parse_log(log_text(ROWS), FMT)
    assert samples[0].timestamp == datetime(2026, 10, 19, 6, 30, tzinfo=UTC).timestamp()
    assert samples[1].timestamp - samples[0].timestamp == 0.5
    assert [s.watts for s in samples] == [10, 20]


def test_semicolon_decimal_comma_and_bom():
    data = (
        "\ufeffDate;Time;CPU Package Power [W]\n"
        "19.10.2026;12:00:00.000;10,5\n19.10.2026;12:00:00.500;20,5\n"
    )
    assert parse_log(data.encode(), replace(FMT, delimiter=";", decimal=","))[0].watts == 10.5


@pytest.mark.parametrize("power", ["NaN", "inf", "-1", "N/A", ""])
def test_invalid_power_is_not_silently_skipped(power):
    with pytest.raises(ValueError):
        parse_log(log_text([ROWS[0], f"19.10.2026,12:00:00.500,{power}"]), FMT)


@pytest.mark.parametrize("time", ["12:00:00.000", "11:59:59.500"])
def test_duplicate_or_reversed_time_rejected(time):
    with pytest.raises(ValueError, match="Duplicate/backward"):
        parse_log(log_text([ROWS[0], f"19.10.2026,{time},20"]), FMT)


def test_duplicate_power_header_requires_explicit_index():
    data = log_text(
        [row + ",30" for row in ROWS], "Date,Time,CPU Package Power [W],CPU Package Power [W]"
    )
    with pytest.raises(ValueError, match="ambiguous"):
        parse_log(data, FMT)
    assert parse_log(data, replace(FMT, power_index=3))[0].watts == 30


def test_live_partial_tail_ignored_but_complete_bad_row_rejected():
    data = log_text(ROWS) + b"19.10.2026,12:"
    assert len(parse_log(data, FMT, live=True)) == 2
    with pytest.raises(ValueError):
        parse_log(data + b"\n", FMT, live=True)


def test_wrong_units_rejected():
    with pytest.raises(ValueError):
        parse_log(
            log_text(ROWS, "Date,Time,CPU Package Power [kW]"),
            replace(FMT, power_column="CPU Package Power [kW]"),
        )


def test_preflight_requires_real_growth(tmp_path):
    path = tmp_path / "log.csv"
    path.write_bytes(log_text(ROWS))
    now = parse_log(path.read_bytes(), FMT)[-1].timestamp
    with pytest.raises(ValueError, match="not growing"):
        preflight_log(path, FMT, now=lambda: now, sleep=lambda _: None)

    def advance(_):
        path.write_bytes(log_text(ROWS + ["19.10.2026,12:00:01.000,25"]))

    value = preflight_log(path, FMT, now=lambda: now + 0.5, sleep=advance)
    assert value["bytes_after"] > value["bytes_before"]


def test_stale_log_rejected(tmp_path):
    path = tmp_path / "log.csv"
    path.write_bytes(log_text(ROWS))
    with pytest.raises(ValueError, match="stale"):
        preflight_log(path, FMT, now=lambda: 9999999999, sleep=lambda _: None)


def test_capture_preserves_bytes_and_rejects_replacement(tmp_path):
    source, mirror = tmp_path / "source.csv", tmp_path / "mirror.csv"
    source.write_bytes(log_text(ROWS))
    end = parse_log(source.read_bytes(), FMT)[-1].timestamp
    _, metadata = capture_log(source, mirror, FMT, end)
    assert mirror.read_bytes() == source.read_bytes()
    assert metadata["prefix_bytes"] == len(source.read_bytes())
    source.write_bytes(log_text([row.replace(",10", ",11") for row in ROWS]))
    with pytest.raises(ValueError, match="replaced"):
        capture_log(source, mirror, FMT, end)
