"""Writing a published file, byte for byte the same on every machine.

`Path.write_text` asks the platform how a line ends. On Windows that is two bytes, on Linux
one, so a measurement script run here and the same script run in a container produce files
that differ everywhere and agree on every number. Git hides it at commit time, which is worse
than not hiding it: the working tree looks clean, and the difference only surfaces when
something compares a fresh run to the committed artefact.

Everything under `reports/` and `data/eval/` goes through the three functions below, and
they fix the line ending instead of inheriting it.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

#: One byte, everywhere. Chosen to match what `.gitattributes` stores.
NEWLINE = "\n"


def write_text(path: Path, text: str) -> Path:
    """Write ``text`` to ``path``, with the line ending this repository publishes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline=NEWLINE)
    return path


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> Path:
    """Write ``rows`` as a CSV whose lines end the same way every other artefact's do.

    `csv.writer` has a default of its own, and it is the two-byte terminator on every
    platform: a file opened with ``newline=""`` and written by the csv module comes out
    with carriage returns even on Linux. It is the one writer that ignores the rules
    everything around it follows.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator=NEWLINE)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_json(path: Path, payload: Any) -> Path:
    """Write ``payload`` as indented JSON, ending on a single newline.

    The trailing newline is not cosmetic: without it the last line of the file has no
    terminator, and a diff of the next version rewrites a line nothing changed.
    """

    return write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + NEWLINE)
