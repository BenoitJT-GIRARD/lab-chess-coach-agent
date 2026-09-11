# Frontend — the Angular interface

An interactive chessboard and the coach's answer panel. It talks to the FastAPI backend
through a relative path (`/api/v1`), which is what lets the same build run behind the
container's nginx proxy and behind the `ng serve` dev proxy without a rebuild.

## What it is built on

Two public bricks, and the attribution matters more than the line count:

- **[ngx-chess-board](https://www.npmjs.com/package/ngx-chess-board)** — the board itself,
  with its `[size]`, `[lightTileColor]`, `[darkTileColor]` inputs and its `(moveChange)`
  output. Version 3.0.0 ships sources only on npm, so the build pins the Ivy-compiled
  2.2.3, which Angular 17 accepts through legacy peer resolution.
- **[Angular Material](https://material.angular.io/)** — toolbar, cards, buttons, chips,
  tooltips and the loading indicator.

The Material theme is built on a navy and a gold (`src/styles.scss`). The icon font is
bundled through the `material-icons` package rather than loaded from Google Fonts, so the
interface stays usable with no internet access — which is also what a demonstration on a
conference network needs.

## Layout

```
src/app/
├── app.component.*              # shell: the title bar
├── chessboard/                  # the board, its controls, the demo positions
├── coach/                       # the answer panel
├── models/agent.models.ts       # types mirroring the API responses
└── services/agent.service.ts    # HTTP calls to the backend
```

The split is deliberately blunt: `chessboard` holds the state of the game and calls the
backend, `coach-panel` only renders what it is handed. A panel that fetched its own data
would make the board's state and the panel's state two things that can disagree.

## Running it

```powershell
npm install
npm start          # http://localhost:4200, proxying to http://localhost:8000
```

The backend has to be running alongside — see `../backend/README.md`, or the
`docker compose up` described at the root.

## Tests

```powershell
npm test -- --watch=false --browsers=ChromeHeadless
```

They cover the HTTP service and the answer panel: loading and error states, the detected
opening, the theoretical moves, the reference games, and the list of tools the agent
actually used.

## Building the image

```powershell
docker build -t chess-coach-frontend .
```

The `Dockerfile` builds the application with Node, then serves it with nginx, which
forwards `/api/` to the backend.
