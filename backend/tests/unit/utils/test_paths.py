"""What `chess_coach.utils.paths` says, and why it says it from `backend/`.

This is the repository whose Python lives one directory down, beside an Angular application,
so the root the module finds is `backend/` and not the checkout. Three things follow, and each
has a test here: the marker file it walks up to, the variable a container can set to override
it, and the split between a tracked corpus and a downloaded one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chess_coach.utils import paths

#: Every root directory this project is allowed to have, plus the one it ignores.
VOCABULARY = {
    "src",
    "tests",
    "scripts",
    "notebooks",
    "docs",
    "reports",
    "data",
    "models",
    "infra",
    "var",
}


def test_the_root_holds_the_marker_it_was_found_by() -> None:
    assert (paths.ROOT_DIR / "pyproject.toml").is_file()


def test_the_root_is_the_python_project_and_not_the_repository() -> None:
    """`backend/` carries the project; the repository above it also carries an Angular app."""
    assert paths.ROOT_DIR.name == "backend"
    assert (paths.ROOT_DIR.parent / "frontend").is_dir()


def test_an_explicit_override_wins_over_the_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Set it, and the walk up the tree never happens: the value is taken as given."""
    monkeypatch.setenv(paths.ROOT_ENV, str(tmp_path))

    assert paths._find_root() == tmp_path.resolve()


def test_the_environment_variable_is_named_after_the_package() -> None:
    """The name is derived from the package rather than written down anywhere."""
    assert paths.PACKAGE == "chess_coach"
    assert paths.ROOT_ENV == "CHESS_COACH_ROOT"


def test_every_named_artefact_sits_inside_the_closed_vocabulary() -> None:
    """A constant that points outside those directories is a directory nobody decided to have.

    Two roots are admitted, and only two: the project, and the repository one level above it
    that carries `docs/` and `frontend/`. A constant that resolves to neither is a directory
    this repository never agreed to have.
    """
    roots = (paths.ROOT_DIR, paths.REPO_DIR)
    outside = []
    for name in dir(paths):
        value = getattr(paths, name)
        if name.startswith("_") or not isinstance(value, Path) or value in roots:
            continue
        relative = next(
            (value.relative_to(root) for root in roots if value.is_relative_to(root)), None
        )
        if relative is None or relative.parts[0] not in VOCABULARY:
            outside.append(f"{name} -> {value}")

    assert outside == []


def test_the_documentation_of_this_repository_is_not_the_backend_s() -> None:
    """`docs/` sits beside `backend/`, not inside it: the interface is documented there too."""
    assert paths.DOCS_DIR.parent == paths.REPO_DIR
    assert paths.IMAGES_DIR.is_dir()


def test_the_downloaded_corpus_and_the_written_notes_do_not_share_a_directory() -> None:
    """FICGS reserves the rights on its text, so its articles are written where git ignores.

    The eleven notes written for the club are the repository's own, and they are tracked.
    Putting both under `data/` is what would make the ignore rule impossible to state.
    """
    assert paths.WIKICHESS_DIR.parent == paths.VAR_DIR
    assert paths.OPENINGS_DIR.parent == paths.DATA_DIR


def test_the_manifest_of_the_corpus_is_published_although_the_corpus_is_not() -> None:
    """A list of titles, codes and URLs is a record of what was read, not the text that was read."""
    assert paths.WIKICHESS_MANIFEST.parent == paths.REPORTS_DIR
    assert paths.WIKICHESS_MANIFEST.is_file()


def test_the_frozen_evaluation_inputs_are_tracked_where_a_reader_can_open_them() -> None:
    """Both are sampled once and then left alone; a question set that moves measures itself."""
    for path in (paths.RETRIEVAL_CASES, paths.THEORY_POSITIONS):
        assert path.parent == paths.EVAL_DIR
        assert path.is_file(), f"{path.name} is tracked and has to be there"


def test_what_the_package_re_exports_is_what_the_module_defines() -> None:
    """`from chess_coach.utils import REPORTS_DIR` and the module's own name are one object."""
    from chess_coach import utils

    for name in utils.__all__:
        assert getattr(utils, name) is getattr(paths, name)
