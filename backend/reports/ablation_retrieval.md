# Retrieval ablation — query formulation

- Measured: 2026-09-15
- Cases: 14, hand-written, hard label on the source article
- Corpus: var/wikichess + data/openings
- Embedding model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Retrieved: top 10, deduplicated by source file

| Variant | recall@1 | recall@3 | recall@5 | MRR |
|---|---|---|---|---|
| `name-only` | 0.93 | 1.00 | 1.00 | 0.964 |
| `french-question` *(served)* | 0.86 | 1.00 | 1.00 | 0.929 |
| `english-verbose` | 0.50 | 0.86 | 0.93 | 0.693 |
| `name-and-eco` | 0.93 | 0.93 | 1.00 | 0.946 |

> **How to read it.** Variants differ only in how the question is phrased. Each `recall@k` column
> asks whether a correct article appears among the first k results returned, so the columns get
> easier from left to right by construction. MRR (mean reciprocal rank) instead rewards the right
> article for sitting near the top, averaging one over its rank across the fourteen cases.

On 14 cases one case is worth 0.07 of recall, so a gap narrower than that is a single question changing its mind, not a result.

## Where each variant lands, case by case

Rank of the first correct article, `—` when none is retrieved in the top 10.

| Case | `name-only` | `french-question` | `english-verbose` | `name-and-eco` |
|---|---|---|---|---|
| ruy-lopez | 1 | 1 | 6 | 1 |
| italian-game | 2 | 2 | 3 | 4 |
| sicilian | 1 | 1 | 1 | 1 |
| french | 1 | 1 | 2 | 1 |
| scandinavian | 1 | 1 | 1 | 1 |
| scotch | 1 | 1 | 2 | 1 |
| petrov | 1 | 1 | 1 | 1 |
| queens-gambit | 1 | 1 | 1 | 1 |
| slav | 1 | 1 | 5 | 1 |
| kings-indian | 1 | 1 | 1 | 1 |
| english | 1 | 2 | 2 | 1 |
| reti | 1 | 1 | 1 | 1 |
| caro-kann | 1 | 1 | 1 | 1 |
| london | 1 | 1 | 2 | 1 |
