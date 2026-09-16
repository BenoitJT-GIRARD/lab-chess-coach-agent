# Backend — FastAPI service and LangGraph agent

All the Python lives here: the agent, its tools, the API that exposes them, and the
harness that measures the two decisions the agent takes. The Angular interface is in
`../frontend`, and `../docker-compose.yml` assembles the two.

## Layout

```
backend/
├── src/chess_coach/
│   ├── config.py          # every tunable, read from the environment
│   ├── utils/paths.py     # every path, resolved from one marker file
│   ├── artifacts.py       # the three writers a published file goes through
│   ├── services/          # one module per external system
│   ├── rag/               # chunking and indexing of the corpus
│   ├── agent/             # LangGraph state, nodes, graph, synthesis
│   ├── evaluation/        # metrics, query variants, threshold sweep
│   └── api/               # routes, schemas, and the mapping between them
├── data/
│   ├── openings/          # 11 notes written in French
│   └── eval/              # the frozen inputs the measurements replay from
├── reports/               # what the measurement scripts publish
├── notebooks/             # the walkthrough, from a FEN to the agent's prompt
├── scripts/               # ingestion, the measurement scripts, the smoke run
├── tests/                 # unit, integration, system
├── var/                   # what a run leaves behind; git ignores it
├── Dockerfile
└── pyproject.toml
```

The dependency rule is one line: the API and the agent call the services, never the
reverse. `evaluation/` depends on both, and nothing depends on `evaluation/`.

## Running the backend on its own

From this directory.

```powershell
uv sync --extra dev                          # uv reads .python-version and uv.lock
uv run pytest
uv run uvicorn chess_coach.api.main:app --reload   # Milvus and MongoDB must be reachable
```

Interactive API documentation: <http://localhost:8000/docs>.

The three tiers of the suite are separated by what they may touch. `tests/unit/` replaces
the socket module, so a test that reaches a service fails with the reason instead of
passing slowly on the machine that happens to run one. `tests/integration/` wires two real
components together. `tests/system/` launches uvicorn itself and questions the result over
HTTP, with the six containers absent.

## Loading the knowledge base

```powershell
uv run python -m scripts.fetch_wikichess     # downloads the Wikichess articles
uv run python -m scripts.ingest_wikichess    # chunks and indexes them into Milvus
```

The downloaded articles are not versioned with the project, because they belong to their
authors, so the first command is the one that creates the corpus. The second is the one to
run after a fresh `docker compose up`: the Milvus volume keeps the index between restarts,
but it starts empty.

## Reproducing the measurements

```powershell
uv run python -m scripts.run_retrieval_ablation   # four query formulations, 14 cases
uv run python -m scripts.sweep_theory_threshold   # reads the frozen Explorer reading
uv run python -m scripts.sample_theory_positions  # re-takes it; the only script needing a token
uv run python -m scripts.check_move_invention --rejudge   # re-reads the saved answers
```

The ablation needs the stack up and the corpus ingested. The sweep touches no network by
design: the Explorer is a living database, so its reading is taken once, dated, and
committed, and everything downstream runs on the file.

The latency bench belongs inside the container, where Stockfish is installed:

```powershell
docker compose exec backend python -m scripts.bench_agent
```

Results land in `reports/`, and the README at the root quotes them. `../docs/protocol.md`
says, for each one, what its design can and cannot settle.

## The evidence of a run

```powershell
uv run python scripts/smoke.py
```

It answers one position with every service unreachable, replays the threshold sweep, and
re-reads the 42 saved model answers. If any of the four files it regenerates comes out
different from the committed version, it names them and writes nothing;
`reports/run-evidence.json` is written only when the run reproduced what is published.

## Rebuilding the notebook and the documents

```powershell
uv run python scripts/run_notebooks.py           # one clean kernel, outputs committed
uv run python scripts/run_notebooks.py --check   # fail if the notebook is stale
uv run python -m scripts.build_pdf ../docs/feasibility_video_analysis.md
```

`build_pdf` drives Pandoc and headless Chrome, so a Mermaid diagram reaches the page as a
picture and not as a block of code. Its stylesheet takes its nine colours from
`chess_coach.figure_style`, so the PDF and the figures of the same document agree.

## Quality gates

| Tool | Command |
| --- | --- |
| Ruff (lint) | `uv run ruff check .` |
| Ruff (format) | `uv run ruff format --check .` |
| Bandit | `uv run bandit -c pyproject.toml -r src` |
| Pytest | `uv run pytest` |

Warnings are errors: `filterwarnings = ["error"]`, with no exemption. The stack is made of
six fast-moving libraries, and the configuration used to silence three whole warning
categories, including the one libraries use to announce a breaking change.
