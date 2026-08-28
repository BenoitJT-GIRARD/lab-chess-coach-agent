# Frontend — interface Angular

L'interface présente un échiquier interactif et le panneau de conseils de
l'agent. Elle parle au backend FastAPI par un chemin relatif (`/api/v1`), ce qui
lui permet de fonctionner aussi bien derrière le proxy nginx du conteneur que
derrière le proxy de `ng serve`.

## D'où vient cette interface

Deux briques viennent d'une interface de démonstration publique :
un projet Angular Material public. On lui
reprend deux choses :

- la librairie d'échiquier **[ngx-chess-board](https://www.npmjs.com/package/ngx-chess-board)**,
  avec ses entrées `[size]`, `[lightTileColor]`, `[darkTileColor]` et sa sortie
  `(moveChange)` ;
- l'habillage **Angular Material** : barre d'outils, cartes, boutons, info-bulles
  et indicateur de chargement.

Le thème Material est reconstruit sur un bleu nuit et un or
(`src/styles.scss`). La police d'icônes est
embarquée dans le paquet `material-icons`, pour que l'application reste
utilisable sans accès à internet pendant la démonstration.

## Organisation

```
src/app/
├── app.component.*              # Coquille : barre de titre
├── chessboard/                  # Échiquier, commandes, positions de démo
├── coach/                       # Panneau de réponse de l'agent
├── models/agent.models.ts       # Types miroir des réponses de l'API
└── services/agent.service.ts    # Appels HTTP vers le backend
```

Le découpage est volontairement simple : `chessboard` tient l'état de la partie
et appelle le backend, `coach-panel` ne fait qu'afficher ce qu'on lui passe.

## Lancer l'interface

```powershell
npm install
npm start          # http://localhost:4200, proxy vers http://localhost:8000
```

Le backend doit tourner à côté (voir `../backend/README.md` ou le
`docker compose up` décrit à la racine).

## Tests

```powershell
npm test -- --watch=false --browsers=ChromeHeadless
```

Les tests couvrent le service HTTP et le panneau de conseils : états de
chargement et d'erreur, affichage de l'ouverture, des coups théoriques, des
parties de référence et des outils utilisés par l'agent.

## Construire l'image

```powershell
docker build -t chess_coach-frontend .
```

Le `Dockerfile` compile l'application avec Node puis la sert avec nginx, qui
relaie `/api/` vers le backend.
