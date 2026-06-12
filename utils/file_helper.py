"""Helper functions for reading and writing data files."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path


def _invert_fieldnames(fieldnames: Mapping[str, str]) -> dict[str, str]:
    """Map CSV column headers back to dict keys."""
    return {header: key for key, header in fieldnames.items()}


def _read_raw_csv(file_path: str | Path) -> list[dict[str, str]]:
    with open(file_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_csv_rows(
    file_path: str | Path,
    fieldnames: Mapping[str, str],
) -> list[dict[str, str]]:
    """Read a CSV file and return rows keyed by field names."""
    header_to_key = _invert_fieldnames(fieldnames)
    return [
        {header_to_key.get(header, header): value for header, value in row.items()}
        for row in _read_raw_csv(file_path)
    ]


def write_csv(
    file_path: str | Path,
    data: list[dict],
    fieldnames: Mapping[str, str],
) -> None:
    """Write rows to a CSV file using fieldnames as key → column title mapping."""
    headers = list(fieldnames.values())
    rows = [{fieldnames[key]: row.get(key, "") for key in fieldnames} for row in data]

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
