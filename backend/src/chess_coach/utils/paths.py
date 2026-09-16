"""Where this project's files are. One module answers, and nothing else computes a root.

Every path hangs off :data:`ROOT_DIR`, which is **found**, never assumed. Counting
directories up from a file only works from an editable ``src/`` checkout: installed as a
wheel, the package lands inside ``site-packages``, and the whole tree — models, reports,
figures — would be written there without a word. Finding the marker file instead means the
same code works from a checkout, from a wheel and from a container.

Nothing else in the project resolves a root. No ``sys.path.insert``, no ``Path(__file__)``
walked back three times in a script, no artefact read or written through a path relative to
the working directory: each of those is a second answer to a question that already has one,
and they disagree the day someone runs a script from another directory.

The directory names below are the whole vocabulary this project uses at its root. Named
artefacts — the served model, the published table — hang off them; a new root directory
does not get added because a script found it convenient.
"""

from __future__ import annotations

import os
from pathlib import Path


def _package_name() -> str:
    """The distribution package this module belongs to, read from the import system.

    Read rather than written down, so that renaming the package does not leave a stale
    string behind in the one module whose job is to know where things are.
    """
    if __package__:
        return __package__.split(".")[0]
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if candidate.parent.name == "src":
            return candidate.name
    return here.parent.name


#: The package name, and the environment variable that overrides the root: ``<PACKAGE>_ROOT``.
PACKAGE: str = _package_name()
ROOT_ENV: str = f"{PACKAGE.upper()}_ROOT"


def _find_root() -> Path:
    """An explicit override, the marker file, or — installed outside a checkout — the cwd."""
    override = os.environ.get(ROOT_ENV)
    if override:
        return Path(override).resolve()
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pyproject.toml").exists():
            return candidate
    # Installed outside a checkout. The working directory is the only defensible guess, and
    # it keeps what a run writes where the user is working, and out of site-packages.
    return Path.cwd().resolve()


ROOT_DIR: Path = _find_root()

SRC_DIR: Path = ROOT_DIR / "src" / PACKAGE
TESTS_DIR: Path = ROOT_DIR / "tests"
SCRIPTS_DIR: Path = ROOT_DIR / "scripts"
NOTEBOOKS_DIR: Path = ROOT_DIR / "notebooks"
DOCS_DIR: Path = ROOT_DIR / "docs"
IMAGES_DIR: Path = DOCS_DIR / "images"
REPORTS_DIR: Path = ROOT_DIR / "reports"
FIGURES_DIR: Path = REPORTS_DIR / "figures"
DATA_DIR: Path = ROOT_DIR / "data"
MODELS_DIR: Path = ROOT_DIR / "models"
INFRA_DIR: Path = ROOT_DIR / "infra"

#: The only ignored directory: logs, checkpoints, caches, coverage reports, anything a run
#: leaves behind that no reader is meant to open.
VAR_DIR: Path = ROOT_DIR / "var"


def rel(path: Path | str) -> str:
    """A path as a log line should carry it: relative to the project, with forward slashes.

    A log that reads ``C:/Users/someone/work/data/raw/events.json`` says where the run
    happened, which the next reader cannot use and cannot compare with their own run. The
    part that carries information is ``data/raw/events.json``. A path outside the project
    keeps its absolute form, because there it is the only unambiguous answer.
    """
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return resolved.as_posix()


def ensure_dirs() -> None:
    """Create the directories a run writes into.

    Reading is never a reason to create a directory: a missing input must fail where it is
    missing, not quietly become an empty folder.
    """
    for path in (REPORTS_DIR, FIGURES_DIR, MODELS_DIR, VAR_DIR):
        path.mkdir(parents=True, exist_ok=True)


#: The repository, one level above the Python project: `frontend/` sits beside `backend/`,
#: and `docs/` belongs to both. The two constants below are therefore redefined against
#: the repository and not against the project, because a screenshot of the interface is
#: not a document of the backend.
REPO_DIR: Path = ROOT_DIR.parent
DOCS_DIR = REPO_DIR / "docs"
IMAGES_DIR = DOCS_DIR / "images"

# --- The named files of the chess coach -------------------------------------
#
# Above: the directories. Below: the files this project reads and writes. A module that wants one of them imports its name
# from here, and nowhere does a path get assembled out of a literal — which is what lets a
# script be launched from any working directory and still find its inputs.

#: The two corpora the retrieval reads. One is written by hand, in French, for a young
#: player; the other is downloaded and never redistributed.
OPENINGS_DIR: Path = DATA_DIR / "openings"
WIKICHESS_DIR: Path = VAR_DIR / "wikichess"

#: What the Wikichess download left behind: which article, from which URL, on which day.
#: It is published and the articles are not, because FICGS reserves the rights on its text
#: and an index of titles is not the text.
WIKICHESS_MANIFEST: Path = REPORTS_DIR / "wikichess_manifest.json"

#: The frozen evaluation inputs. Both are sampled once, dated, and then left alone: a
#: question set that moves between two runs measures the set rather than the system.
EVAL_DIR: Path = DATA_DIR / "eval"
RETRIEVAL_CASES: Path = EVAL_DIR / "retrieval_cases.json"
THEORY_POSITIONS: Path = EVAL_DIR / "theory_positions.json"

#: What the four measurement scripts publish.
LATENCY_JSON: Path = REPORTS_DIR / "latency.json"
ABLATION_JSON: Path = REPORTS_DIR / "ablation_retrieval.json"
ABLATION_TABLE: Path = REPORTS_DIR / "ablation_retrieval.md"
MOVE_INVENTION_JSON: Path = REPORTS_DIR / "move_invention.json"
MOVE_INVENTION_TABLE: Path = REPORTS_DIR / "move_invention.md"
THRESHOLD_SWEEP_CSV: Path = REPORTS_DIR / "theory_threshold_sweep.csv"
THRESHOLD_SWEEP_TABLE: Path = REPORTS_DIR / "theory_threshold_sweep.md"
