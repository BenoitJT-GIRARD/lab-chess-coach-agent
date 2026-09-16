# Running it

Six containers, one command, and a stack that answers before all six are useful. This page is
about the gap between those two facts: what is up, what is merely running, what each missing
key costs, and what to look at when an answer stops arriving.

## Starting it

```powershell
copy .env.example .env       # every key in it is optional
docker compose up -d --build

# the articles are not redistributed; this downloads them into backend/var/
docker compose run --rm backend python -m scripts.fetch_wikichess

# index them into Milvus, once. The named volume keeps the collection
docker compose run --rm backend python -m scripts.ingest_wikichess
```

| | |
|---|---|
| Interface | <http://localhost:4200> |
| API documentation | <http://localhost:8000/docs> |
| Liveness probe | <http://localhost:8000/api/v1/healthcheck> |
| Milvus health | <http://localhost:9091/healthz> |

**Milvus is the slow one.** It waits for etcd and MinIO, and its own healthcheck is given a
ninety-second grace period before Compose starts counting failures. The backend waits for it,
the frontend waits for the backend, so `docker compose up` is quiet for a while and then
everything appears at once. A stack that looks stuck two minutes in is usually Milvus still
starting.

## What is up, and what is ready

The service answers `/api/v1/healthcheck` as soon as uvicorn binds its port. That is liveness,
and it is what the container healthcheck and the frontend probe. It is not readiness, and the
difference is worth knowing:

| Route | Works with nothing behind it |
|---|---|
| `/api/v1/healthcheck` | yes |
| `/api/v1/position/{fen}` | yes, the board is arithmetic |
| `/api/v1/moves/{fen}` | yes, from the local opening book |
| `/api/v1/evaluate/{fen}` | needs the Stockfish binary, which is in the image |
| `/api/v1/vector-search` | needs Milvus, and a collection that has been ingested |
| `/api/v1/videos/{opening}` | needs a YouTube key; answers with an empty list otherwise |
| `/api/v1/agent` | answers, degraded, whatever is missing |
| `/api/v1/history` | needs MongoDB; answers with an empty history otherwise |

**The embedding model is loaded at startup, in a background thread.** It used to load inside
the first request that needed one, which cost that request ten seconds on a warm cache and a
few hundred megabytes of download on a cold one. The service now starts, answers its probe,
and logs `Embedding model ready` when the first search will be fast. Until that line appears, a
search is slow, and it is not broken.

## What each missing key costs

Everything works without a single key. What changes is which source answers.

| Missing | What happens |
|---|---|
| `LICHESS_TOKEN` | the Explorer refuses the call and the local opening book answers; eleven openings instead of the master database |
| `YOUTUBE_API_KEY` | the videos panel stays empty, and the agent does not claim otherwise |
| `LLM_API_KEY`, or `LLM_ENABLED=false` | a deterministic French template writes the recommendation from the same facts |
| the Wikichess download | the retrieval answers from the eleven written notes alone, and `scripts/ingest_wikichess` refuses to index a third of a corpus |

That last refusal is deliberate. An index built on a third of the corpus answers every
question, plausibly, and scores a third of what `docs/protocol.md` publishes. The ingestion
reads the manifest, sees that none of the articles it lists is on disk, and names the command
that fetches them.

## When something stops answering

**A search that hangs.** Look at `docker compose logs milvus`. A call to the vector store is
given three seconds (`MILVUS_TIMEOUT`); beyond that the route answers `503` with the address it
tried. Without that deadline pymilvus retries a closed port for about ten seconds, which a
reader experiences as a page that has stopped working.

**A search that answers nothing.** The collection is empty: the container came up, the volume
is new, and nobody has run the ingestion. `docker compose run --rm backend python -m
scripts.ingest_wikichess` prints how many articles each folder held, which is the fastest way
to see that one of them held none.

**The history stays empty.** Persistence is best effort by design: a MongoDB outage logs a
warning and never costs the player an answer. Check `docker compose logs backend` for
`Could not persist interaction to MongoDB`.

**The coach says a position is out of theory when it is not.** Two causes, and the logs
separate them: no Lichess token, so the local book answered and it holds eleven openings; or
the position genuinely has fewer than `THEORY_MIN_GAMES` master games. `docs/protocol.md`
sweeps that threshold and says how much of the repertoire each value moves.

**The interface shows nothing at all.** nginx serves the built Angular application and proxies
`/api/` to the backend. If the page loads and every panel is empty, the proxy is the suspect:
`docker compose logs frontend`.

## Restarting, and what survives

Five named volumes hold the state: `milvus_data`, `etcd_data` and `minio_data` for the vector
store, `mongo_data` for the history, `hf_cache` for the downloaded embedding model. A
`docker compose restart` keeps all five, so the demonstration comes back without re-ingesting
anything.

`docker compose down -v` removes them, and then the corpus has to be ingested again. The
downloaded articles themselves survive, because they live on the host under `backend/var/` and
are mounted into the container.

## What is not here

No deployment. This stack runs on one machine, with `docker compose`, and every address above
is a localhost port. There is no orchestration manifest, no ingress, no secret manager and no
horizontal scaling, because none of them was ever exercised — publishing a Kubernetes chart
that has never run would be a claim rather than a document.

What the stack does carry is the part a deployment would need first: a liveness probe, a
healthcheck in the image, dependency ordering between the six services, a non-root user, and
every setting behind an environment variable.
