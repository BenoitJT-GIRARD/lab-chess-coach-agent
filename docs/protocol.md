# How the numbers were measured

The README carries the four tables. This page carries what stands behind them: the design of
each measurement, the population it ran on, and the questions its design is unable to settle.
Every label the tables use is defined once in [`metrics.yaml`](../metrics.yaml), and the
per-case detail of each study sits beside the table it summarises, under
[`backend/reports/`](../backend/reports/).

One property the four share: each replays from a file committed here. No key, no running
stack, and no live call to the site the corpus came from.

## 1. Retrieval: does the wording of the question matter?

### The population

Fourteen questions, each one a thing a club player would type, paired with the articles that
would answer it. Two of the thirty-two articles are about the Ruy Lopez and a French note
covers it as well, so a case is labelled with a *set*: any of the three counts. Labelling a
case with one file chosen among equals would mark a correct retrieval wrong.

**Nothing in a question is taken from the article it points at.** Generating the question from
its own target turns the score into a measure of shared vocabulary, and it improves whenever
the generator and the index agree on how to cut words. The file states this at its top, and
the cases are in
[`backend/data/eval/retrieval_cases.json`](../backend/data/eval/retrieval_cases.json).

### The four wordings

| Variant | What is sent to the embedder |
|---|---|
| `name-only` | the opening name alone, `Ruy Lopez` |
| `french-question` | what the agent sends, the player's question in French |
| `english-verbose` | `chess opening X: main ideas, plans and typical moves` |
| `name-and-eco` | the name followed by its ECO code |

The `french-question` row is not a paraphrase of what the agent does: the script calls the
agent's own `build_context_query`, and a unit test fails if that stops being true. A variant
that reimplements the thing it measures measures the reimplementation.

### What is indexed, and what is not

Each article opens on four quoted lines of codes and links. Until 2026-09-15 they were
indexed along with the prose, which let `name-and-eco` match a code in the query against the
same code in the text. The header is now parsed into fields and dropped before indexing, and the table in the
README is the one measured after that change.

### The scoring

Ten passages come back, and they are collapsed by source file before the cut at k. A single
article occupies several index entries, so without that collapse an opening can hold every
slot of a top three and every variant scores high for a reason that belongs to the chunker.

The score needs no judge: the label is a file name, so a case is right or it is not, and a
second run of the same variant gives the same number.

### What the design cannot settle

One case of fourteen moves recall by 0.071. Two wordings closer together than that are tied as
far as this study can tell, and the README says so where the table shows them. Thirty-two
articles is a small base, too: a high score at rank three is partly a property of a corpus
where the answer is rarely far away.

### Reproducing it

```bash
cd backend
uv run python -m scripts.run_retrieval_ablation     # needs the stack up and ingested
```

## 2. Routing: how sharply does the branch depend on its threshold?

### The population

Fifty-four positions, walked from the curated opening book at several depths, plus eight lines
that no master game reaches. The Explorer was queried once for each, and the answer was written
to [`backend/data/eval/theory_positions.json`](../backend/data/eval/theory_positions.json).

**The reading is frozen and dated on purpose.** The `masters` database grows: a position with
nine hundred games today has eleven hundred next year, and a sweep that queried it live would
publish a different table each month with nothing in the agent having changed. Freezing the
reading is what makes the study a measurement of the threshold instead of the calendar.

### What is varied, and what is read

The threshold alone. For each candidate value the study counts how many of the fifty-four
positions the agent would send to the book, and how many changed side since the value below.
The second count is the one that matters: a row of zeros means the value sits in the middle of
a flat stretch, and no argument is needed to defend it against its neighbours.

The README shows the seven rows around the served value; the full sweep from 0 to 50 000 is in
[`backend/reports/theory_threshold_sweep.md`](../backend/reports/theory_threshold_sweep.md).

### What the design cannot settle

Sensitivity is not correctness. A position sent to the book is answered from master games, and
one sent to the engine is answered from a search; which of the two serves a player better is a
question this study never asks, and could not answer without a judge.

### Reproducing it

```bash
cd backend
uv run python -m scripts.sweep_theory_threshold     # replays the frozen reading, no key
uv run python -m scripts.sample_theory_positions    # re-takes the reading; needs a token
```

## 3. Synthesis: does the model cite only the moves it was handed?

### The population

Twenty-one positions, each answered twice by `gpt-4o-mini` at temperature 0.3. Forty-two billed
calls, and each answer is kept in the JSON beside the table so the reading can be redone for
nothing.

The positions are not a sample. They are every line of the frozen reading that the routing
sent to the engine, plus the twelve shallowest of those it sent to the book, so both branches
of the graph are exercised. That matters because the two branches build different prompts.

### The reader is the measurement

Every move named in an answer is classified against two things: the board that produced it, and
the list of moves the prompt carried. Four outcomes, and the README's table is their counts.

**The parser was wrong the first time, and wrong in the direction that accuses.** Ten citations
came back as moves that do not exist; read one by one, all ten were faults of the parser and
not of the model. A move following a numbered one belongs to the same line although it carries
no number of its own; a square named as a place is not a move; an opening's first move quoted
in its history is not a claim about the board. Each of the three shapes became a unit test on
the sentence that exposed it.

Two consequences follow, and both are visible in what is published. The table comes from a
**fresh** run, so the parser is not scored on the text it was tuned against. And the counts
obtained with every square-looking token read as a move are published beside it, as an upper
bound on what a stricter parser could possibly flag.

### What the design cannot settle

One model at one temperature. The instruction has a second half, about staying silent on the
engine unless an evaluation was supplied, and nothing counts that. The lines the model narrates
are not checked for being the right lines either: the frozen reading holds positions, and a
position says nothing about the order of moves that reached it.

### Reproducing it

```bash
cd backend
uv run python -m scripts.check_move_invention              # 42 billed calls
uv run python -m scripts.check_move_invention --rejudge    # reads the saved answers, free
```

## 4. Latency: what does a question cost?

### The population

Four positions, three repeats each, inside the deployed configuration. Two of the four have
left theory, so the engine node runs on half the sample and the other nodes on all of it.

The language model is switched off for the bench. Its call is billed, its duration belongs to a
third party, and one slow generation would hide every local node behind it.

### What the numbers support

A median over twelve points on one machine is not a service level. What survives that weakness
is the ordering of the nodes, which holds by more than an order of magnitude between the
cheapest and the dearest, and that ordering is what the README reads from the table.

### Reproducing it

```bash
docker compose exec backend python -m scripts.bench_agent
```

## What the four share

**Warnings are errors.** The suite silences nothing wholesale. On a stack built from six
libraries that move quickly, a silenced deprecation is the notice that one of them is about to
change an API underneath a measurement.

**No measurement runs in continuous integration.** The workflows lint, scan and test. They
ingest nothing and they call no paid endpoint, so no published table is a function of when
somebody last pushed.
