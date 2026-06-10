# 🧩 Maze Generator (Python)

A visual maze generator built with Python using a **recursive backtracking algorithm**. The program creates a perfect maze step-by-step and displays the generation process in real time.

---

## ✨ Features

* Real-time animated maze generation
* Recursive Backtracking algorithm
* Perfect maze (no loops, always solvable)
* Easy-to-modify grid size
* Clean visual rendering

---

## 📦 Requirements

### Option 1 — Pygame version (recommended for supported Python versions)

```bash
pip install pygame
```

If pygame fails to install:

```bash
pip install pygame-ce
```

Then change in code:

```python
import pygame_ce as pygame
```

---

## 🚀 How to Run

1. Clone or download the project
2. Open terminal in the project folder
3. Run:

```bash
python maze.py
```

---

## ⚠️ Common Issues

### ❌ pygame build error

If you see:

```
Failed to build pygame wheel
```

Try:

```bash
pip install --upgrade pip setuptools wheel
pip install pygame --only-binary :all:
```

Or use:

```bash
pip install pygame-ce
```

---

### ❌ Python version issues

Pygame may not support the latest Python versions yet.

Recommended:

* Python 3.10 – 3.12

Check version:

```bash
python --version
```

---

## 🧠 Algorithm Explanation

The maze is generated using **Recursive Backtracking**:

1. Start from a random cell
2. Mark it as visited
3. Pick a random unvisited neighbor
4. Remove the wall between them
5. Move to that cell
6. If stuck, backtrack using a stack
7. Repeat until all cells are visited

This guarantees a **perfect maze** with one unique path between any two points.

---

## 🎮 Future Ideas

* Maze solver (BFS / DFS / A*)
* Speed controls for generation
* Multiple algorithms comparison
* Start/End visual pathfinding
* Color animations

---

## 👨‍💻 Author

Made with Python for learning algorithms, game dev, and visualization practice.
