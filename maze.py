"""
Maze Lab — Flask web service
Maze generation (recursive backtracking) + BFS / DFS / Dijkstra / A* solvers.
"""

import heapq
import os
import random
import time
from collections import deque

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

class Cell:
    """A single maze cell with four walls (top, right, bottom, left)."""

    __slots__ = ("col", "row", "visited", "walls")

    def __init__(self, col: int, row: int):
        self.col = col
        self.row = row
        self.visited = False
        # walls: [top, right, bottom, left]
        self.walls = [True, True, True, True]

    def to_dict(self):
        return {
            "col": self.col,
            "row": self.row,
            "visited": self.visited,
            "walls": self.walls,
        }


# ---------------------------------------------------------------------------
# Grid helpers
# ---------------------------------------------------------------------------

def make_grid(cols: int, rows: int) -> list[Cell]:
    return [Cell(c, r) for r in range(rows) for c in range(cols)]


def cell_index(col: int, row: int, cols: int, rows: int):
    if col < 0 or row < 0 or col >= cols or row >= rows:
        return None
    return col + row * cols


def remove_walls(a: Cell, b: Cell):
    dx = a.col - b.col
    dy = a.row - b.row
    if dx == 1:
        a.walls[3] = False
        b.walls[1] = False
    elif dx == -1:
        a.walls[1] = False
        b.walls[3] = False
    if dy == 1:
        a.walls[0] = False
        b.walls[2] = False
    elif dy == -1:
        a.walls[2] = False
        b.walls[0] = False


def get_unvisited_neighbors(cell: Cell, grid: list[Cell], cols: int, rows: int) -> list[Cell]:
    neighbors = []
    for dc, dr in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        idx = cell_index(cell.col + dc, cell.row + dr, cols, rows)
        if idx is not None and not grid[idx].visited:
            neighbors.append(grid[idx])
    return neighbors


def open_neighbors(cell: Cell, grid: list[Cell], cols: int, rows: int):
    """Yield cells reachable from *cell* (no wall between them)."""
    for dc, dr, wall_idx in ((0, -1, 0), (1, 0, 1), (0, 1, 2), (-1, 0, 3)):
        if cell.walls[wall_idx]:
            continue
        idx = cell_index(cell.col + dc, cell.row + dr, cols, rows)
        if idx is not None:
            yield grid[idx]


# ---------------------------------------------------------------------------
# Maze generation — recursive backtracking (iterative)
# ---------------------------------------------------------------------------

def generate_maze_complete(cols: int, rows: int) -> list[Cell]:
    """Generate a fully carved maze and return the grid."""
    grid = make_grid(cols, rows)
    current = grid[0]
    current.visited = True
    stack: list[Cell] = []

    while True:
        neighbors = get_unvisited_neighbors(current, grid, cols, rows)
        if neighbors:
            next_cell = random.choice(neighbors)
            stack.append(current)
            remove_walls(current, next_cell)
            next_cell.visited = True
            current = next_cell
        elif stack:
            current = stack.pop()
        else:
            break

    return grid


# ---------------------------------------------------------------------------
# Pathfinding
# ---------------------------------------------------------------------------

def reconstruct_path(came_from: dict, goal_key: tuple) -> list[tuple]:
    path = []
    current = goal_key
    while current is not None:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path


def find_path(
    start: Cell,
    goal: Cell,
    grid: list[Cell],
    cols: int,
    rows: int,
    algorithm: str,
) -> tuple[list[tuple], int, float]:
    """Return (path, visited_count, elapsed_ms)."""
    t0 = time.perf_counter()
    start_key = (start.col, start.row)
    goal_key = (goal.col, goal.row)
    came_from: dict = {start_key: None}
    distances: dict = {start_key: 0}
    searched: set = set()
    visited_count = 0
    counter = 0

    def heuristic(cell: Cell) -> int:
        return abs(cell.col - goal.col) + abs(cell.row - goal.row)

    if algorithm == "BFS":
        frontier: deque | list = deque([start])
    elif algorithm == "DFS":
        frontier = [start]
    else:
        frontier = [(0, 0, start)]

    while frontier:
        if algorithm == "BFS":
            current = frontier.popleft()
        elif algorithm == "DFS":
            current = frontier.pop()
        else:
            current = heapq.heappop(frontier)[2]

        current_key = (current.col, current.row)
        if current_key in searched:
            continue
        searched.add(current_key)
        visited_count += 1

        if current_key == goal_key:
            path = reconstruct_path(came_from, goal_key)
            return path, visited_count, (time.perf_counter() - t0) * 1000

        for neighbor in open_neighbors(current, grid, cols, rows):
            neighbor_key = (neighbor.col, neighbor.row)
            new_dist = distances[current_key] + 1
            if neighbor_key in searched:
                continue
            if neighbor_key in distances and new_dist >= distances[neighbor_key]:
                continue
            came_from[neighbor_key] = current_key
            distances[neighbor_key] = new_dist
            if algorithm == "A*":
                counter += 1
                heapq.heappush(frontier, (new_dist + heuristic(neighbor), counter, neighbor))
            elif algorithm == "Dijkstra":
                counter += 1
                heapq.heappush(frontier, (new_dist, counter, neighbor))
            else:
                frontier.append(neighbor)

    return [], visited_count, (time.perf_counter() - t0) * 1000


