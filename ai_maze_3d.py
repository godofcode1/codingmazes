import math
import random
import sys
from collections import defaultdict, deque

import pygame


WIDTH = 1200
HEIGHT = 800
MIN_WIDTH = 980
MIN_HEIGHT = 640
FPS = 60

COLS = 16
ROWS = 16
ACTIONS = ((0, -1), (1, 0), (0, 1), (-1, 0))
ACTION_NAMES = ("UP", "RIGHT", "DOWN", "LEFT")

BG = (13, 16, 25)
PANEL = (27, 34, 48)
PANEL_2 = (38, 48, 66)
TEXT = (238, 242, 250)
MUTED = (142, 153, 174)
ACCENT = (255, 132, 86)
GOOD = (92, 222, 149)
BAD = (255, 90, 120)
WALL_TOP = (70, 86, 112)
WALL_SIDE = (39, 49, 67)
FLOOR = (31, 39, 55)
FLOOR_ALT = (36, 45, 63)
PATH = (255, 218, 102)
AGENT = (87, 196, 255)
GOAL = (98, 232, 154)
SEARCH = (128, 114, 215)
SHADOW = (5, 7, 12)

pygame.init()
FLAGS = pygame.RESIZABLE | pygame.DOUBLEBUF
screen = pygame.display.set_mode((WIDTH, HEIGHT), FLAGS)
pygame.display.set_caption("AI Maze Trainer 3D")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 18)
small_font = pygame.font.SysFont("consolas", 15)
title_font = pygame.font.SysFont("consolas", 34, bold=True)


class Cell:
    def __init__(self, col, row):
        self.col = col
        self.row = row
        self.visited = False
        self.walls = [True, True, True, True]


def draw_text(text, pos, color=TEXT, used_font=font):
    screen.blit(used_font.render(text, True, color), pos)


def clamp(value, low, high):
    return max(low, min(high, value))


def index(col, row):
    if col < 0 or row < 0 or col >= COLS or row >= ROWS:
        return None
    return col + row * COLS


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


def make_maze():
    grid = [Cell(c, r) for r in range(ROWS) for c in range(COLS)]
    current = grid[0]
    current.visited = True
    stack = []

    while True:
        neighbors = []
        for col, row in ((current.col, current.row - 1), (current.col + 1, current.row), (current.col, current.row + 1), (current.col - 1, current.row)):
            idx = index(col, row)
            if idx is not None and not grid[idx].visited:
                neighbors.append(grid[idx])

        if neighbors:
            nxt = random.choice(neighbors)
            stack.append(current)
            remove_walls(current, nxt)
            nxt.visited = True
            current = nxt
        elif stack:
            current = stack.pop()
        else:
            break

    return grid


def open_actions(grid, state):
    cell = grid[index(*state)]
    actions = []
    for action_id, (dx, dy) in enumerate(ACTIONS):
        if not cell.walls[action_id]:
            actions.append((action_id, (cell.col + dx, cell.row + dy)))
    return actions


class QMazeTrainer:
    def __init__(self):
        self.grid = make_maze()
        self.q = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
        self.start = (0, 0)
        self.goal = (COLS - 1, ROWS - 1)
        self.state = self.start
        self.draw_state = [0.0, 0.0]
        self.episode = 1
        self.steps = 0
        self.total_steps = 0
        self.best_steps = None
        self.successes = 0
        self.epsilon = 0.95
        self.alpha = 0.45
        self.gamma = 0.92
        self.max_steps = COLS * ROWS * 4
        self.running = True
        self.speed = 12
        self.trail = deque(maxlen=90)
        self.episode_lengths = deque(maxlen=50)
        self.message = "The AI starts clueless. Watch the path get less ridiculous."
        self.message_timer = 180

    def reset_maze(self):
        self.__init__()

    def choose_action(self, state):
        valid = open_actions(self.grid, state)
        if random.random() < self.epsilon:
            return random.choice(valid)
        values = self.q[state]
        return max(valid, key=lambda item: values[item[0]])

    def step(self):
        if not self.running:
            return

        action_id, next_state = self.choose_action(self.state)
        reward = -0.04
        done = False

        if next_state == self.goal:
            reward = 40.0
            done = True

        old_value = self.q[self.state][action_id]
        future = max(self.q[next_state])
        self.q[self.state][action_id] = old_value + self.alpha * (reward + self.gamma * future - old_value)

        self.trail.append(self.state)
        self.state = next_state
        self.steps += 1
        self.total_steps += 1

        if done or self.steps >= self.max_steps:
            if done:
                self.successes += 1
                self.best_steps = self.steps if self.best_steps is None else min(self.best_steps, self.steps)
                self.message = random.choice([
                    "Goal reached. The AI looks slightly smug.",
                    "Success. Fewer panic turns next time.",
                    "The maze has been negotiated with.",
                    "Tiny brain gained one wrinkle.",
                ])
            else:
                self.message = "Episode timed out. The AI pretends this was research."
            self.message_timer = 150
            self.episode_lengths.append(self.steps)
            self.episode += 1
            self.steps = 0
            self.state = self.start
            self.trail.clear()
            self.epsilon = max(0.04, self.epsilon * 0.992)

    def update_animation(self):
        target_x, target_y = self.state
        self.draw_state[0] += (target_x - self.draw_state[0]) * 0.28
        self.draw_state[1] += (target_y - self.draw_state[1]) * 0.28
        if abs(self.draw_state[0] - target_x) < 0.01:
            self.draw_state[0] = float(target_x)
        if abs(self.draw_state[1] - target_y) < 0.01:
            self.draw_state[1] = float(target_y)
        if self.message_timer > 0:
            self.message_timer -= 1

    def best_path(self):
        state = self.start
        path = [state]
        seen = {state}
        for _ in range(COLS * ROWS):
            valid = open_actions(self.grid, state)
            action_id, next_state = max(valid, key=lambda item: self.q[state][item[0]])
            if next_state in seen:
                break
            path.append(next_state)
            seen.add(next_state)
            state = next_state
            if state == self.goal:
                break
        return path


