"""Strict HWiNFO sensor CSV ingestion and read-only live-log checks."""

import csv
import hashlib
import io
import math
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from experiments.config import ENERGY


@dataclass(frozen=True)
class LogFormat:
    encoding: str = "utf-8-sig"
    delimiter: str = ","
    decimal: str = "."
    date_format: str = "%d.%m.%Y"
    time_format: str = "%H:%M:%S.%f"
    utc_offset_minutes: int = ENERGY["utc_offset_minutes"]
    power_column: str = ENERGY["sensor_column"]
    power_index: int | None = None


@dataclass(frozen=True)
class Sample:
    timestamp: float
    watts: float


def parse_log(data: bytes, fmt: LogFormat, *, live: bool = False) -> list[Sample]:
    """Never guess dates, reorder samples, interpolate missing values or select a duplicate."""
    if fmt.decimal not in {".", ","} or len(fmt.delimiter) != 1:
        raise ValueError("Invalid CSV decimal/delimiter")
    text = data.decode(fmt.encoding)
    if live and text and not text.endswith("\n"):
        text = text[: text.rfind("\n") + 1]
    reader = csv.reader(io.StringIO(text), delimiter=fmt.delimiter, strict=True)
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ValueError("No complete CSV header") from exc
    header = [name.strip().lstrip("\ufeff") for name in header]
    if header.count("Date") != 1 or header.count("Time") != 1:
        raise ValueError("Expected unique Date and Time columns")
    index = fmt.power_index
    if index is None:
        if header.count(fmt.power_column) != 1:
            raise ValueError("Missing/ambiguous power column; specify its exact name or index")
        index = header.index(fmt.power_column)
    if not 0 <= index < len(header) or header[index] != fmt.power_column:
        raise ValueError("Power index does not identify the requested column")
    if "CPU Package Power" not in header[index] or not header[index].endswith("[W]"):
        raise ValueError("Require CPU Package Power in watts [W], not energy or percent")
    date_index, time_index = header.index("Date"), header.index("Time")
    zone = timezone(timedelta(minutes=fmt.utc_offset_minutes))
    samples = []
    for line, row in enumerate(reader, 2):
        if not row:
            continue
        if len(row) != len(header):
            raise ValueError(f"Malformed CSV row {line}")
        try:
            instant = (
                datetime.strptime(
                    row[date_index].strip() + " " + row[time_index].strip(),
                    fmt.date_format + " " + fmt.time_format,
                )
                .replace(tzinfo=zone)
                .timestamp()
            )
            watts = float(row[index].strip().replace(fmt.decimal, "."))
        except ValueError as exc:
            raise ValueError(f"Invalid date/time/power at row {line}") from exc
        if not math.isfinite(watts) or watts < 0:
            raise ValueError(f"Nonfinite/negative power at row {line}")
        if samples and instant <= samples[-1].timestamp:
            raise ValueError(f"Duplicate/backward timestamp at row {line}")
        samples.append(Sample(instant, watts))
    if len(samples) < 2:
        raise ValueError("Need at least two complete sensor samples")
    return samples


def check_recent(samples: list[Sample], now: float) -> dict:
    """Validate freshness and observed cadence without pretending to set HWiNFO polling."""
    recent = samples[-20:]
    cadence = statistics.median(
        b.timestamp - a.timestamp for a, b in zip(recent, recent[1:], strict=False)
    )
    age = now - samples[-1].timestamp
    if not -ENERGY["poll_seconds"] <= age <= ENERGY["freshness_seconds"]:
        raise ValueError("Sensor clock is stale or ahead of the request clock")
    if abs(cadence - ENERGY["poll_seconds"]) > (
        ENERGY["poll_seconds"] * ENERGY["cadence_relative_tolerance"]
    ):
        raise ValueError(f"Expected 500 ms cadence, observed {cadence} seconds")
    return {"last_sample": samples[-1].timestamp, "age_seconds": age, "cadence_seconds": cadence}


def preflight_log(path: Path, fmt: LogFormat, *, sleep=time.sleep, now=time.time) -> dict:
    """Require more bytes AND advancing valid timestamps, not mere file existence."""
    first = path.read_bytes()
    initial = parse_log(first, fmt, live=True)
    check_recent(initial, now())
    sleep(ENERGY["growth_check_seconds"])
    second = path.read_bytes()
    final = parse_log(second, fmt, live=True)
    if len(second) <= len(first) or not second.startswith(first):
        raise ValueError("HWiNFO log is not growing append-only")
    if final[-1].timestamp <= initial[-1].timestamp:
        raise ValueError("HWiNFO samples did not advance")
    return {"bytes_before": len(first), "bytes_after": len(second), **check_recent(final, now())}


def capture_log(
    source: Path, destination: Path, fmt: LogFormat, end: float, *, sleep=time.sleep, now=time.time
) -> tuple[list[Sample], dict]:
    """Append exact live-log bytes to a session mirror and record a bounded prefix hash."""
    deadline = now() + ENERGY["coverage_wait_seconds"]
    while True:
        data = source.read_bytes()
        samples = parse_log(data, fmt, live=True)
        if samples[-1].timestamp >= end:
            break
        if now() >= deadline:
            raise ValueError("No trailing sensor sample: logging may have stopped")
        sleep(ENERGY["poll_seconds"])
    previous = destination.read_bytes() if destination.exists() else b""
    if not data.startswith(previous):
        raise ValueError("Sensor source was truncated/replaced; retaining existing mirror")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("ab") as stream:
        stream.write(data[len(previous) :])
        stream.flush()
        import os

        os.fsync(stream.fileno())
    return samples, {
        "path": str(destination),
        "prefix_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
