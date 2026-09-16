"""Score four query formulations against the live index, and write the table.

The knowledge base is small — 32 articles, 146 chunks — so recall alone will not separate
much. What this measures is the thing the agent actually chooses: **how the question is
worded**. The served wording is called through the agent's own function, so the row marked
*served* is the product and not a copy of it.

    docker compose up -d
    the ingestion command of docker-compose.yml
    uv run python -m scripts.run_retrieval_ablation
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from chess_coach.artifacts import write_json, write_text
from chess_coach.config import get_settings
from chess_coach.evaluation.cases import load_cases
from chess_coach.evaluation.metrics import aggregate, dedupe_sources, reciprocal_rank
from chess_coach.evaluation.variants import SERVED, VARIANTS
from chess_coach.services.rag_search import RagService
from chess_coach.utils.paths import ABLATION_JSON, ABLATION_TABLE, ROOT_DIR

OUT_JSON = ABLATION_JSON
OUT_TABLE = ABLATION_TABLE

#: Ask for more than the agent does. The agent shows three passages; scoring needs to know
#: where the right article landed when it is not in the top three.
TOP_K = 10
KS = (1, 3, 5)


def _relative(directory: str) -> str:
    """The directory as the repository sees it, whatever the working directory was."""

    path = Path(directory)
    try:
        return path.resolve().relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> None:
    settings = get_settings()
    service = RagService(settings)
    cases = load_cases()

    results: dict[str, dict] = {}
    for name, build_query in VARIANTS.items():
        per_case, detail = [], []
        for case in cases:
            query = build_query(case)
            hits = service.search(query, top_k=TOP_K)
            ranked = dedupe_sources(f"{hit.source}" for hit in hits)
            per_case.append((ranked, case.expected_sources))
            detail.append(
                {
                    "case": case.id,
                    "query": query,
                    "rank": next(
                        (i for i, s in enumerate(ranked, 1) if s in case.expected_sources),
                        None,
                    ),
                    "first": ranked[0] if ranked else None,
                    "rr": round(reciprocal_rank(ranked, case.expected_sources), 4),
                }
            )
        scores = aggregate(per_case, ks=KS)
        results[name] = {"scores": scores, "cases": detail}
        print(
            f"{name:18s} recall@1 {scores['recall@1']:.2f}  "
            f"recall@3 {scores['recall@3']:.2f}  MRR {scores['mrr']:.3f}"
        )

    payload = {
        "measured": datetime.now(UTC).date().isoformat(),
        # Relative to the project: an absolute path published in an artefact says where the
        # author's machine keeps its files, and means nothing to anyone else.
        "corpus": {
            "wikichess": _relative(settings.wikichess_dir),
            "openings": _relative(settings.openings_dir),
            "collection": settings.milvus_collection,
        },
        "embedding_model": settings.embedding_model,
        "n_cases": len(cases),
        "top_k": TOP_K,
        "served_variant": SERVED,
        "variants": results,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    write_json(OUT_JSON, payload)
    write_text(OUT_TABLE, render_table(payload))
    print(f"\nwritten: {OUT_JSON} and {OUT_TABLE}")


def render_table(payload: dict) -> str:
    """The same numbers as the JSON, in the shape a README can quote."""

    n = payload["n_cases"]
    lines = [
        "# Retrieval ablation — query formulation",
        "",
        f"- Measured: {payload['measured']}",
        f"- Cases: {n}, hand-written, hard label on the source article",
        f"- Corpus: {payload['corpus']['wikichess']} + {payload['corpus']['openings']}",
        f"- Embedding model: `{payload['embedding_model']}`",
        f"- Retrieved: top {payload['top_k']}, deduplicated by source file",
        "",
        "| Variant | recall@1 | recall@3 | recall@5 | MRR |",
        "|---|---|---|---|---|",
    ]
    for name, entry in payload["variants"].items():
        s = entry["scores"]
        label = f"`{name}` *(served)*" if name == payload["served_variant"] else f"`{name}`"
        lines.append(
            f"| {label} | {s['recall@1']:.2f} | {s['recall@3']:.2f} | "
            f"{s['recall@5']:.2f} | {s['mrr']:.3f} |"
        )
    step = 1 / n
    lines += [
        "",
        f"On {n} cases one case is worth {step:.2f} of recall, so a gap narrower than that "
        "is a single question changing its mind, not a result.",
        "",
        "## Where each variant lands, case by case",
        "",
        "Rank of the first correct article, `—` when none is retrieved in the top "
        f"{payload['top_k']}.",
        "",
        "| Case | " + " | ".join(f"`{v}`" for v in payload["variants"]) + " |",
        "|---" * (len(payload["variants"]) + 1) + "|",
    ]
    ids = [c["case"] for c in next(iter(payload["variants"].values()))["cases"]]
    for case_id in ids:
        row = [case_id]
        for entry in payload["variants"].values():
            found = next(c for c in entry["cases"] if c["case"] == case_id)
            row.append(str(found["rank"]) if found["rank"] else "—")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
