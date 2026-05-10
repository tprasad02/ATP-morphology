"""
io_utils.py

Shared file-writing helpers for ATP analysis scripts.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def ensure_parent_dir(path: str) -> None:
    parent = Path(path).parent
    if str(parent) != ".":
        parent.mkdir(parents=True, exist_ok=True)


def write_json(path: str, data: Dict[str, Any]) -> None:
    ensure_parent_dir(path)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_csv(path: str, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    ensure_parent_dir(path)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)