# Does the model cite only the moves it was given?

Measured 2026-09-08 · model `gpt-4o-mini` · 21 positions, 2 passes, 42 calls.

| Citations | Given in the prompt | Legal, not given | No such move | Told as a line |
|---|---|---|---|---|
| 116 | 68 | 1 | 2 | 45 |

None of those citations came back in French notation: this model answered in the notation it was handed. The translation step is still in the reader, and an answer written `Cf3` would be counted as the `Nf3` it was given rather than as an invention.

The last column is the opening's own sequence, cited behind its move number: already played, and left out of the invention count.

Unfiltered reading — every square-looking token counted as a move, including the ones the prose names as places:

| Citations | Given in the prompt | Legal, not given | No such move | Told as a line |
|---|---|---|---|---|
| 185 | 98 | 5 | 37 | 45 |

## What was flagged (3)

- **Caro-Kann Defense** (pass 1) — `e5` = e5, *legal* — « En jouant d4, les Blancs cherchent à contrôler le centre et à préparer une expansion avec e5 dans le futur. »
- **Italian Game** (pass 1) — `a6`, *illegal* — « Pense à la suite de tes coups : si les Noirs jouent a6 pour chasser ton fou, tu pourras envisager de reculer avec Bc4 ou de prendre le cavalier. »
- **Scholar's Attack** (pass 2) — `Qh5`, *illegal* — « Les Blancs ont joué Qh5 pour attaquer le pion en e5, et les Noirs doivent maintenant défendre leur position tout en cherchant à se développer. »
