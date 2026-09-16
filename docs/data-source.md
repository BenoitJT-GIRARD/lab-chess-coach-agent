# Where the data comes from

Four sources, and only one of them is a corpus. The knowledge base is thirty-two articles,
twenty-one downloaded and eleven written here. The theory is a live database queried at run
time. The videos are a search API. The engine computes its answer, so it holds no data at
all.

This page says what each one is, what its terms allow, and which of them this repository is
allowed to redistribute. The short answer is: one of the four, and it is the one written here.

## The knowledge base

### Wikichess, twenty-one articles in English

| | |
|---|---|
| Provider | [FICGS Wikichess](https://ficgs.com/wikichess.html) |
| Read on | 2026-09-02 |
| What was taken | 21 articles, each an opening with its ECO code and its main line |
| Where it lands | `backend/var/wikichess/`, which git ignores |
| Index | [`backend/reports/wikichess_manifest.json`](../backend/reports/wikichess_manifest.json) |
| Terms | FICGS reserves the rights on the text of its site |

**The text is not in this repository, and that is a licence decision rather than a size
decision.** The FICGS terms reserve "the general structure, texts, images, graphism, documents,
databases and every element of the site" and allow copying games only, in PGN. So what is
tracked is the index: for each article its title, its ECO code, its opening moves and the page
it came from. One command downloads the articles again:

```bash
cd backend
uv run python -m scripts.fetch_wikichess
```

The index is what makes that command replayable. It names twenty-one pages by URL, so a reader
who runs it gets the same corpus, and not whatever the site holds today; a page that has
since disappeared shows up as a failure, where an unlisted download would simply return a
smaller corpus.

### Eleven notes written in French

Written for this repository, for a club player of about ten years old: the Ruy Lopez, the
Italian, the Sicilian, the French, the Caro-Kann, the Scandinavian, the Scotch, the Queen's
Gambit, the King's Indian, the English and the London System. They live under
`backend/data/openings/` and they are tracked, because they are the repository's own.

They are also the reason the embedding model is multilingual. A French question about a
Spanish opening has to reach an English article about the Ruy Lopez, and it does:
`docs/protocol.md` measures how often.

### What the two folders have in common, and what separates them

| | Wikichess | The written notes |
|---|---|---|
| Language | English | French |
| Tracked by git | no | yes |
| Written by | contributors of the FICGS site | this repository |
| Indexed in the same Milvus collection | yes | yes |

The folder of origin travels with each indexed passage, which is what lets the interface
label an answer: a reader can see whether the explanation in front of them was downloaded or
written here.

## The theory: the Lichess Opening Explorer

| | |
|---|---|
| Provider | [Lichess Opening Explorer](https://lichess.org/api#tag/Opening-Explorer), `masters` database |
| Read at run time | yes, one call per position |
| Frozen reading | 2026-09-07, 54 positions, in [`backend/data/eval/theory_positions.json`](../backend/data/eval/theory_positions.json) |
| Terms | Lichess data is available under the Creative Commons CC0 dedication |
| Key | optional; without one the local opening book answers instead |

The Explorer is a living database: the number of master games reaching a position goes up as
games are added. A sweep that queried it live would never replay, so the fifty-four positions
the threshold study uses were read once, dated, and committed. The agent itself always asks the
live Explorer, because a coach quoting a two-year-old count is quoting the wrong number.

## The videos: the YouTube Data API

| | |
|---|---|
| Provider | [YouTube Data API v3](https://developers.google.com/youtube/v3) |
| What is requested | a search, restricted to the opening name |
| What is kept | the video identifier, its title, its channel and its thumbnail URL |
| Terms | the API terms of service; no video and no thumbnail is stored here |
| Key | optional; without one the videos panel stays empty |

Nothing of YouTube is redistributed. The interface shows a thumbnail served by Google and a
link that opens on YouTube, which is what the terms ask for.

## The engine: Stockfish

| | |
|---|---|
| Provider | [Stockfish](https://stockfishchess.org/), installed in the backend image |
| Licence | GPL-3.0 |
| How it is used | called as a separate process through the `stockfish` package, at depth 15 |

Stockfish computes an evaluation, so it needs no data and carries no provenance question.
Its licence is the reason it is installed in the image and not copied into this repository.

## The embedding model

| | |
|---|---|
| Model | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| Provider | [Hugging Face](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2) |
| Licence | Apache-2.0 |
| Why this one | the questions are French and two thirds of the corpus is English |
| Where it lands | the `hf_cache` volume, downloaded on first use |

## What this repository redistributes

Nothing but its own. The eleven notes and the code are under the licence in
[`LICENSE`](../LICENSE). The Wikichess articles are downloaded by the reader, under FICGS's
terms. The Explorer counts under `backend/data/eval/` are counts of public games with the date
they were read, which is a measurement and not a copy of the database. The screenshots
under `docs/images/` are of this application, showing its own answers, and
[`docs/images/MANIFEST.json`](images/MANIFEST.json) says for each one what was on screen.
