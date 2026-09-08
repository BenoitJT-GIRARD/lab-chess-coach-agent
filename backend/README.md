# Backend — API FastAPI et agent LangGraph

Cette partie du projet contient tout le code Python : l'agent, ses outils et
l'API qui les expose. Le frontend Angular vit dans `../frontend`, et
l'orchestration des deux dans `../docker-compose.yml`.

## Organisation

```
backend/
├── src/chess_coach/
│   ├── config.py          # Réglages lus dans l'environnement
│   ├── services/          # Un module par système externe
│   ├── rag/               # Préparation et indexation du corpus
│   ├── agent/             # État, nœuds et graphe LangGraph
│   └── api/               # Routes FastAPI
├── data/                  # Base de connaissances sur les ouvertures
├── scripts/               # Ingestion, présentation, packaging
├── tests/                 # Suite pytest
├── Dockerfile
└── pyproject.toml
```

La règle de dépendance est simple : l'API et l'agent appellent les services,
jamais l'inverse.

## Lancer le backend seul

Les commandes se lancent depuis ce dossier.

```powershell
# Installer les dépendances (uv lit .python-version et uv.lock)
uv sync --all-extras

# Jouer la suite de tests
uv run pytest

# Servir l'API (Milvus et MongoDB doivent être joignables)
uv run uvicorn chess_coach.api.main:app --reload
```

Documentation interactive de l'API : <http://localhost:8000/docs>.

## Charger la base de connaissances

```powershell
uv run python -m scripts.fetch_wikichess    # télécharge les articles Wikichess
uv run python -m scripts.ingest_wikichess   # les indexe dans Milvus
```

Les articles téléchargés sont versionnés avec le projet : la première commande
n'est à rejouer que pour rafraîchir le corpus.

## Fabriquer les documents

```powershell
uv run python -m scripts.build_pdf ../docs/feasibility_video_analysis.md
```

`build_pdf` s'appuie sur Pandoc et sur Chrome en mode sans interface ; les
schémas Mermaid sont dessinés par le navigateur avant l'impression.

## Contrôles qualité

| Outil | Commande |
| --- | --- |
| Ruff (lint et format) | `uv run ruff check src tests` |
| Bandit (sécurité) | `uv run bandit -c pyproject.toml -r src` |
| Pytest | `uv run pytest` |
