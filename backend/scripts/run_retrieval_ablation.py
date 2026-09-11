"""Score four query formulations against the live index, and write the table.

The knowledge base is small — 32 articles, 146 chunks — so recall alone will not separate
much. What this measures is the thing the agent actually chooses: **how the question is
worded**. The served wording is called through the agent's own function, so the row marked
*served* is the product and not a copy of it.

    docker compose up -d
    docker compose run --rm backend python -m scripts.ingest_wikichess
    uv run python -m scripts.run_retrieval_ablation
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from chess_coach.config import get_settings
from chess_coach.evaluation.cases import load_cases
from chess_coach.evaluation.metrics import aggregate, dedupe_sources, reciprocal_rank
from chess_coach.evaluation.variants import SERVED, VARIANTS
from chess_coach.services.rag_search import RagService

OUT_JSON = Path("data/eval/ablation_retrieval.json")
OUT_TABLE = Path("data/eval/ablation_retrieval.md")

#: Ask for more than the agent does. The agent shows three passages; scoring needs to know
#: where the right article landed when it is not in the top three.
TOP_K = 10
KS = (1, 3, 5)


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
        "corpus": {
            "wikichess": settings.wikichess_dir,
            "openings": settings.openings_dir,
            "collection": settings.milvus_collection,
        },
        "embedding_model": settings.embedding_model,
        "n_cases": len(cases),
        "top_k": TOP_K,
        "served_variant": SERVED,
        "variants": results,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_TABLE.write_text(render_table(payload), encoding="utf-8")
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
