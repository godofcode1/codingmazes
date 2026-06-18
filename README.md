# Coding Mazes

Coding Mazes is a small Pygame project for experimenting with playable mazes, pathfinding, and maze-solving visualizations.

The main app is `maze.py`, a playable maze lab with solver visualizations such as BFS, DFS, Dijkstra, and A*.

## Download and Run

If you are on Windows and just want to try the app, use the packaged file in `dist/`:

- `dist/maze.exe`

Double-click the file to launch it. The executable was built with Pygame included, so Python does not need to be installed just to run it.

## Run from Source

If you want to run or edit the Python files directly, install Python 3.12 and Pygame:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install pygame
.\.venv312\Scripts\python.exe maze.py
```

## Build the Executable

The Windows executable was built with PyInstaller:

```powershell
.\.venv312\Scripts\python.exe -m pip install pyinstaller pygame
.\.venv312\Scripts\python.exe -m PyInstaller --onefile --windowed --clean --name maze maze.py
```

Python 3.12 is recommended for building because Pygame has reliable Windows wheels for it.

## Notes

This is a learning project, so the code favors being easy to explore over being packaged like a large production app. The `dist/` folder is included so people can try the maze app immediately.