SOLVERS = ("BFS", "DFS", "Dijkstra", "A*")


def compare_all_solvers(game: dict) -> list[dict]:
    results = []
    start = game["grid"][0]
    goal = game["goal"]
    grid = game["grid"]
    cols, rows = game["cols"], game["rows"]
    for algo in SOLVERS:
        path, visited, elapsed = find_path(start, goal, grid, cols, rows, algo)
        results.append(
            {
                "algorithm": algo,
                "path_length": len(path),
                "visited": visited,
                "time_ms": round(elapsed, 2),
            }
        )
    return results


# ---------------------------------------------------------------------------
# Collectibles
# ---------------------------------------------------------------------------

def place_collectibles(game: dict):
    candidates = list(range(1, len(game["grid"]) - 1))
    random.shuffle(candidates)
    count = max(4, min(18, (game["cols"] * game["rows"]) // 130))
    game["collectibles"] = set()
    for idx in candidates[:count]:
        cell = game["grid"][idx]
        game["collectibles"].add((cell.col, cell.row))


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

_game: dict | None = None


def new_game(cols: int, rows: int) -> dict:
    cols = max(5, min(120, cols))
    rows = max(5, min(90, rows))
    grid = generate_maze_complete(cols, rows)
    game: dict = {
        "cols": cols,
        "rows": rows,
        "grid": grid,
        "player_col": 0,
        "player_row": 0,
        "goal_col": cols - 1,
        "goal_row": rows - 1,
        "moves": 0,
        "won": False,
        "collectibles": set(),
        "collected": 0,
        "trail": [],          # list of (col, row)
        "solver": None,       # active solver state
        "selected_path": [],  # final path from last completed solve
        "searched": [],       # cells visited by solver (for rendering)
        "frontier": [],       # current frontier (for rendering)
        "comparison": None,
        "selected_solver": None,
    }
    place_collectibles(game)
    return game


def game_to_json(game: dict) -> dict:
    """Serialise game state for the frontend."""
    solver = game.get("solver")
    solver_info = None
    if solver:
        solver_info = {
            "algorithm": solver["algorithm"],
            "visited_count": solver["visited_count"],
            "elapsed_ms": round(solver["elapsed_ms"], 2),
            "done": solver["done"],
        }

    return {
        "cols": game["cols"],
        "rows": game["rows"],
        "cells": [c.to_dict() for c in game["grid"]],
        "player": {"col": game["player_col"], "row": game["player_row"]},
        "goal": {"col": game["goal_col"], "row": game["goal_row"]},
        "moves": game["moves"],
        "won": game["won"],
        "collectibles": [{"col": c, "row": r} for c, r in game["collectibles"]],
        "collected": game["collected"],
        "total_collectibles": game["collected"] + len(game["collectibles"]),
        "trail": [{"col": c, "row": r} for c, r in game["trail"]],
        "selected_path": [{"col": c, "row": r} for c, r in game["selected_path"]],
        "searched": [{"col": c, "row": r} for c, r in game.get("searched", [])],
        "frontier": [{"col": c, "row": r} for c, r in game.get("frontier", [])],
        "comparison": game.get("comparison"),
        "selected_solver": game.get("selected_solver"),
        "solver": solver_info,
    }


# ---------------------------------------------------------------------------
# Solver stepping (called from /api/solve — runs to completion server-side)
# ---------------------------------------------------------------------------

def run_solver(game: dict, algorithm: str):
    """Run the chosen algorithm to completion and store results in game."""
    start = game["grid"][0]
    goal_col, goal_row = game["goal_col"], game["goal_row"]
    goal = game["grid"][cell_index(goal_col, goal_row, game["cols"], game["rows"])]

    t0 = time.perf_counter()
    start_key = (start.col, start.row)
    goal_key = (goal.col, goal.row)
    came_from: dict = {start_key: None}
    distances: dict = {start_key: 0}
    searched: set = set()
    frontier_keys: set = {start_key}
    visited_count = 0
    counter = 0

    # We record the order cells were searched so the frontend can animate
    searched_order: list[tuple] = []
    frontier_snapshots: list[tuple] = []

    def heuristic(cell: Cell) -> int:
        return abs(cell.col - goal.col) + abs(cell.row - goal.row)

    if algorithm == "BFS":
        frontier_q: deque | list = deque([start])
    elif algorithm == "DFS":
        frontier_q = [start]
    else:
        frontier_q = [(0, 0, start)]

    while frontier_q:
        if algorithm == "BFS":
            current = frontier_q.popleft()
        elif algorithm == "DFS":
            current = frontier_q.pop()
        else:
            current = heapq.heappop(frontier_q)[2]

        current_key = (current.col, current.row)
        frontier_keys.discard(current_key)

        if current_key in searched:
            continue
        searched.add(current_key)
        searched_order.append(current_key)
        visited_count += 1

        if current_key == goal_key:
            path = reconstruct_path(came_from, goal_key)
            elapsed = (time.perf_counter() - t0) * 1000
            game["selected_path"] = path
            game["searched"] = searched_order
            game["frontier"] = list(frontier_keys)
            game["selected_solver"] = algorithm
            game["solver"] = {
                "algorithm": algorithm,
                "visited_count": visited_count,
                "elapsed_ms": elapsed,
                "done": True,
            }
            game["comparison"] = compare_all_solvers(game)
            return

        for neighbor in open_neighbors(current, game["grid"], game["cols"], game["rows"]):
            neighbor_key = (neighbor.col, neighbor.row)
            new_dist = distances[current_key] + 1
            if neighbor_key in searched:
                continue
            if neighbor_key in distances and new_dist >= distances[neighbor_key]:
                continue
            came_from[neighbor_key] = current_key
            distances[neighbor_key] = new_dist
            frontier_keys.add(neighbor_key)
            if algorithm == "A*":
                counter += 1
                heapq.heappush(frontier_q, (new_dist + heuristic(neighbor), counter, neighbor))
            elif algorithm == "Dijkstra":
                counter += 1
                heapq.heappush(frontier_q, (new_dist, counter, neighbor))
            else:
                frontier_q.append(neighbor)

    # No path found
    elapsed = (time.perf_counter() - t0) * 1000
    game["searched"] = searched_order
    game["frontier"] = []
    game["selected_solver"] = algorithm
    game["solver"] = {
        "algorithm": algorithm,
        "visited_count": visited_count,
        "elapsed_ms": elapsed,
        "done": True,
    }


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def api_generate():
    global _game
    data = request.get_json(silent=True) or {}
    cols = int(data.get("cols", 25))
    rows = int(data.get("rows", 18))
    _game = new_game(cols, rows)
    return jsonify(game_to_json(_game))


@app.route("/api/state", methods=["GET"])
def api_state():
    if _game is None:
        return jsonify({"error": "No game in progress"}), 404
    return jsonify(game_to_json(_game))


@app.route("/api/move", methods=["POST"])
def api_move():
    global _game
    if _game is None:
        return jsonify({"error": "No game in progress"}), 404

    data = request.get_json(silent=True) or {}
    direction = data.get("direction", "")

    delta = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}.get(direction)
    if delta is None:
        return jsonify({"error": "Invalid direction"}), 400

    dx, dy = delta
    game = _game

    if game["won"]:
        return jsonify(game_to_json(game))

    player_col = game["player_col"]
    player_row = game["player_row"]
    player_cell = game["grid"][cell_index(player_col, player_row, game["cols"], game["rows"])]

    wall_map = {(0, -1): 0, (1, 0): 1, (0, 1): 2, (-1, 0): 3}
    wall_idx = wall_map[(dx, dy)]

    if player_cell.walls[wall_idx]:
        return jsonify({**game_to_json(game), "blocked": True})

    next_idx = cell_index(player_col + dx, player_row + dy, game["cols"], game["rows"])
    if next_idx is None:
        return jsonify(game_to_json(game))

    # Move
    game["trail"].append((player_col, player_row))
    if len(game["trail"]) > 18:
        game["trail"].pop(0)

    game["player_col"] = player_col + dx
    game["player_row"] = player_row + dy
    game["moves"] += 1

    # Collect
    key = (game["player_col"], game["player_row"])
    collected_now = False
    if key in game["collectibles"]:
        game["collectibles"].remove(key)
        game["collected"] += 1
        collected_now = True

    # Win check
    game["won"] = (game["player_col"] == game["goal_col"] and game["player_row"] == game["goal_row"])

    result = game_to_json(game)
    result["collected_now"] = collected_now
    return jsonify(result)


@app.route("/api/solve", methods=["POST"])
def api_solve():
    global _game
    if _game is None:
        return jsonify({"error": "No game in progress"}), 404

    data = request.get_json(silent=True) or {}
    algorithm = data.get("algorithm", "BFS")
    if algorithm not in SOLVERS:
        return jsonify({"error": f"Unknown algorithm. Choose from {SOLVERS}"}), 400

    # Clear previous solve state
    _game["selected_path"] = []
    _game["searched"] = []
    _game["frontier"] = []
    _game["solver"] = None

    run_solver(_game, algorithm)
    return jsonify(game_to_json(_game))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # Generate a default game on startup so /api/state works immediately
    _game = new_game(25, 18)
    app.run(host="0.0.0.0", port=port, debug=False)
