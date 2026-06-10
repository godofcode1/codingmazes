import heapq
import math
import random
import sys
import time
from array import array
from collections import deque

import pygame


START_WIDTH = 1180
START_HEIGHT = 760
MIN_WIDTH = 860
MIN_HEIGHT = 560
FPS = 60
MARGIN = 24
PANEL_WIDTH = 350
SOLVERS = ("BFS", "DFS", "Dijkstra", "A*")

BG = (17, 20, 28)
SURFACE = (25, 30, 42)
PANEL = (31, 38, 52)
PANEL_2 = (40, 49, 66)
FIELD = (43, 51, 68)
FIELD_ACTIVE = (58, 68, 90)
TEXT = (236, 240, 247)
MUTED = (150, 160, 178)
WALL = (230, 235, 244)
VISITED = (47, 57, 82)
ACCENT = (255, 122, 86)
GOOD = (91, 219, 144)
PLAYER = (80, 190, 255)
GOAL = (91, 226, 151)
PATH = (255, 218, 102)
SEARCHED = (78, 104, 156)
FRONTIER = (137, 116, 211)
SHADOW = (8, 10, 16)
COIN = (102, 232, 202)
PIXEL_DARK = (14, 16, 24)
PARTY_COLORS = ((255, 122, 86), (102, 232, 202), (255, 218, 102), (137, 116, 211), (80, 190, 255))

pygame.init()
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
    AUDIO_READY = True
except pygame.error:
    AUDIO_READY = False
WINDOW_FLAGS = pygame.RESIZABLE | pygame.DOUBLEBUF
screen = pygame.display.set_mode((START_WIDTH, START_HEIGHT), WINDOW_FLAGS)
pygame.display.set_caption("Playable Maze Lab")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 20)
small_font = pygame.font.SysFont("consolas", 16)
title_font = pygame.font.SysFont("consolas", 34, bold=True)


def configure_window():
    try:
        from pygame._sdl2 import Window

        window = Window.from_display_module()
        window.resizable = True
        window.minimum_size = (MIN_WIDTH, MIN_HEIGHT)
    except (ImportError, AttributeError, pygame.error):
        pass


configure_window()


class Cell:
    def __init__(self, col, row):
        self.col = col
        self.row = row
        self.visited = False
        self.walls = [True, True, True, True]

    def draw(self, surface, cell_size, origin):
        x = origin[0] + self.col * cell_size
        y = origin[1] + self.row * cell_size
        rect = (x, y, cell_size, cell_size)

        if self.visited:
            pygame.draw.rect(surface, VISITED, rect)

        line_width = 1 if cell_size <= 10 else 2
        if self.walls[0]:
            pygame.draw.line(surface, WALL, (x, y), (x + cell_size, y), line_width)
        if self.walls[1]:
            pygame.draw.line(surface, WALL, (x + cell_size, y), (x + cell_size, y + cell_size), line_width)
        if self.walls[2]:
            pygame.draw.line(surface, WALL, (x + cell_size, y + cell_size), (x, y + cell_size), line_width)
        if self.walls[3]:
            pygame.draw.line(surface, WALL, (x, y + cell_size), (x, y), line_width)


class InputField:
    def __init__(self, label, value, rect, min_value, max_value):
        self.label = label
        self.value = str(value)
        self.rect = pygame.Rect(rect)
        self.min_value = min_value
        self.max_value = max_value

    def handle_key(self, event):
        if event.key == pygame.K_BACKSPACE:
            self.value = self.value[:-1]
        elif event.unicode.isdigit() and len(self.value) < 3:
            self.value += event.unicode

    def number(self):
        if not self.value:
            return self.min_value
        return max(self.min_value, min(self.max_value, int(self.value)))

    def draw(self, active):
        fill = FIELD_ACTIVE if active else FIELD
        pygame.draw.rect(screen, fill, self.rect, border_radius=7)
        pygame.draw.rect(screen, ACCENT if active else PANEL_2, self.rect, 2, border_radius=7)
        draw_text(self.label, (self.rect.x, self.rect.y - 24), MUTED, small_font)
        draw_text(self.value or "_", (self.rect.x + 12, self.rect.y + 10), TEXT, font)


