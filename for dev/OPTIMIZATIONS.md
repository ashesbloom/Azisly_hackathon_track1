# Robot changes log

This file records every change to `robot.py`, why it was made, and what it did to the score.
It is for us, not the grader: only `robot.py` (renamed to our team id) is submitted.

## The rules that matter

- **Score per maze:** `max(10, 100 - 2 x (our ticks - shortest possible) - 5 x wall hits)`. An unsolved maze scores 0.
  - One wasted tick = -2 points. One wall hit = -7 (5 points plus the wasted tick).
  - Being 45+ ticks over the shortest route drops the maze to the 10-point floor.
- **Shortest possible** ("optimal" in the contract) is the fewest ticks with the map already known, counting turns.
  Our robot never knows the map, so some exploration waste is unavoidable. The goal is to waste as little as possible.
- **Final-round limits:** 6 x shortest + 300 ticks, 500 ms per tick, 30 s per maze.
- **The goal is invisible:** the robot learns where it is only by standing on it, and the run ends right there.
- **Hard hidden mazes:** sensor range 1, readings off by 1 (noise), wheel speeds off by about 5 (jitter), open rooms.

## How to measure

```
python3.11 "for dev/viz.py" --text          # score table, all practice mazes
python3.11 "for dev/viz.py" --text p02      # tick-by-tick log with the robot's reasons
python3.11 "for dev/viz.py"                 # GUI: step through, hover anything for an explanation
python3.11 selftest.py robot.py             # submission plumbing check -- run before every upload
```

Use `python3.11`. The macOS system `python3` (3.9, Tk 8.5) freezes any window, including the kit's `play.py`.
The grader runs 3.11+ anyway.

---

## #0 Baseline: right-hand wall follower (the kit's starter code)

- **What:** unchanged starter logic. We only added `memory["why"]` on each branch so the viewer can show the reason.
- **Why it's weak:** it has no memory. It walks the same long way round, wastes ticks in loops (p02), and can circle forever in open rooms.
  It also trusts every sensor reading, so noise can cause wall hits.
- **Where:** `decide()` in `robot.py`.
- **Result:**

| maze | ticks | shortest | wall hits | score |
|---|---|---|---|---|
| p01 | 33 | 33 | 0 | 100 |
| p02 | 112 | 66 | 0 | 10 |
| p03 | 94 | 82 | 0 | 76 |
| p04 | 64 | 62 | 0 | 96 |
| **total** | | | | **282 / 400** |

- **Verdict:** this is the number to beat. Note that p01 and p04 are already (nearly) optimal *by luck*: the right-hand wall happens
  to lead straight to the goal there. A smarter explorer can lose points on those mazes, so always compare the whole table.

---

## #1 "Just working" explorer: remember the maze, go to the nearest unvisited cell

- **What:** replaced the wall follower with a robot that keeps a map.
  1. **Position (`_update_pose`)**: we know what we commanded, so we track `(x, y, heading)` ourselves from start = (0,0) facing "N".
     After a `forward`, if both wheels read above 60 we moved. Otherwise we hit a wall, so we stay put and mark that cell as a wall.
     Why 60: moving wheels read 120 +-5, a stalled wheel reads exactly 0, so 60 can't be confused even with jitter.
  2. **Map (`_sense`)**: each reading `d` marks the `d` cells in that direction open, and the cell after them a wall,
     unless `d` equals the sensor range ("at least d" -- we can't tell). We aren't told the range, so we use the largest
     reading seen so far, which can never be too big. A cell we've stood on is never marked a wall.
     The newest reading of a cell overwrites the old one.
  3. **Decision (`_route`)**: breadth-first search through cells we believe are open, to the nearest cell we haven't stood on.
     Any of them could be the goal, and the only way to find out is to stand on it. Then turn toward the first step or drive.
     If nothing is reachable, turn left to sense the cell behind us.
- **Why it should help:** no more walking the same corridors or circling loops (p02), and it only drives into cells its map says are open.
- **Where:** `_update_pose`, `_sense`, `_route`, `decide` in `robot.py`.
- **Result, practice mazes** (`--text`):

| maze | ticks before -> after | shortest | wall hits | score before -> after |
|---|---|---|---|---|
| p01 | 33 -> 43 | 33 | 0 | 100 -> 80 |
| p02 | 112 -> 88 | 66 | 0 | 10 -> 56 |
| p03 | 94 -> 96 | 82 | 0 | 76 -> 72 |
| p04 | 64 -> 64 | 62 | 0 | 96 -> 96 |
| **total** | | | | **282 -> 304** |

- **Result, worst-case sensors** (`--hard`: range 1, 10% noise, jitter, 5 noise seeds per maze, average score):

| maze | solved before -> after | wall hits before -> after | avg score before -> after |
|---|---|---|---|
| p01 | 5/5 -> 5/5 | 0 -> 0 | 56 -> 57 |
| p02 | 5/5 -> 4/5 | 6 -> 18 | 10 -> 15 |
| p03 | 5/5 -> 3/5 | 8 -> 50 | 37 -> 22 |
| p04 | 5/5 -> 5/5 | 5 -> 2 | 47 -> 80 |
| **total** | **20/20 -> 17/20** | **19 -> 70** | **150 -> 173** |

- **What we learned:**
  - p01 got worse (100 -> 80). The explorer goes to whatever unvisited cell is *nearest*, which sent it into a side corridor
    the wall follower happened to skip. With a hidden goal, "nearest" isn't always best. It also turns more,
    because its search ignores that turns cost ticks.
  - **Noise breaks it.** Because the newest reading wins, one wrong reading ("1 open cell ahead" where there's a wall) makes it
    drive into a wall (seen at `--text` on p03 with range 1, tick 10). Another wrong reading can hide an open cell and strand it.
    3 of 20 hard runs never reached the goal = 0 points each. The wall follower is dumber but never stranded.
- **Verdict:** kept as the base. Higher total, but it is **not yet safe on noisy mazes**. That's the first thing to fix.
