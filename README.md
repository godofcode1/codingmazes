# Maze Lab

A browser-based maze generation and pathfinding visualiser, deployable as a Railway web service.

## Features

- **Recursive-backtracking** maze generation — every maze is a perfect maze (exactly one path between any two cells)
- **Interactive player** — move with Arrow keys or WASD; collect glowing data shards scattered through the maze
- **Four pathfinding solvers** — watch BFS, DFS, Dijkstra, and A* animate their search in real time
- **Comparison table** — run all four solvers and compare path length, cells visited, and wall-clock time
- **Canvas renderer** — dark-theme pixel art style with smooth player interpolation and solver animation replay

## API

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `GET`  | `/api/state` | — | Current game state (grid, player, goal, solver results) |
| `POST` | `/api/generate` | `{"cols": 25, "rows": 18}` | Generate a new maze |
| `POST` | `/api/move` | `{"direction": "up\|down\|left\|right"}` | Move the player one cell |
| `POST` | `/api/solve` | `{"algorithm": "BFS\|DFS\|Dijkstra\|A*"}` | Run a pathfinding algorithm |

## Running locally

```bash
pip install -r requirements.txt
python maze.py          # dev server on :8080
```

Or with gunicorn:

```bash
gunicorn maze:app --bind 0.0.0.0:8080
```

## Deploying to Railway

Push this repository to Railway. The `Procfile` configures gunicorn automatically. Set the `PORT` environment variable if needed (Railway injects it by default).
