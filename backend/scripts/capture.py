"""Take this repository's screenshots, and write down what each one shows.

A screenshot is the only image of a repository that cannot be regenerated from data. What
makes it checkable is the sentence next to it: which build was running, what had already
happened to the application, where the displayed data came from. This script takes the picture
and writes that sentence into ``docs/images/MANIFEST.json`` in the same gesture, because a
manifest filled in afterwards is filled in from memory.

The repository fills in :data:`CAPTURES` and :func:`prepare`, and nothing else. Each entry says
what the image must *prove*: « the API answers a prediction » names a surface, « a request with
a missing feature is refused with the field named » names a behaviour; :func:`prepare` holds the
commands that put the product into the state being photographed.

    uv run python scripts/capture.py                 # every capture
    uv run python scripts/capture.py --only api-docs
    uv run python scripts/capture.py --check         # take nothing, report what is stale

Two engines. Chrome headless is enough for a page that renders server-side or in one pass —
Swagger, Airflow, a static report — as long as ``--virtual-time-budget`` is given, without
which the picture is taken before the JavaScript has drawn anything. It is **not** enough for
a page whose content arrives over a websocket: a Streamlit page loads an empty skeleton and
fills it afterwards, and the virtual clock advances timers without waiting for that round
trip, so the capture comes out black however long the budget. Those pages go through
``playwright``, which waits for a selector that only exists once the content is there.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

from chess_coach.utils.paths import IMAGES_DIR, REPO_DIR, ROOT_DIR

#: Logical size of every capture, and the density it is rendered at. One size for all of
#: them, so that two screenshots of this product can be read side by side.
VIEWPORT = (1280, 1000)
DEVICE_SCALE_FACTOR = 2

MANIFEST = IMAGES_DIR / "MANIFEST.json"
SOURCE = "scripts/capture.py"


@dataclass(frozen=True)
class Capture:
    """One image, and everything a reader needs to believe it.

    ``app_state`` is described precisely enough to be reproduced: « after 300 scoring
    requests, two of them refused », and never « with data ». ``data_source`` names where what
    is displayed comes from; a capture never redistributes someone else's work, so a
    third-party source is refused outright.
    """

    name: str
    route: str
    app_state: str
    demonstrates_behaviour: str
    data_source: str
    engine: str = "chrome"
    #: A selector that exists only once the content has arrived. Required by the playwright
    #: engine, ignored by Chrome.
    ready_selector: str | None = None
    #: What to do before the picture, in order. Each step is ``(action, target, value)``:
    #: ``("click", role, accessible name)``, ``("open", css selector, "")``,
    #: ``("fill", css selector, text)``,
    #: ``("scroll", css selector, "")``. A capture of an answer needs the three: click the
    #: control, type a real question, bring the response into the frame.
    steps: tuple[tuple[str, str, str], ...] = ()
    #: The twin image, when the product has a nominal and a degraded behaviour. A refusal
    #: shown alone reads as a failure; shown next to the nominal answer it reads as a design.
    paired_with: str | None = None
    depends_on: tuple[str, ...] = ()
    #: A surface of this repository that is NOT the one ``SERVE_COMMAND`` starts — an
    #: orchestrator's web interface, a database console, a second service of the same
    #: compose file. ``served_by`` is the command a reader runs to bring it up, and the
    #: capture is skipped, loudly, when nothing answers there: a picture is worth taking
    #: only of something that is running.
    base_url: str | None = None
    served_by: str | None = None

    @property
    def target(self) -> str:
        return f"{self.base_url or BASE_URL}{self.route}"

    @property
    def is_second_surface(self) -> bool:
        return self.base_url is not None

    @property
    def path(self) -> Path:
        return IMAGES_DIR / f"{self.name}.png"


#: Where the API listens. This repository is not started by a command from `scripts/`: the
#: product is six containers, and the README's « Running it » section starts them with
#: `docker compose up -d --build`. `SERVE_COMMAND` is therefore empty and the captures are
#: taken against a stack a reader brings up the same way.
BASE_URL = "http://127.0.0.1:8000"
SERVE_COMMAND: tuple[str, ...] = ()
HEALTH_ROUTE: str | None = "/api/v1/healthcheck"

#: The interface, served by nginx in its own container.
INTERFACE_URL = "http://127.0.0.1:4200"

COMPOSE = "docker compose up -d --build"

STATE = (
    "the six containers up through `docker compose up -d --build`, the Wikichess corpus "
    "downloaded and ingested into Milvus, and a Lichess token, a YouTube key and a language "
    "model key present in .env"
)

#: The repository's captures. Nothing else in this file changes from one repository to
#: the next.
CAPTURES: tuple[Capture, ...] = (
    Capture(
        name="api-docs",
        route="/docs",
        # The page is empty until the schema arrives and Swagger has built itself from it,
        # which is why this one waits on an element and not on a timer.
        engine="playwright",
        ready_selector="#operations-tag-position",
        app_state=STATE + ", and no request sent yet",
        demonstrates_behaviour=(
            "the eight routes and the shape of every answer, generated from the Pydantic "
            "models rather than written by hand, so the page a caller reads cannot drift "
            "from the contract the service enforces"
        ),
        data_source="own",
        depends_on=("src/chess_coach/api/main.py", "src/chess_coach/api/schemas.py"),
    ),
    Capture(
        name="coach-in-theory",
        base_url=INTERFACE_URL,
        served_by=COMPOSE,
        route="/",
        engine="playwright",
        app_state=STATE + ", the board set to the Ruy Lopez after 3.Bb5 from the demo row",
        demonstrates_behaviour=(
            "the nominal answer, at the top of the panel where a reader lands: the opening "
            "named with its ECO code, the summary, the move most played in master games with "
            "its count, the theoretical moves and the reference games. The retrieved passage "
            "is below the fold here and visible in the twin capture"
        ),
        data_source="own",
        ready_selector="app-coach-panel .recommendation",
        steps=(("open", 'mat-chip:has-text("Partie espagnole")', ""),),
        paired_with="coach-out-of-theory",
        depends_on=(
            "../frontend/src/app/coach/coach-panel.component.html",
            "src/chess_coach/agent/graph.py",
        ),
    ),
    Capture(
        name="coach-out-of-theory",
        base_url=INTERFACE_URL,
        served_by=COMPOSE,
        route="/",
        engine="playwright",
        app_state=STATE + ", the board set to 1.e4 e5 2.Qh5 from the demo row",
        demonstrates_behaviour=(
            "the same screen one branch later: the master database does not reach this "
            "position, so the theory panel says so and the engine evaluation takes its "
            "place, which is the branch the routing threshold decides"
        ),
        data_source="own",
        ready_selector="app-coach-panel .recommendation",
        steps=(
            ("open", 'mat-chip:has-text("Hors théorie")', ""),
            # The engine block is what replaces the theory here, and it sits below the fold.
            ("scroll", "app-coach-panel .block.engine", ""),
        ),
        paired_with="coach-in-theory",
        depends_on=(
            "../frontend/src/app/coach/coach-panel.component.html",
            "src/chess_coach/agent/graph.py",
        ),
    ),
)


def prepare() -> None:
    """Check that the stack is up and that the index holds the corpus.

    Nothing is started here. The product of this repository is a compose file, and a capture
    taken against a stack this script brought up its own way would prove something about that
    way. What `prepare` does instead is refuse to photograph an empty index: a page that
    answers with no passage looks like a product with no retrieval, and the picture would be
    of a state the README never describes.
    """

    if not _answers(f"{INTERFACE_URL}/"):
        raise SystemExit(f"nothing is serving {INTERFACE_URL} — run `{COMPOSE}` first")

    probe = f"{BASE_URL}/api/v1/vector-search?q=ruy%20lopez&top_k=1"
    try:
        with urllib.request.urlopen(probe, timeout=60) as answer:
            passages = json.loads(answer.read().decode("utf-8"))["passages"]
    except (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f"the vector store did not answer ({exc})") from exc
    if not passages:
        raise SystemExit(
            "the index is empty — run `docker compose run --rm backend python -m "
            "scripts.ingest_wikichess`"
        )


# --- Starting the product, and knowing when it is up ------------------------


def _answers(url: str) -> bool:
    """Whether something is already serving that URL, right now."""
    try:
        with urllib.request.urlopen(url, timeout=1) as answer:
            return answer.status < 500
    except (urllib.error.URLError, OSError):
        return False


def wait_until_healthy(url: str, *, timeout: float = 90.0) -> None:
    """Poll until the service answers. Never sleep a fixed number of seconds.

    A fixed sleep is either too short on a cold start, and the capture photographs a
    connection error, or wasted on every run afterwards.
    """
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as answer:
                if answer.status < 500:
                    return
        except (urllib.error.URLError, OSError) as exc:  # not up yet
            last = exc
        time.sleep(0.25)
    raise TimeoutError(f"{url} never answered in {timeout:.0f}s ({last})")


class Serving:
    """Start the product, wait for it, capture, stop it — even when a capture raises."""

    def __init__(self, command: tuple[str, ...], health: str | None):
        self.command = command
        self.health = health
        self.process: subprocess.Popen | None = None

    def __enter__(self) -> Self:
        if self.health is None:
            return self
        if not self.command:
            wait_until_healthy(self.health, timeout=5)
            return self
        # Something already answering on that port gets photographed in place of the
        # product: a server left over from an earlier run serves an older build, and its
        # picture is indistinguishable from a fresh one.
        if _answers(self.health):
            raise RuntimeError(
                f"{self.health} already answers: stop what is listening before capturing, "
                "or the picture will be of that and not of this build"
            )
        self.process = subprocess.Popen(
            list(self.command), cwd=ROOT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
        )
        wait_until_healthy(self.health)
        return self

    def __exit__(self, *_exception) -> None:
        """Stop the whole tree. `uv run uvicorn` is two processes, and killing the first
        leaves the second holding the port for the next run."""
        if self.process is None:
            return
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            self.process.terminate()
        try:
            self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.process.kill()


# --- The two engines --------------------------------------------------------


def _chrome_binary() -> str:
    """The browser on this machine, named by the environment and never guessed.

    A path hard-coded here would be one machine's installation shipped inside a published
    repository; ``CHROME_PATH`` keeps that constraint where it belongs.
    """
    explicit = os.environ.get("CHROME_PATH")
    if explicit:
        return explicit
    for name in ("chrome", "google-chrome", "chromium"):
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError(
        "no Chrome on PATH: set CHROME_PATH to the browser's executable, or run the "
        "capture with --engine playwright"
    )


def by_chrome(capture: Capture) -> None:
    """One pass, headless. `--virtual-time-budget` is what makes a JavaScript page render."""
    width, height = VIEWPORT
    subprocess.run(
        [
            _chrome_binary(),
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--virtual-time-budget=8000",
            f"--window-size={width},{height}",
            f"--force-device-scale-factor={DEVICE_SCALE_FACTOR}",
            f"--screenshot={capture.path}",
            capture.target,
        ],
        check=True,
        cwd=ROOT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def by_playwright(capture: Capture) -> None:
    """For a page whose content arrives over a websocket, and that Chrome photographs black.

    ``channel="chrome"`` reuses the system browser: no download, and the picture is taken by
    the same engine a reader would open the page with.
    """
    from playwright.sync_api import sync_playwright  # installed in the capture environment

    width, height = VIEWPORT
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=DEVICE_SCALE_FACTOR,
        )
        page.goto(capture.target, wait_until="networkidle", timeout=90_000)
        for action, target, value in capture.steps:
            if action == "click":
                # `.first`: a Swagger operation carries a title button and an arrow button
                # under the same accessible name, and the first in document order is the one
                # a reader sees and clicks.
                page.get_by_role(target, name=value).first.click()
            elif action == "open":
                # A control named by a CSS selector, where no accessible name reaches it. A
                # Swagger operation reached through a deep link is not always expanded by the
                # time the page settles, and its « Try it out » button is not in the DOM
                # until it is: clicking the operation's own header is what puts it there.
                page.locator(target).first.click()
            elif action == "fill":
                page.locator(target).first.fill(value)
            elif action == "scroll":
                page.locator(target).first.scroll_into_view_if_needed()
            else:
                raise ValueError(f"{capture.name}: unknown capture step « {action} »")
            page.wait_for_timeout(300)
        if capture.ready_selector:
            page.wait_for_selector(capture.ready_selector, timeout=180_000)
        page.wait_for_timeout(4000)  # let the animations settle
        page.screenshot(path=str(capture.path))
        browser.close()


ENGINES = {"chrome": by_chrome, "playwright": by_playwright}


# --- Writing down what was photographed -------------------------------------


def _git_revision() -> str | None:
    try:
        done = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return done.stdout.strip() or None


def record(capture: Capture) -> dict:
    """The manifest entry for an image that has just been written."""
    if capture.data_source == "third_party":
        raise ValueError(
            f"{capture.name}: a capture does not redistribute someone else's work. "
            "Photograph the product against data this repository may publish."
        )
    entry = {
        "sha256": hashlib.sha256(capture.path.read_bytes()).hexdigest(),
        "written": datetime.now(tz=UTC).date().isoformat(),
        "source": SOURCE,
        "command": f"uv run python {SOURCE} --only {capture.name}",
        "target": capture.target,
        "viewport": list(VIEWPORT),
        "device_scale_factor": DEVICE_SCALE_FACTOR,
        "app_state": capture.app_state,
        "data_source": capture.data_source,
        "demonstrates_behaviour": capture.demonstrates_behaviour,
    }
    revision = _git_revision()
    if revision:
        entry["git_revision"] = revision
    if capture.paired_with:
        entry["paired_with"] = f"{capture.paired_with}.png"
    if capture.depends_on:
        entry["depends_on"] = list(capture.depends_on)
    return entry


def write_manifest(entries: dict[str, dict]) -> None:
    """Merge into the manifest. An image nobody re-took keeps the entry it had."""
    payload: dict = {"schema": "image-manifest/1", "images": {}}
    if MANIFEST.exists():
        with contextlib.suppress(json.JSONDecodeError):
            payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload.setdefault("schema", "image-manifest/1")
    payload.setdefault("images", {})
    payload["images"].update(entries)
    payload["images"] = dict(sorted(payload["images"].items()))
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline=""
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", help="a single capture, by name")
    parser.add_argument(
        "--check", action="store_true", help="take nothing; report what the manifest is missing"
    )
    arguments = parser.parse_args(argv)

    wanted = [c for c in CAPTURES if not arguments.only or c.name == arguments.only]
    if not wanted:
        print("no capture selected", file=sys.stderr)
        return 1

    if arguments.check:
        known = {}
        if MANIFEST.exists():
            known = json.loads(MANIFEST.read_text(encoding="utf-8")).get("images", {})
        stale = [
            c.name
            for c in wanted
            if not c.path.exists()
            or known.get(c.path.name, {}).get("sha256")
            != hashlib.sha256(c.path.read_bytes()).hexdigest()
        ]
        for name in stale:
            print(f"  {name} is missing or does not match its manifest entry")
        return 1 if stale else 0

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    prepare()
    entries: dict[str, dict] = {}
    health = f"{BASE_URL}{HEALTH_ROUTE}" if HEALTH_ROUTE else None
    with Serving(SERVE_COMMAND, health):
        for capture in wanted:
            if capture.is_second_surface and not _answers(capture.target):
                print(
                    f"{capture.name:24} skipped: nothing answers {capture.target}. "
                    f"Start it with: {capture.served_by}",
                    file=sys.stderr,
                )
                continue
            ENGINES[capture.engine](capture)
            entries[capture.path.name] = record(capture)
            print(f"{capture.name:24} {capture.path.relative_to(REPO_DIR)}")
    write_manifest(entries)
    print(f"{len(entries)} capture(s), {MANIFEST.relative_to(REPO_DIR)} updated")
    print("Read every image before committing it: no key, no token, no address on screen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
