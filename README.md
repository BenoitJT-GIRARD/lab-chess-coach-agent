# Chess Coach — chess-opening coaching agent

Chess Coach is a proof-of-concept conversational agent that helps young players
study chess **openings**. For any board position (FEN) the agent combines
several specialised tools through a [LangGraph](https://langchain-ai.github.io/langgraph/)
workflow:

- **theory** — best book moves from the public
  [Lichess Opening Explorer](https://lichess.org/api#tag/Opening-Explorer);
- **engine** — a [Stockfish](https://stockfishchess.org/) evaluation when the
  game leaves known theory;
- **context** — a Retrieval-Augmented Generation (RAG) layer over Wikichess
  opening articles, embedded with
  [sentence-transformers](https://www.sbert.net/) and stored in
  [Milvus](https://milvus.io/);
- **videos** — relevant tutorials from the
  [YouTube Data API v3](https://developers.google.com/youtube/v3).

The project is a chess-opening coaching agent. It is
delivered as a containerised stack — **FastAPI + LangGraph + Milvus + MongoDB +
Angular** — runnable end-to-end with a single `docker compose up`.

## Repository layout

```
ffe/
├── docs/                       # Auto-evaluation, feasibility note, architecture
├── frontend/                   # Angular interface (ngx-chessboard)
├── notebooks/
│   └── chess_coach_mission.ipynb    # End-to-end didactic walk-through (French)
├── scripts/                    # Ingestion, presentation, packaging helpers
├── src/chess_coach/
│   ├── config.py               # Centralised settings (env variables)
│   ├── services/               # Lichess, Stockfish, YouTube, Milvus, MongoDB
│   ├── rag/                    # Wikichess preprocessing + Milvus ingestion
│   ├── agent/                  # LangGraph state, nodes and graph
│   └── api/                    # FastAPI routes (thin layer over the services)
├── tests/                      # Pytest suite
├── docker/                     # Service Dockerfiles
├── docker-compose.yml          # Full stack orchestration
├── pyproject.toml              # uv-managed deps + ruff/bandit/pytest
├── .pre-commit-config.yaml     # ruff, bandit, nbstripout
└── README.md
```

## Quick start (Docker)

```powershell
# 1. Copy the environment template and add your YouTube Data API key
copy .env.example .env

# 2. Build and start the whole stack (FastAPI, Milvus, MongoDB, Angular)
docker compose up --build

# 3. Load the Wikichess knowledge base into Milvus (first run only)
docker compose run --rm backend python -m scripts.ingest_wikichess

# 4. Open the interfaces
#    - Angular UI ............ http://localhost:4200
#    - FastAPI Swagger docs .. http://localhost:8000/docs
```

## Quick start (local backend, without Docker)

```powershell
# 1. Install Python 3.12 and the project (uv reads .python-version)
uv sync --all-extras

# 2. Run the test suite
uv run pytest

# 3. Serve the API (needs Milvus/MongoDB reachable, see docker-compose.yml)
uv run uvicorn chess_coach.api.main:app --reload
```

## Quality gates

| Tool | Configuration | Command |
| ---- | ------------- | ------- |
| Ruff | `pyproject.toml` (`E,W,F,I,B,C4,UP,N,SIM,RUF`) | `uv run ruff check src tests` |
| Bandit | `pyproject.toml` | `uv run bandit -c pyproject.toml -r src` |
| Pytest | `pyproject.toml` | `uv run pytest` |
| Pre-commit | `.pre-commit-config.yaml` | `uv run pre-commit run --all-files` |

The pre-commit pipeline runs `ruff --fix`, `ruff-format`, `bandit` and
`nbstripout` (notebooks are committed without execution outputs).

## Deliverables

- The end-to-end reasoning is narrated in `notebooks/chess_coach_mission.ipynb`.
- The self-evaluation grid is filled out in `docs/auto_evaluation.md`.
- The advanced video-analysis study (benefits/limits, MCP architecture and
  cost estimates) is in `docs/feasibility_video_analysis.md`.

## License

MIT.