class Button:
    def __init__(self, label, rect, action, kind="normal"):
        self.label = label
        self.rect = pygame.Rect(rect)
        self.action = action
        self.kind = kind

    def draw(self, mouse_pos, selected=False, disabled=False):
        hovered = self.rect.collidepoint(mouse_pos) and not disabled
        if disabled:
            fill = (34, 39, 51)
            border = (55, 62, 78)
            label_color = (104, 112, 130)
        elif selected:
            fill = ACCENT
            border = (255, 180, 135)
            label_color = (18, 20, 26)
        elif hovered:
            fill = (61, 73, 95)
            border = ACCENT
            label_color = TEXT
        else:
            fill = (43, 58, 58) if self.kind == "primary" else PANEL_2
            border = (68, 78, 99)
            label_color = TEXT

        pygame.draw.rect(screen, SHADOW, self.rect.move(0, 3), border_radius=8)
        pygame.draw.rect(screen, fill, self.rect, border_radius=8)
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=8)
        label = small_font.render(self.label, True, label_color)
        screen.blit(label, (self.rect.centerx - label.get_width() // 2, self.rect.centery - label.get_height() // 2))

    def clicked(self, pos):
        return self.rect.collidepoint(pos)


def make_tone(frequency, duration_ms, volume=0.25):
    if not AUDIO_READY:
        return None

    sample_rate = 44100
    sample_count = int(sample_rate * duration_ms / 1000)
    samples = array("h")
    fade = max(1, sample_count // 12)

    for i in range(sample_count):
        envelope = 1.0
        if i < fade:
            envelope = i / fade
        elif i > sample_count - fade:
            envelope = (sample_count - i) / fade
        wave = math.sin(2 * math.pi * frequency * i / sample_rate)
        samples.append(int(32767 * volume * envelope * wave))

    return pygame.mixer.Sound(buffer=samples.tobytes())


SOUNDS = {
    "move": make_tone(360, 38, 0.16),
    "blocked": make_tone(120, 70, 0.14),
    "collect": make_tone(880, 90, 0.20),
    "win": make_tone(660, 180, 0.22),
    "solver": make_tone(520, 90, 0.18),
    "secret": make_tone(990, 160, 0.18),
}


def play_sound(name):
    sound = SOUNDS.get(name)
    if sound is not None:
        sound.play()


def clamp(value, low, high):
    return max(low, min(high, value))


def draw_text(text, pos, color=TEXT, used_font=font):
    screen.blit(used_font.render(text, True, color), pos)


def draw_backdrop():
    width, height = screen.get_size()
    screen.fill(BG)
    step = 32
    dot = (28, 34, 48)
    for x in range(0, width, step):
        for y in range(0, height, step):
            if (x // step + y // step) % 2 == 0:
                pygame.draw.rect(screen, dot, (x + 12, y + 12, 4, 4))


def make_grid(cols, rows):
    return [Cell(c, r) for r in range(rows) for c in range(cols)]


def index(col, row, cols, rows):
    if col < 0 or row < 0 or col >= cols or row >= rows:
        return None
    return col + row * cols


def remove_walls(a, b):
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


def get_unvisited_neighbors(cell, grid, cols, rows):
    neighbors = []
    for col, row in (
        (cell.col, cell.row - 1),
        (cell.col + 1, cell.row),
        (cell.col, cell.row + 1),
        (cell.col - 1, cell.row),
    ):
        idx = index(col, row, cols, rows)
        if idx is not None and not grid[idx].visited:
            neighbors.append(grid[idx])
    return neighbors


def open_neighbors(cell, grid, cols, rows):
    for dx, dy, wall_idx in ((0, -1, 0), (1, 0, 1), (0, 1, 2), (-1, 0, 3)):
        if cell.walls[wall_idx]:
            continue
        idx = index(cell.col + dx, cell.row + dy, cols, rows)
        if idx is not None:
            yield grid[idx]


def reconstruct_path(came_from, goal_key):
    path = []
    current_key = goal_key
    while current_key is not None:
        path.append(current_key)
        current_key = came_from[current_key]
    path.reverse()
    return path


def find_path(start, goal, grid, cols, rows, algorithm):
    start_key = (start.col, start.row)
    goal_key = (goal.col, goal.row)
    came_from = {start_key: None}
    distances = {start_key: 0}
    searched = set()
    visited_count = 0

    def heuristic(cell):
        return abs(cell.col - goal.col) + abs(cell.row - goal.row)

    if algorithm == "BFS":
        frontier = deque([start])
    elif algorithm == "DFS":
        frontier = [start]
    else:
        frontier = [(0, 0, start)]
        counter = 0

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
            return reconstruct_path(came_from, goal_key), visited_count

        for neighbor in open_neighbors(current, grid, cols, rows):
            neighbor_key = (neighbor.col, neighbor.row)
            new_distance = distances[current_key] + 1
            if neighbor_key in searched:
                continue
            if neighbor_key in distances and new_distance >= distances[neighbor_key]:
                continue

            came_from[neighbor_key] = current_key
            distances[neighbor_key] = new_distance

            if algorithm == "A*":
                counter += 1
                heapq.heappush(frontier, (new_distance + heuristic(neighbor), counter, neighbor))
            elif algorithm == "Dijkstra":
                counter += 1
                heapq.heappush(frontier, (new_distance, counter, neighbor))
            else:
                frontier.append(neighbor)

    return [], visited_count


def compare_solvers(start, goal, grid, cols, rows):
    results = []
    for algorithm in SOLVERS:
        t0 = time.perf_counter()
        path, visited_count = find_path(start, goal, grid, cols, rows, algorithm)
        results.append(
            {
                "algorithm": algorithm,
                "path_length": len(path),
                "visited": visited_count,
                "time_ms": (time.perf_counter() - t0) * 1000,
            }
        )
    return results


def start_solver(game, solver):
    start = game["grid"][0]
    start_key = (start.col, start.row)
    if solver in ("BFS", "DFS"):
        frontier = deque([start]) if solver == "BFS" else [start]
    else:
        frontier = [(0, 0, start)]

    game["selected_solver"] = solver
    game["selected_path"] = []
    game["comparison"] = None
    game["solver"] = {
        "algorithm": solver,
        "frontier": frontier,
        "frontier_keys": {start_key},
        "came_from": {start_key: None},
        "distances": {start_key: 0},
        "searched": set(),
        "visited_count": 0,
        "counter": 0,
        "started_at": time.perf_counter(),
        "elapsed_ms": 0,
        "done": False,
    }
    set_message(game, f"{solver} is searching...", PATH, 1.6)
    play_sound("solver")


def compare_all(game):
    game["comparison"] = compare_solvers(game["grid"][0], game["goal"], game["grid"], game["cols"], game["rows"])
    set_message(game, "Comparison ready. Tiny spreadsheets, big drama.", GOOD, 2.0)


def solver_step(game, steps):
    solver = game["solver"]
    goal = game["goal"]
    goal_key = (goal.col, goal.row)
    algorithm = solver["algorithm"]

    def heuristic(cell):
        return abs(cell.col - goal.col) + abs(cell.row - goal.row)

    for _ in range(steps):
        frontier = solver["frontier"]
        if not frontier:
            solver["done"] = True
            solver["elapsed_ms"] = (time.perf_counter() - solver["started_at"]) * 1000
            return True

        if algorithm == "BFS":
            current = frontier.popleft()
        elif algorithm == "DFS":
            current = frontier.pop()
        else:
            current = heapq.heappop(frontier)[2]

        current_key = (current.col, current.row)
        solver["frontier_keys"].discard(current_key)
        if current_key in solver["searched"]:
            continue

        solver["searched"].add(current_key)
        solver["visited_count"] += 1

        if current_key == goal_key:
            game["selected_path"] = reconstruct_path(solver["came_from"], goal_key)
            game["comparison"] = compare_solvers(game["grid"][0], game["goal"], game["grid"], game["cols"], game["rows"])
            solver["done"] = True
            solver["elapsed_ms"] = (time.perf_counter() - solver["started_at"]) * 1000
            return True

        for neighbor in open_neighbors(current, game["grid"], game["cols"], game["rows"]):
            neighbor_key = (neighbor.col, neighbor.row)
            new_distance = solver["distances"][current_key] + 1
            if neighbor_key in solver["searched"]:
                continue
            if neighbor_key in solver["distances"] and new_distance >= solver["distances"][neighbor_key]:
                continue

            solver["came_from"][neighbor_key] = current_key
            solver["distances"][neighbor_key] = new_distance
            solver["frontier_keys"].add(neighbor_key)

            if algorithm == "A*":
                solver["counter"] += 1
                heapq.heappush(frontier, (new_distance + heuristic(neighbor), solver["counter"], neighbor))
            elif algorithm == "Dijkstra":
                solver["counter"] += 1
                heapq.heappush(frontier, (new_distance, solver["counter"], neighbor))
            else:
                frontier.append(neighbor)

    solver["elapsed_ms"] = (time.perf_counter() - solver["started_at"]) * 1000
    return False


def maze_layout():
    width, height = screen.get_size()
    panel_width = min(PANEL_WIDTH, max(250, width // 4))
    panel_rect = pygame.Rect(width - panel_width, 0, panel_width, height)
    maze_rect = pygame.Rect(MARGIN, MARGIN, width - panel_width - MARGIN * 2, height - MARGIN * 2)
    return maze_rect, panel_rect


def resize_window(width, height, game):
    global screen
    width = max(MIN_WIDTH, width)
    height = max(MIN_HEIGHT, height)
    screen = pygame.display.set_mode((width, height), WINDOW_FLAGS)
    pygame.display.set_caption("Playable Maze Lab")
    configure_window()
    if game is not None:
        fit_maze(game)


def fit_maze(game):
    maze_rect, _ = maze_layout()
    cell_size = max(5, min(32, maze_rect.width // game["cols"], maze_rect.height // game["rows"]))
    maze_width = game["cols"] * cell_size
    maze_height = game["rows"] * cell_size
    game["cell_size"] = cell_size
    game["origin"] = (
        maze_rect.x + (maze_rect.width - maze_width) // 2,
        maze_rect.y + (maze_rect.height - maze_height) // 2,
    )


def start_maze(cols, rows):
    grid = make_grid(cols, rows)
    current = grid[0]
    current.visited = True
    game = {
        "cols": cols,
        "rows": rows,
        "grid": grid,
        "current": current,
        "stack": [],
        "player": grid[0],
        "goal": grid[-1],
        "moves": 0,
        "comparison": None,
        "selected_solver": None,
        "selected_path": [],
        "solver": None,
        "won": False,
        "collectibles": set(),
        "collected": 0,
        "message": "Find the exit. Grab shiny data shards if you feel fancy.",
        "message_color": MUTED,
        "message_until": time.perf_counter() + 3.0,
        "player_dir": (1, 0),
        "player_draw": [0.0, 0.0],
        "party": False,
        "trail": [],
        "secret_typed": "",
        "cell_size": 12,
        "origin": (MARGIN, MARGIN),
    }
    fit_maze(game)
    return game


def generation_speed(game):
    return clamp((game["cols"] * game["rows"]) // 28, 16, 260)


def solver_speed(game):
    return clamp((game["cols"] * game["rows"]) // 90, 4, 90)


def generation_progress(game):
    visited = sum(1 for cell in game["grid"] if cell.visited)
    return visited / len(game["grid"])


def generation_step(game, steps):
    for _ in range(steps):
        neighbors = get_unvisited_neighbors(game["current"], game["grid"], game["cols"], game["rows"])
        if neighbors:
            next_cell = random.choice(neighbors)
            game["stack"].append(game["current"])
            remove_walls(game["current"], next_cell)
            next_cell.visited = True
            game["current"] = next_cell
        elif game["stack"]:
            game["current"] = game["stack"].pop()
        else:
            return True
    return False


def set_message(game, text, color=MUTED, seconds=2.0):
    game["message"] = text
    game["message_color"] = color
    game["message_until"] = time.perf_counter() + seconds


def place_collectibles(game):
    candidates = list(range(1, len(game["grid"]) - 1))
    random.shuffle(candidates)
    count = clamp((game["cols"] * game["rows"]) // 130, 4, 18)
    game["collectibles"] = set()
    for idx in candidates[:count]:
        cell = game["grid"][idx]
        game["collectibles"].add((cell.col, cell.row))


def collect_here(game):
    key = (game["player"].col, game["player"].row)
    if key in game["collectibles"]:
        game["collectibles"].remove(key)
        game["collected"] += 1
        set_message(game, random.choice([
            "Data shard acquired.",
            "Tiny sparkle successfully looted.",
            "The maze approves. Probably.",
            "Inventory: one suspiciously useful pixel.",
        ]), COIN, 2.0)
        play_sound("collect")


def setup_layout(fields, buttons):
    width, height = screen.get_size()
    card = pygame.Rect(0, 0, min(680, width - MARGIN * 2), 430)
    card.center = (width // 2, height // 2)
    fields[0].rect = pygame.Rect(card.x + 42, card.y + 184, 150, 50)
    fields[1].rect = pygame.Rect(card.x + 226, card.y + 184, 150, 50)
    buttons[0].rect = pygame.Rect(card.x + 42, card.y + 304, 176, 46)
    buttons[1].rect = pygame.Rect(card.x + 236, card.y + 304, 104, 46)
    return card


def draw_setup(fields, active_field, buttons, mouse_pos):
    draw_backdrop()
    card = setup_layout(fields, buttons)
    pygame.draw.rect(screen, SHADOW, card.move(0, 8), border_radius=16)
    pygame.draw.rect(screen, SURFACE, card, border_radius=16)
    pygame.draw.rect(screen, PANEL_2, card, 2, border_radius=16)
    draw_text("Playable Maze Lab", (card.x + 42, card.y + 42), TEXT, title_font)
    draw_text("Create it visually. Play it yourself. Then watch solvers race their way through.", (card.x + 44, card.y + 98), MUTED, small_font)

    for i, field in enumerate(fields):
        field.draw(i == active_field)

    draw_text("Recommended: 25 x 18. Big mazes generate faster now.", (card.x + 44, card.y + 260), MUTED, small_font)
    for button in buttons:
        button.draw(mouse_pos)


def draw_maze(game):
    playfield = pygame.Rect(
        game["origin"][0] - 8,
        game["origin"][1] - 8,
        game["cols"] * game["cell_size"] + 16,
        game["rows"] * game["cell_size"] + 16,
    )
    pygame.draw.rect(screen, SHADOW, playfield.move(0, 6), border_radius=10)
    pygame.draw.rect(screen, SURFACE, playfield, border_radius=10)
    pygame.draw.rect(screen, PANEL_2, playfield, 2, border_radius=10)

    for cell in game["grid"]:
        cell.draw(screen, game["cell_size"], game["origin"])

    draw_collectibles(game)
    draw_solver_search(game)
    draw_path(game)

    if game["current"] is not None:
        draw_cell_marker(game["current"], game, ACCENT, 0.42)

    draw_trail(game)
    draw_goal(game)
    draw_player(game)


def draw_collectibles(game):
    size = game["cell_size"]
    for col, row in game["collectibles"]:
        x = game["origin"][0] + col * size
        y = game["origin"][1] + row * size
        pad = max(2, size // 4)
        color = random.choice(PARTY_COLORS) if game["party"] and pygame.time.get_ticks() % 240 < 80 else COIN
        pygame.draw.rect(screen, color, (x + pad, y + pad, size - pad * 2, size - pad * 2))
        if size >= 14:
            pygame.draw.rect(screen, TEXT, (x + size // 2 - 1, y + pad + 2, 2, 2))


def draw_trail(game):
    size = game["cell_size"]
    for i, (col, row) in enumerate(game["trail"]):
        alpha_scale = (i + 1) / max(1, len(game["trail"]))
        trail_size = max(2, int(size * 0.22 * alpha_scale))
        x = game["origin"][0] + col * size + size // 2 - trail_size // 2
        y = game["origin"][1] + row * size + size // 2 - trail_size // 2
        pygame.draw.rect(screen, (55, 150, 210), (x, y, trail_size, trail_size))


def draw_solver_search(game):
    solver = game["solver"]
    if not solver:
        return

    size = game["cell_size"]
    pad = 2 if size > 9 else 1
    for col, row in solver["searched"]:
        pygame.draw.rect(
            screen,
            SEARCHED,
            (game["origin"][0] + col * size + pad, game["origin"][1] + row * size + pad, size - pad * 2, size - pad * 2),
        )
    for col, row in solver["frontier_keys"]:
        pygame.draw.rect(
            screen,
            FRONTIER,
            (game["origin"][0] + col * size + pad, game["origin"][1] + row * size + pad, size - pad * 2, size - pad * 2),
        )


def draw_path(game):
    if len(game["selected_path"]) < 2:
        return

    size = game["cell_size"]
    points = [
        (game["origin"][0] + col * size + size // 2, game["origin"][1] + row * size + size // 2)
        for col, row in game["selected_path"]
    ]
    pygame.draw.lines(screen, PATH, False, points, max(3, size // 4))


def draw_cell_marker(cell, game, color, scale):
    size = game["cell_size"]
    marker_size = max(4, int(size * scale))
    offset = (size - marker_size) // 2
    x = game["origin"][0] + cell.col * size + offset
    y = game["origin"][1] + cell.row * size + offset
    pygame.draw.rect(screen, color, (x, y, marker_size, marker_size), border_radius=3)


def draw_goal(game):
    size = game["cell_size"]
    cell = game["goal"]
    x = game["origin"][0] + cell.col * size
    y = game["origin"][1] + cell.row * size
    pad = max(2, size // 5)
    pygame.draw.rect(screen, GOAL, (x + pad, y + pad, size - pad * 2, size - pad * 2))
    if size >= 13:
        pygame.draw.rect(screen, TEXT, (x + pad + 2, y + pad + 2, size - pad * 2 - 4, 2))


def update_player_animation(game):
    target_col = float(game["player"].col)
    target_row = float(game["player"].row)
    draw_col, draw_row = game["player_draw"]
    speed = 0.32
    draw_col += (target_col - draw_col) * speed
    draw_row += (target_row - draw_row) * speed

    if abs(target_col - draw_col) < 0.01:
        draw_col = target_col
    if abs(target_row - draw_row) < 0.01:
        draw_row = target_row

    game["player_draw"] = [draw_col, draw_row]


def draw_player(game):
    size = game["cell_size"]
    draw_col, draw_row = game["player_draw"]
    x = game["origin"][0] + draw_col * size
    y = game["origin"][1] + draw_row * size
    unit = max(1, size // 6)
    bob = 1 if pygame.time.get_ticks() // 180 % 2 == 0 else 0

    body = pygame.Rect(int(x + unit), int(y + unit + bob), size - unit * 2, size - unit * 2)
    pygame.draw.rect(screen, PLAYER, body)
    pygame.draw.rect(screen, PIXEL_DARK, body, max(1, unit // 2))

    eye_y = int(y + unit * 2 + bob)
    if game["player_dir"][0] >= 0:
        eye_xs = (int(x + size - unit * 3), int(x + size - unit * 2))
    else:
        eye_xs = (int(x + unit * 2), int(x + unit * 3))
    for eye_x in eye_xs:
        pygame.draw.rect(screen, TEXT, (eye_x, eye_y, max(1, unit), max(1, unit)))

    hat_color = random.choice(PARTY_COLORS) if game["party"] else ACCENT
    pygame.draw.rect(screen, hat_color, (int(x + unit * 2), int(y + bob), size - unit * 4, max(2, unit)))
    pygame.draw.rect(screen, hat_color, (int(x + unit * 3), int(y - unit + bob), size - unit * 6, max(2, unit * 2)))


def play_button_layout(buttons):
    _, panel = maze_layout()
    x = panel.x + 20
    y = 218
    half = (panel.width - 48) // 2
    buttons[0].rect = pygame.Rect(x, y, half, 36)
    buttons[1].rect = pygame.Rect(x + half + 8, y, half, 36)
    buttons[2].rect = pygame.Rect(x, y + 46, panel.width - 40, 36)
    y += 96
    for i, button in enumerate(buttons[3:]):
        col = i % 2
        row = i // 2
        button.rect = pygame.Rect(x + col * (half + 8), y + row * 44, half, 36)


def draw_progress(rect, value, color):
    value = clamp(value, 0, 1)
    pygame.draw.rect(screen, FIELD, rect, border_radius=6)
    fill = pygame.Rect(rect.x, rect.y, int(rect.width * value), rect.height)
    pygame.draw.rect(screen, color, fill, border_radius=6)
    pygame.draw.rect(screen, PANEL_2, rect, 2, border_radius=6)


def draw_panel(game, mode, buttons, mouse_pos):
    _, panel = maze_layout()
    pygame.draw.rect(screen, PANEL, panel)
    pygame.draw.line(screen, (55, 64, 82), (panel.x, 0), (panel.x, panel.height), 2)

    draw_text("Maze Lab", (panel.x + 20, 24), TEXT, title_font)
    draw_text(f"{game['cols']} x {game['rows']} cells", (panel.x + 22, 78), MUTED, small_font)
    draw_text(f"Moves: {game['moves']}", (panel.x + 22, 104), MUTED, small_font)
    total_shards = game["collected"] + len(game["collectibles"])
    draw_text(f"Shards: {game['collected']} / {total_shards}", (panel.x + 126, 104), COIN, small_font)

    if mode == "generating":
        draw_text("Generating maze", (panel.x + 22, 128), ACCENT, small_font)
        draw_progress(pygame.Rect(panel.x + 20, 132 + 24, panel.width - 40, 12), generation_progress(game), ACCENT)
    elif mode == "solving" and game["solver"]:
        solver = game["solver"]
        draw_text(f"{solver['algorithm']} is solving", (panel.x + 22, 128), PATH, small_font)
        draw_text(f"Visited: {solver['visited_count']}", (panel.x + 22, 148), MUTED, small_font)
    elif game["won"]:
        draw_text("Goal reached", (panel.x + 22, 128), GOOD, small_font)
    else:
        draw_text("Play with WASD, arrows, or clicks.", (panel.x + 22, 128), MUTED, small_font)

    if time.perf_counter() < game["message_until"]:
        draw_text(game["message"], (panel.x + 22, 182), game["message_color"], small_font)

    play_button_layout(buttons)
    disabled = mode == "generating"
    for button in buttons:
        selected = button.action == f"solver:{game['selected_solver']}"
        button.draw(mouse_pos, selected=selected, disabled=disabled)

    y = buttons[-1].rect.bottom + 28
    if game["comparison"]:
        table = pygame.Rect(panel.x + 20, y - 8, panel.width - 40, 146)
        pygame.draw.rect(screen, (24, 30, 42), table, border_radius=8)
        pygame.draw.rect(screen, PANEL_2, table, 2, border_radius=8)
        draw_text("Comparison", (panel.x + 32, y + 6), TEXT, font)
        y += 34
        draw_text("Solver      Path  Seen   ms", (panel.x + 32, y), MUTED, small_font)
        y += 22
        for result in game["comparison"]:
            draw_text(
                f"{result['algorithm']:<9} {result['path_length']:>4} {result['visited']:>5} {result['time_ms']:>5.1f}",
                (panel.x + 32, y),
                TEXT,
                small_font,
            )
            y += 22
        y = table.bottom + 18

    if game["selected_solver"]:
        draw_text(f"Selected: {game['selected_solver']}", (panel.x + 22, y), PATH, small_font)
        y += 24
    draw_text("Blue = searched", (panel.x + 22, y), SEARCHED, small_font)
    draw_text("Purple = frontier", (panel.x + 22, y + 22), FRONTIER, small_font)
    draw_text("Yellow = final path", (panel.x + 22, y + 44), PATH, small_font)
    draw_text("P: party pixels", (panel.x + 22, y + 74), MUTED, small_font)
    draw_text("C: watch selected solver", (panel.x + 22, y + 96), MUTED, small_font)


def build_setup_buttons():
    return [
        Button("Generate Maze", (0, 0, 176, 46), "generate", "primary"),
        Button("Quit", (0, 0, 104, 46), "quit"),
    ]


def build_play_buttons():
    buttons = [
        Button("New Maze", (0, 0, 10, 10), "new"),
        Button("Regenerate", (0, 0, 10, 10), "reset"),
        Button("Compare All", (0, 0, 10, 10), "compare", "primary"),
    ]
    for solver in SOLVERS:
        buttons.append(Button(f"Watch {solver}", (0, 0, 10, 10), f"solver:{solver}"))
    return buttons


def move_player(game, dx, dy):
    if game["won"]:
        return

    game["player_dir"] = (dx, dy)
    wall_idx = {(0, -1): 0, (1, 0): 1, (0, 1): 2, (-1, 0): 3}[(dx, dy)]
    player = game["player"]
    if player.walls[wall_idx]:
        set_message(game, random.choice(["Wall says no.", "Bonk.", "That route is decorative.", "Solid pixels ahead."]), ACCENT, 1.0)
        play_sound("blocked")
        return

    next_idx = index(player.col + dx, player.row + dy, game["cols"], game["rows"])
    if next_idx is None:
        return

    game["player"] = game["grid"][next_idx]
    game["trail"].append((player.col, player.row))
    if len(game["trail"]) > 18:
        game["trail"].pop(0)
    game["moves"] += 1
    play_sound("move")
    collect_here(game)
    game["won"] = game["player"] == game["goal"]
    if game["won"]:
        set_message(game, f"Exit found in {game['moves']} moves. Stylish.", GOOD, 4.0)
        play_sound("win")


def cell_at_pos(game, pos):
    x = pos[0] - game["origin"][0]
    y = pos[1] - game["origin"][1]
    if x < 0 or y < 0:
        return None

    col = x // game["cell_size"]
    row = y // game["cell_size"]
    idx = index(col, row, game["cols"], game["rows"])
    if idx is None:
        return None
    return game["grid"][idx]


def toggle_maximize():
    try:
        from pygame._sdl2 import Window

        window = Window.from_display_module()
        if getattr(window, "maximized", False):
            window.restore()
        else:
            window.maximize()
    except (ImportError, AttributeError, pygame.error):
        width, height = screen.get_size()
        if width < 1200 or height < 760:
            resize_window(START_WIDTH, START_HEIGHT, game)
        else:
            resize_window(MIN_WIDTH, MIN_HEIGHT, game)


def minimize_window():
    try:
        from pygame._sdl2 import Window

        Window.from_display_module().minimize()
    except (ImportError, AttributeError, pygame.error):
        pygame.display.iconify()


fields = [
    InputField("Columns", 25, (0, 0, 150, 50), 5, 120),
    InputField("Rows", 18, (0, 0, 150, 50), 5, 90),
]
setup_buttons = build_setup_buttons()
play_buttons = build_play_buttons()
active_field = 0
mode = "setup"
game = None
running = True

while running:
    clock.tick(FPS)
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            resize_window(event.w, event.h, game)

        elif event.type == getattr(pygame, "WINDOWSIZECHANGED", -1):
            resize_window(event.x, event.y, game)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if mode == "setup":
                setup_layout(fields, setup_buttons)
                for i, field in enumerate(fields):
                    if field.rect.collidepoint(event.pos):
                        active_field = i

                for button in setup_buttons:
                    if button.clicked(event.pos):
                        if button.action == "generate":
                            game = start_maze(fields[0].number(), fields[1].number())
                            mode = "generating"
                        elif button.action == "quit":
                            running = False

            elif mode in ("playing", "solving") and game is not None:
                play_button_layout(play_buttons)
                clicked_button = False
                for button in play_buttons:
                    if button.clicked(event.pos):
                        clicked_button = True
                        if button.action == "new":
                            mode = "setup"
                            game = None
                        elif button.action == "reset":
                            game = start_maze(game["cols"], game["rows"])
                            mode = "generating"
                        elif button.action == "compare":
                            compare_all(game)
                        elif button.action.startswith("solver:"):
                            start_solver(game, button.action.split(":", 1)[1])
                            mode = "solving"

                if not clicked_button and mode == "playing" and game is not None:
                    target = cell_at_pos(game, event.pos)
                    if target is not None:
                        dx = target.col - game["player"].col
                        dy = target.row - game["player"].row
                        if abs(dx) + abs(dy) == 1:
                            move_player(game, dx, dy)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_F11:
                toggle_maximize()
            elif event.key == pygame.K_m and pygame.key.get_mods() & pygame.KMOD_CTRL:
                minimize_window()

            if mode == "setup":
                if event.key == pygame.K_TAB:
                    active_field = (active_field + 1) % len(fields)
                elif event.key == pygame.K_RETURN:
                    game = start_maze(fields[0].number(), fields[1].number())
                    mode = "generating"
                else:
                    fields[active_field].handle_key(event)

            elif mode in ("generating", "playing", "solving"):
                if event.key == pygame.K_n:
                    mode = "setup"
                    game = None
                elif event.key == pygame.K_r and game is not None:
                    game = start_maze(game["cols"], game["rows"])
                    mode = "generating"
                elif event.key == pygame.K_p and game is not None:
                    game["party"] = not game["party"]
                    set_message(game, "Party pixels enabled." if game["party"] else "Party pixels resting.", random.choice(PARTY_COLORS), 2.0)
                    play_sound("secret")

                if mode == "playing" and game is not None:
                    if event.key in (pygame.K_w, pygame.K_UP):
                        move_player(game, 0, -1)
                    elif event.key in (pygame.K_d, pygame.K_RIGHT):
                        move_player(game, 1, 0)
                    elif event.key in (pygame.K_s, pygame.K_DOWN):
                        move_player(game, 0, 1)
                    elif event.key in (pygame.K_a, pygame.K_LEFT):
                        move_player(game, -1, 0)
                    elif event.key == pygame.K_c:
                        compare_all(game)
                    elif event.unicode and event.unicode.isalpha():
                        game["secret_typed"] = (game["secret_typed"] + event.unicode.lower())[-8:]
                        if game["secret_typed"].endswith("pizza"):
                            game["party"] = True
                            set_message(game, "Secret pizza mode: hat colors are now less responsible.", PATH, 3.0)
                            play_sound("secret")

    if mode == "setup":
        draw_setup(fields, active_field, setup_buttons, mouse_pos)

    elif game is not None:
        draw_backdrop()
        update_player_animation(game)
        if mode == "generating":
            finished = generation_step(game, generation_speed(game))
            if finished:
                game["current"] = None
                place_collectibles(game)
                set_message(game, "Maze ready. The tiny hero awaits orders.", GOOD, 2.5)
                mode = "playing"
        elif mode == "solving":
            finished = solver_step(game, solver_speed(game))
            if finished:
                mode = "playing"

        draw_maze(game)
        draw_panel(game, mode, play_buttons, mouse_pos)

    pygame.display.flip()

pygame.quit()
sys.exit()