def resize(event_w, event_h):
    global screen
    screen = pygame.display.set_mode((max(MIN_WIDTH, event_w), max(MIN_HEIGHT, event_h)), FLAGS)


def iso_layout():
    width, height = screen.get_size()
    panel_w = 330
    arena = pygame.Rect(20, 20, width - panel_w - 42, height - 40)
    tile_w = min(arena.width // (COLS + ROWS + 3) * 2, arena.height // (COLS + ROWS + 5) * 4)
    tile_w = clamp(tile_w, 28, 54)
    tile_h = tile_w // 2
    height_px = max(14, tile_h // 2)
    origin = (arena.centerx, arena.y + 58)
    return arena, pygame.Rect(width - panel_w, 0, panel_w, height), tile_w, tile_h, height_px, origin


def iso_point(col, row, tile_w, tile_h, origin):
    x = origin[0] + (col - row) * tile_w // 2
    y = origin[1] + (col + row) * tile_h // 2
    return x, y


def draw_poly(points, color):
    pygame.draw.polygon(screen, color, points)


def draw_tile(col, row, tile_w, tile_h, origin, color):
    x, y = iso_point(col, row, tile_w, tile_h, origin)
    points = [(x, y), (x + tile_w // 2, y + tile_h // 2), (x, y + tile_h), (x - tile_w // 2, y + tile_h // 2)]
    draw_poly(points, color)
    pygame.draw.polygon(screen, (51, 62, 82), points, 1)


def draw_wall_between(col, row, wall_id, tile_w, tile_h, height_px, origin):
    x, y = iso_point(col, row, tile_w, tile_h, origin)
    top = [(x, y), (x + tile_w // 2, y + tile_h // 2), (x, y + tile_h), (x - tile_w // 2, y + tile_h // 2)]
    raised = [(px, py - height_px) for px, py in top]

    if wall_id == 0:
        side = [top[0], top[1], raised[1], raised[0]]
    elif wall_id == 1:
        side = [top[1], top[2], raised[2], raised[1]]
    elif wall_id == 2:
        side = [top[2], top[3], raised[3], raised[2]]
    else:
        side = [top[3], top[0], raised[0], raised[3]]

    draw_poly(side, WALL_SIDE)
    pygame.draw.line(screen, WALL_TOP, side[2], side[3], 3)


def draw_agent(trainer, tile_w, tile_h, origin):
    col, row = trainer.draw_state
    x, y = iso_point(col, row, tile_w, tile_h, origin)
    bob = math.sin(pygame.time.get_ticks() / 110) * 3
    body = [
        (x, y - 28 + bob),
        (x + 14, y - 16 + bob),
        (x + 10, y + 2 + bob),
        (x - 10, y + 2 + bob),
        (x - 14, y - 16 + bob),
    ]
    draw_poly(body, AGENT)
    pygame.draw.polygon(screen, (12, 18, 28), body, 2)
    pygame.draw.rect(screen, TEXT, (x - 7, y - 16 + bob, 4, 4))
    pygame.draw.rect(screen, TEXT, (x + 4, y - 16 + bob, 4, 4))
    pygame.draw.rect(screen, ACCENT, (x - 10, y - 31 + bob, 20, 5))


def draw_arena(trainer):
    arena, _, tile_w, tile_h, height_px, origin = iso_layout()
    pygame.draw.rect(screen, SHADOW, arena.move(0, 8), border_radius=14)
    pygame.draw.rect(screen, (18, 23, 34), arena, border_radius=14)
    pygame.draw.rect(screen, PANEL_2, arena, 2, border_radius=14)

    best = set(trainer.best_path())
    trail = set(trainer.trail)
    for row in range(ROWS):
        for col in range(COLS):
            color = FLOOR_ALT if (col + row) % 2 else FLOOR
            if (col, row) in best:
                color = (80, 70, 50)
            if (col, row) in trail:
                color = SEARCH
            if (col, row) == trainer.goal:
                color = GOAL
            draw_tile(col, row, tile_w, tile_h, origin, color)

    for row in range(ROWS):
        for col in range(COLS):
            cell = trainer.grid[index(col, row)]
            for wall_id, has_wall in enumerate(cell.walls):
                if has_wall:
                    draw_wall_between(col, row, wall_id, tile_w, tile_h, height_px, origin)

    draw_agent(trainer, tile_w, tile_h, origin)


def draw_panel(trainer):
    _, panel, _, _, _, _ = iso_layout()
    pygame.draw.rect(screen, PANEL, panel)
    pygame.draw.line(screen, (54, 65, 86), (panel.x, 0), (panel.x, panel.height), 2)
    draw_text("AI Maze Trainer", (panel.x + 24, 26), TEXT, title_font)
    draw_text("Q-learning simulation", (panel.x + 26, 78), MUTED, small_font)

    y = 122
    stats = [
        ("Episode", str(trainer.episode)),
        ("Current steps", str(trainer.steps)),
        ("Total steps", str(trainer.total_steps)),
        ("Successes", str(trainer.successes)),
        ("Best solve", "--" if trainer.best_steps is None else str(trainer.best_steps)),
        ("Exploration", f"{trainer.epsilon:.2f}"),
        ("Speed", f"{trainer.speed}x"),
    ]
    for label, value in stats:
        draw_text(label, (panel.x + 26, y), MUTED, small_font)
        draw_text(value, (panel.x + 190, y), TEXT, small_font)
        y += 28

    avg = 0 if not trainer.episode_lengths else sum(trainer.episode_lengths) / len(trainer.episode_lengths)
    draw_text("Recent avg", (panel.x + 26, y), MUTED, small_font)
    draw_text("--" if avg == 0 else f"{avg:.1f}", (panel.x + 190, y), TEXT, small_font)
    y += 46

    if trainer.message_timer > 0:
        pygame.draw.rect(screen, PANEL_2, (panel.x + 22, y, panel.width - 44, 74), border_radius=8)
        draw_text(trainer.message[:32], (panel.x + 34, y + 18), PATH, small_font)
        draw_text(trainer.message[32:64], (panel.x + 34, y + 42), PATH, small_font)
    y += 106

    draw_text("Controls", (panel.x + 26, y), TEXT, font)
    y += 34
    for line in (
        "Space: pause / resume",
        "R: new maze + reset AI",
        "Up/Down: training speed",
        "Yellow floor: current best policy",
        "Purple floor: current episode trail",
    ):
        draw_text(line, (panel.x + 26, y), MUTED, small_font)
        y += 25

    bar = pygame.Rect(panel.x + 26, panel.height - 74, panel.width - 52, 12)
    pygame.draw.rect(screen, (43, 52, 70), bar, border_radius=6)
    value = 1.0 - trainer.epsilon
    pygame.draw.rect(screen, GOOD, (bar.x, bar.y, int(bar.width * value), bar.height), border_radius=6)
    draw_text("Learning confidence", (bar.x, bar.y - 24), MUTED, small_font)


def draw_backdrop():
    screen.fill(BG)
    width, height = screen.get_size()
    for x in range(0, width, 36):
        for y in range(0, height, 36):
            if (x // 36 + y // 36) % 2 == 0:
                pygame.draw.rect(screen, (24, 29, 42), (x + 15, y + 15, 4, 4))


trainer = QMazeTrainer()
running = True

while running:
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            resize(event.w, event.h)
        elif event.type == getattr(pygame, "WINDOWSIZECHANGED", -1):
            resize(event.x, event.y)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                trainer.running = not trainer.running
            elif event.key == pygame.K_r:
                trainer.reset_maze()
            elif event.key == pygame.K_UP:
                trainer.speed = min(120, trainer.speed + 4)
            elif event.key == pygame.K_DOWN:
                trainer.speed = max(1, trainer.speed - 4)

    for _ in range(trainer.speed):
        trainer.step()
    trainer.update_animation()

    draw_backdrop()
    draw_arena(trainer)
    draw_panel(trainer)
    pygame.display.flip()

pygame.quit()
sys.exit()
