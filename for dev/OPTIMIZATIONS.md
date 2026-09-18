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
