# Chess Coach — agent d'aide à l'apprentissage des ouvertures

Chess Coach est un agent conversationnel qui aide les jeunes joueurs à travailler
leurs **ouvertures**. Pour une position donnée (au format FEN), il combine
plusieurs outils spécialisés dans un graphe [LangGraph](https://langchain-ai.github.io/langgraph/) :

- **la théorie** — les coups et les parties de référence issus de la base de
  parties de maîtres, via
  [l'Opening Explorer de Lichess](https://lichess.org/api#tag/Opening-Explorer) ;
- **le moteur** — une évaluation [Stockfish](https://stockfishchess.org/) quand
  la partie sort des sentiers battus ;
- **le contexte** — une recherche augmentée (RAG) sur les articles
  [Wikichess](https://ficgs.com/wikichess.html), vectorisés avec
  [sentence-transformers](https://www.sbert.net/) et indexés dans
  [Milvus](https://milvus.io/) ;
- **les vidéos** — des tutoriels pertinents remontés par
  [l'API YouTube Data v3](https://developers.google.com/youtube/v3).

Un modèle de langage rédige ensuite la recommandation à partir de ces seuls
éléments. Il ne décide rien : les coups viennent de Lichess, l'évaluation de
Stockfish, le contexte de Milvus. Sans clé d'API, ou si l'appel échoue, un
gabarit déterministe prend le relais et l'agent répond quand même.

Le projet est un agent d'aide à l'apprentissage des ouvertures. Il se
présente comme une pile conteneurisée — **FastAPI + LangGraph + Milvus +
MongoDB + Angular** — qui démarre entièrement avec un seul `docker compose up`.

## Organisation du dépôt

```
ffe/
├── backend/                    # API FastAPI et agent LangGraph
│   ├── src/chess_coach/
│   │   ├── config.py           # Réglages lus dans l'environnement
│   │   ├── services/           # Lichess, Stockfish, YouTube, Milvus, MongoDB
│   │   ├── rag/                # Préparation et indexation du corpus
│   │   ├── agent/              # État, nœuds et graphe LangGraph
│   │   └── api/                # Routes FastAPI
│   ├── data/                   # Base de connaissances sur les ouvertures
│   ├── scripts/                # Ingestion, présentation, packaging
│   ├── tests/                  # Suite pytest
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/                   # Interface Angular Material (ngx-chess-board)
├── docs/                       # Architecture, note de faisabilité, auto-évaluation
├── notebooks/
│   └── chess_coach_mission.ipynb    # Déroulé de la démarche
├── docker-compose.yml          # Orchestration des six services
└── README.md
```

La séparation `backend/` / `frontend/` est celle demandée à l'étape 1 du brief.
Chaque moitié se construit et se teste indépendamment ; `docker-compose.yml` les
assemble.

## Démarrage rapide

Docker Desktop doit être lancé.

```powershell
# 1. Copier le modèle d'environnement et y coller ses clés
copy .env.example .env

# 2. Construire et démarrer toute la pile
docker compose up -d --build

# 3. Charger la base de connaissances dans Milvus (une seule fois :
#    le volume Milvus la conserve d'un redémarrage à l'autre)
docker compose run --rm backend python -m scripts.ingest_wikichess

# 4. Ouvrir les interfaces
#    - Application Angular ..... http://localhost:4200
#    - Documentation de l'API .. http://localhost:8000/docs
```

Les six services (`etcd`, `minio`, `milvus`, `mongo`, `backend`, `frontend`)
démarrent dans l'ordre grâce aux sondes de santé. Tout l'état vit dans des
volumes nommés (`docker volume ls`) : arrêter puis relancer la pile conserve la
base vectorielle et l'historique des interactions.

Pour tout arrêter : `docker compose down`. Pour repartir de zéro, volumes
compris : `docker compose down -v`.

## Ce qu'on peut montrer en démonstration

Ouvrir <http://localhost:4200>, jouer des coups sur l'échiquier ou cliquer sur
les positions préparées.

| Position | Ce que fait l'agent |
| --- | --- |
| Position de départ | Reconnaît la famille d'ouverture et liste les premiers coups |
| Italienne (après 3.Fc4 Fc5) | Nomme l'ouverture, montre la théorie, le contexte Wikichess et des vidéos |
| Sicilienne (après 1.e4 c5) | Remonte les articles et tutoriels sur la sicilienne |
| Hors théorie (après 1.e4 e5 2.Dh5) | Bascule sur Stockfish et explique l'évaluation |

## Les routes de l'API

| Route | Rôle |
| --- | --- |
| `GET /api/v1/healthcheck` | Vérifie que le service répond |
| `GET /api/v1/position/{fen}` | Décrit une position (trait, coups légaux, diagramme) |
| `GET /api/v1/moves/{fen}` | Coups théoriques et parties de référence (Lichess), ou le livre local |
| `GET /api/v1/evaluate/{fen}` | Évaluation Stockfish et meilleur coup |
| `GET /api/v1/vector-search?q=` | Recherche vectorielle dans la base de connaissances |
| `GET /api/v1/videos/{opening}` | Vidéos explicatives YouTube |
| `POST /api/v1/agent` | Exécute le graphe complet sur une position |

## En cas de souci

- **Pas de vidéos** — la clé `YOUTUBE_API_KEY` manque ou son quota est épuisé.
  Le reste de la réponse fonctionne quand même.
- **Pas de théorie, seulement le moteur** — l'Opening Explorer de Lichess exige
  un jeton. Sans `LICHESS_TOKEN`, le livre d'ouvertures local couvre les
  grandes lignes et les positions plus profondes basculent sur Stockfish.
- **`vector-search` ne renvoie rien** — l'ingestion (étape 3) n'a pas été jouée.

## Développement sans Docker

Les commandes Python se lancent depuis `backend/` (voir `backend/README.md`).
Le frontend se lance depuis `frontend/` avec `npm start`.

## Contrôles qualité

| Outil | Configuration | Commande |
| --- | --- | --- |
| Ruff | `backend/pyproject.toml` | `uv run ruff check src tests` |
| Bandit | `backend/pyproject.toml` | `uv run bandit -c pyproject.toml -r src` |
| Pytest | `backend/pyproject.toml` | `uv run pytest` |
| Pre-commit | `.pre-commit-config.yaml` | `uv run pre-commit run --all-files` |
| Karma (frontend) | `frontend/angular.json` | `npm test -- --watch=false --browsers=ChromeHeadless` |

Le crochet pre-commit enchaîne `ruff --fix`, `ruff-format`, `bandit` et
`nbstripout` : les notebooks sont versionnés sans sortie d'exécution.

## Documents

- Le raisonnement complet est déroulé dans `notebooks/chess_coach_mission.ipynb`.
- Le schéma d'architecture est dans `docs/architecture.md`.
- L'étude du système d'analyse vidéo (bénéfices, limites, architecture MCP et
  coûts) est dans `docs/feasibility_video_analysis.md`.
- La fiche d'auto-évaluation est remplie dans `docs/auto_evaluation.md`.

## Licence

MIT.
