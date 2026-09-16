# Backend — FastAPI service and LangGraph agent

All the Python lives here: the agent, its tools, the API that exposes them, and the
harness that measures the two decisions the agent takes. The Angular interface is in
`../frontend`, and `../docker-compose.yml` assembles the two.

## Layout

```
backend/
├── src/chess_coach/
│   ├── config.py          # every tunable, read from the environment
│   ├── services/          # one module per external system
│   ├── rag/               # chunking and indexing of the corpus
│   ├── agent/             # LangGraph state, nodes, graph, synthesis
│   ├── evaluation/        # metrics, query variants, threshold sweep
│   └── api/               # FastAPI routes and schemas
├── data/
│   ├── wikichess/         # 21 articles, English, each citing its source
│   ├── openings/          # 11 notes written in French
│   └── eval/              # the published measurements and the cases behind them
├── scripts/               # ingestion, the measurement scripts, the PDF build
├── tests/                 # 87 tests, no network
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

## Loading the knowledge base

```powershell
uv run python -m scripts.fetch_wikichess     # downloads the Wikichess articles
uv run python -m scripts.ingest_wikichess    # chunks and indexes them into Milvus
```

The downloaded articles are not versioned with the project — they belong to their authors —
so the first command is the one that creates the corpus. The second is the one to run after a fresh `docker compose up`:
the Milvus volume keeps the index between restarts, but it starts empty.

## Reproducing the measurements

```powershell
uv run python -m scripts.run_retrieval_ablation   # four query formulations, 14 cases
uv run python -m scripts.sweep_theory_threshold   # reads the frozen Explorer reading
uv run python -m scripts.sample_theory_positions  # re-takes it; the only script needing a token
```

The ablation needs the stack up and the corpus ingested. The sweep touches no network by
design: the Explorer is a living database, so its reading is taken once, dated, and
committed, and everything downstream runs on the file.

The latency bench belongs inside the container, where Stockfish is installed:

```powershell
docker compose exec backend python -m scripts.bench_agent
```

Results land in `data/eval/`, and the README at the root quotes them.

## Building the documents

```powershell
uv run python -m scripts.build_pdf ../docs/feasibility_video_analysis.md
```

`build_pdf` drives Pandoc and headless Chrome; the Mermaid diagrams are drawn by the
browser before printing rather than left as code blocks.

## Quality gates

| Tool | Command |
| --- | --- |
| Ruff — lint | `uv run ruff check .` |
| Ruff — format | `uv run ruff format --check .` |
| Bandit | `uv run bandit -c pyproject.toml -r src` |
| Pytest | `uv run pytest` |

Warnings are errors: `filterwarnings = ["error"]`, with no exemption. The stack is made of
six fast-moving libraries, and the configuration used to silence three whole warning
categories — including the one libraries use to announce a breaking change.
