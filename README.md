# Coding Mazes

Coding Mazes is a small set of Pygame maze projects for experimenting with pathfinding, maze generation, and simple AI behavior.

There are two apps in this repository:

- `maze.py`: a playable maze lab with solver visualizations such as BFS, DFS, Dijkstra, and A*.
- `ai_maze_3d.py`: an AI maze trainer with a 3D-style view and Q-learning behavior.

## Download and Run

If you are on Windows and just want to play with the apps, use the packaged files in `dist/`:

- `dist/maze.exe`
- `dist/ai_maze_3d.exe`

Double-click either file to launch it. The executables were built with Pygame included, so Python does not need to be installed just to run them.

## Run from Source

If you want to run or edit the Python files directly, install Python 3.12 and Pygame:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install pygame
.\.venv312\Scripts\python.exe maze.py
```

To run the AI maze trainer:

```powershell
.\.venv312\Scripts\python.exe ai_maze_3d.py
```

## Build the Executables

The Windows executables were built with PyInstaller:

```powershell
.\.venv312\Scripts\python.exe -m pip install pyinstaller pygame
.\.venv312\Scripts\python.exe -m PyInstaller --onefile --windowed --clean --name maze maze.py
.\.venv312\Scripts\python.exe -m PyInstaller --onefile --windowed --clean --name ai_maze_3d ai_maze_3d.py
```

Python 3.12 is recommended for building because Pygame has reliable Windows wheels for it.

## Notes

This is a learning project, so the code favors being easy to explore over being packaged like a large production app. The `dist/` folder is included so people can try the maze apps immediately.
