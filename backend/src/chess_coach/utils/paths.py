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

The directory names are the closed vocabulary shared by every repository of the portfolio.
A project adds its own *named artefacts* below — the served model, the published table — and
never a new root directory: a directory outside the vocabulary exists only when
``targets.yaml`` declares it with the technical reason that imposes it.
"""

from __future__ import annotations

import os
from pathlib import Path


def _package_name() -> str:
    """The distribution package this module belongs to, read from the import system.

    The same file is copied into every project of the portfolio, so it must not name one.
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


def ensure_dirs() -> None:
    """Create the directories a run writes into.

    Reading is never a reason to create a directory: a missing input must fail where it is
    missing, not quietly become an empty folder.
    """
    for path in (REPORTS_DIR, FIGURES_DIR, MODELS_DIR, VAR_DIR):
        path.mkdir(parents=True, exist_ok=True)


#: The repository, one level above the Python project. This is the only project of the
#: portfolio that is not at the root of its repository: `frontend/` is beside it, and
#: `docs/` belongs to both. The two constants below are therefore redefined against the
#: repository and not against the project: a screenshot of the interface is not a
#: document of the backend.
REPO_DIR: Path = ROOT_DIR.parent
DOCS_DIR = REPO_DIR / "docs"
IMAGES_DIR = DOCS_DIR / "images"

# --- The named files of the chess coach -------------------------------------
#
# Above: the directories every repository of the portfolio shares. Below: the files this
# project in particular reads and writes. A module that wants one of them imports its name
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
