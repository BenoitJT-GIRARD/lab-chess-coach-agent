# Routing threshold — how sharply the agent's only branch depends on it

- Explorer read on: 2026-09-07 (database `masters`)
- Positions: 54, walked from the curated opening book at several depths, plus eight lines nobody plays
- Served threshold: **1000** master games

| Threshold | In theory | Out of theory | Positions that flipped |
|---|---|---|---|
| 0 | 53 | 1 | 0 |
| 10 | 53 | 1 | 0 |
| 50 | 49 | 5 | 4 |
| 100 | 48 | 6 | 1 |
| 250 | 47 | 7 | 1 |
| 500 | 47 | 7 | 0 |
| **1000** | 45 | 9 | 2 |
| 2500 | 45 | 9 | 0 |
| 5000 | 45 | 9 | 0 |
| 10000 | 41 | 13 | 4 |
| 25000 | 28 | 26 | 13 |
| 50000 | 24 | 30 | 4 |

Divide the served threshold by 3 and **2 of 54** positions change side; multiply it by 3 and **0** do.

The reading is frozen on purpose. The Explorer is a living database and these counts move; the sweep runs on the file so that it replays.
