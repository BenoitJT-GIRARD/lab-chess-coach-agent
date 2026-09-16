"""A published file has the same bytes wherever it was written.

The measurement scripts run here, on Windows, and in the backend container, on Linux. Before
`chess_coach.artifacts` existed they used `Path.write_text`, which asks the platform how a
line ends: the same script produced a file with two-byte terminators here and one-byte
terminators there, identical in every number it carried.

Git normalises at commit time, and that is what made it hard to see. The working tree looked
clean; the divergence appeared only where something compared a fresh run against the committed
artefact, which is exactly what a smoke test does.
"""

from __future__ import annotations

from pathlib import Path

from chess_coach.artifacts import write_csv, write_json, write_text


def test_a_written_table_carries_no_carriage_return(tmp_path: Path) -> None:
    target = write_text(tmp_path / "table.md", "| a | b |\n|---|---|\n| 1 | 2 |\n")

    assert b"\r" not in target.read_bytes()


def test_a_written_payload_carries_no_carriage_return(tmp_path: Path) -> None:
    target = write_json(tmp_path / "run.json", {"measured": "2026-09-15", "nodes": [1, 2, 3]})

    assert b"\r" not in target.read_bytes()


def test_a_payload_ends_on_exactly_one_newline(tmp_path: Path) -> None:
    """Without it the last line has no terminator, and the next version rewrites it."""
    target = write_json(tmp_path / "run.json", {"a": 1})

    assert target.read_bytes().endswith(b"}\n")


def test_the_directory_is_created_when_it_is_missing(tmp_path: Path) -> None:
    """A script writing its first artefact should not fail on a directory nobody made."""
    target = write_json(tmp_path / "reports" / "nested" / "run.json", {"a": 1})

    assert target.is_file()


def test_the_payload_reads_back_as_what_was_written(tmp_path: Path) -> None:
    """Non-ASCII survives: the French notes and the model's answers are full of accents."""
    import json

    payload = {"opening": "Partie espagnole", "note": "préparer une expansion"}
    target = write_json(tmp_path / "run.json", payload)

    assert json.loads(target.read_text(encoding="utf-8")) == payload


def test_a_written_table_of_rows_carries_no_carriage_return(tmp_path: Path) -> None:
    """The csv module is the exception: its own default terminator is two bytes, everywhere.

    A file opened with `newline=""` and handed to `csv.writer` comes out with carriage
    returns on Linux as well as on Windows, so it is the one writer that would keep the
    divergence alive after every other one was fixed.
    """
    target = write_csv(
        tmp_path / "sweep.csv",
        ["threshold", "in_theory"],
        [{"threshold": 1000, "in_theory": 45}, {"threshold": 2500, "in_theory": 45}],
    )

    assert b"\r" not in target.read_bytes()
    assert target.read_text(encoding="utf-8").splitlines()[0] == "threshold,in_theory"
