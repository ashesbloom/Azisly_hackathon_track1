# Robot changes log

This file records every change to `robot.py`, why it was made, and what it did to the score.
It is for us, not the grader: only `robot.py` (renamed to our team id) is submitted.

## Where we ended up (read this first)

| | wall follower (start) | final robot |
|---|---|---|
| practice mazes | 282 / 400 | **376 / 400** (p02, p03 perfect) |
| hard: practice mazes with range 1, 10% noise, jitter | 150 / 400 | **206 / 400** |
| benchmark: solved | 174 / 190 | **190 / 190** |
| benchmark: wall hits | 151 | **53** |
| benchmark: total score (190 mazes) | 6027 | **6629 (+10%)** |
| slowest thinking on a 61x61 maze | -- | ~6 s of the 30 s allowed |

Honest reading: the big wins are **reliability** (the wall follower fails 16 of 190 mazes = 16 zeros; we fail none)
and **safety** (a third of the wall hits). On huge mazes both robots burn many ticks exploring, because the goal is
invisible until you stand on it. The wall follower's "avg extra ticks" looks lower (85 vs 92) only because that
average skips the mazes it failed.

What worked, biggest first: turn-aware routing (#3), noise voting (#2), skipping cells that can't be the goal plus
preferring deeper targets (#4, #5), turning toward open space (#6), speed (#11), the safety net (#12).
Tried and dropped, with the reasons: #7, #8, #10. Tuning plateau: #9.

```
python3.11 "for dev/viz.py"               # the viewer: pick a maze, Run, step through with ← →
python3.11 "for dev/viz.py" --text        # score table for all 4 practice mazes
python3.11 "for dev/viz.py" --text p01    # every tick of p01 with the robot's reason
python3.11 "for dev/viz.py" --hard        # the same mazes with worst-case sensors
python3.11 play.py                        # the kit's own viewer (works now too)
python3.11 selftest.py robot.py           # the check to run before uploading

```

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
python3.11 "for dev/viz.py" --bench         # 140 generated mazes -- the main number we optimise
python3.11 selftest.py robot.py             # submission plumbing check -- run before every upload
```

### Why a benchmark, and what's in it

4 practice mazes are too few to tune on: a change can win on them by luck and lose on the hidden set.
`--bench` generates 140 mazes in the practice mazes' style (odd grid, border walls, start at (1,1)), with sizes
9x9 to 31x31, some with loops, some with open chambers, sensor range 1-4, noise 0-10%, jitter on/off.

- **Farthest-goal set (100 mazes):** goal on the cell farthest from the start. **All 4 practice mazes are built this way**
  (checked: in each one the goal is the single farthest cell, and a dead end). The hidden mazes very likely are too.
- **Farthest-by-ticks set (50 mazes, added at #7):** goal on the cell farthest when turns are counted too. The practice
  mazes fit both "farthest in steps" and "farthest in ticks", so we test both.
- **Random-goal set (40 mazes):** goal on a random cell. A safety check, so we notice if a change only works when
  the goal is far away.
- **Avg extra ticks** (our ticks minus the shortest possible) is the number to push down. Big mazes cost so many exploring
  ticks that many land on the 10-point floor, which hides progress in the score column.
- The 6 worst mazes of each run are saved to `for dev/mazes/` (not committed) and show up in the GUI's maze list.

## Scoreboard

| # | change | practice /400 | hard /400 | bench far: solved, extra ticks, score | bench random: solved, extra ticks, score | bench wall hits |
|---|---|---|---|---|---|---|
| 0 | wall follower | 282 | 150 | 96/100, 85.2, 30.8 | 32/40, 86.9, 41.8 | 112 |
| 1 | explorer (nearest unvisited) | 304 | 173 | 98/100, 135.5, 26.5 | 39/40, 101.1, 44.5 | 178 |
| 2 | noise voting + re-checking uncertain cells | 298 | 167 (20/20 solved) | 98/100, 129.8, 26.1 | 40/40, 105.2, 43.5 | 37 |
| 3 | turn-aware routing | **370** | 194 (20/20) | **100/100, 102.0**, 26.9 | 39/40, 111.5, 42.4 | 31 |
| 4 | skip cells that can't be the goal (farthest-cell rule) | 370 | 187 (20/20) | 100/100, 95.6, 27.6 | 38/40, 98.3, 42.5 | 36 |
| 5 | prefer deeper targets (W = 0.25) | 370 | 197 (20/20) | 100/100, **89.7, 32.8** | 40/40, 112.4, 41.2 | 44 |
| 6 | on a tie, turn toward the more open side | **376** | **204** (20/20) | 100/100, 91.8, **34.0** | 40/40, 116.6, **43.6** | 45 |
| 7 | *tried, reverted:* drop the 3-step margin | 352 | 218 | 99/100, 96.2, 34.1 | 40/40, 116.5, 44.6 | 49 |
| 8 | *tried, reverted:* other ways to handle tied readings | -- | -- | see entry | -- | -- |
| 9 | *tuning sweep:* SLACK x W | -- | -- | all within 1% (plateau) | -- | -- |
| 10 | *tried, reverted:* "goal must be a dead end" rule | 352 | 204 | 99/100, 87.7 | 39/40, 105.1 | 62 |
| 11 | speed: 5x faster, identical decisions | 376 | 204 | unchanged | unchanged | unchanged |
| 12 | safety net: never crash | 376 | 204 | unchanged | unchanged | unchanged |
| 13 | code-review fixes (correct pocket bound, etc.) | 376 | 206 (20/20) | 100/100, 93.0, 33.9 | 40/40, 110.7, 43.6 | 53 |

From #7 on the benchmark also has the farthest-by-ticks set. For #6 it reads: 50/50 solved, 128.3 extra ticks, score 29.9.

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
  - p01 got worse (100 -> 80). At (3,7) the bottom corridor goes both ways. "Nearest unvisited" happened to pick east:
    a 4-cell dead end (x=4..7), then two turns and back = 10 wasted ticks. The goal was west. The wall follower
    wasn't smarter -- its right-hand rule just happened to turn the right way on this maze. With a hidden goal,
    every fork is a guess; what we can control is how cheaply a wrong guess gets undone.
  - **Noise breaks it.** Because the newest reading wins, one wrong reading ("1 open cell ahead" where there's a wall) makes it
    drive into a wall (seen at `--text` on p03 with range 1, tick 10). Another wrong reading can hide an open cell and strand it.
    3 of 20 hard runs never reached the goal = 0 points each. The wall follower is dumber but never stranded.
- **Verdict:** kept as the base. Higher total, but it is **not yet safe on noisy mazes**. That's the first thing to fix.
- **Later, on the 140-maze benchmark** (added after this entry): the explorer is *worse* than the wall follower on the
  farthest-goal set (135.5 vs 85.2 extra ticks). On big mazes "nearest unvisited cell" zig-zags: it leaves a branch half
  done, goes elsewhere, and walks back later. The wall follower is a depth-first search -- it finishes a branch before the next.

---

## #2 Noise voting, plus going back to re-check uncertain cells

- **What:**
  1. **Votes instead of "latest wins" (`_sense`, `_is_open`).** Every reading is a vote: "open" for the cells it saw
     through, "wall" for the cell it stopped at. A cell is open if open votes > wall votes, a wall if the opposite,
     and **unknown** if tied. Two things are certain and skip voting: a cell we stood on is open, and a cell we drove
     into is a wall (`memory["sure"]`).
  2. **Unknown cells are targets (`_next_to`, `_route`).** Before, the robot only went to cells it hadn't stood on.
     Now "next to an unknown cell" is also a target, because arriving there senses it.
  3. **If already next to an uncertain cell:** `wait` one tick for a fresh reading, since noise is re-rolled every tick.
     If the cell is behind us, turn to face it.
  4. **Safety net:** if everything is explored and there's still no goal, noise must have faked a wall. Go re-check
     the walls whose lead is smallest (wall votes minus open votes <= k), widening k until something is found.
- **Why:** with noise, one wrong reading used to decide a cell. It either drove us into a wall (-7 points) or hid an
  open corridor. Most cells get seen several times as we pass, so a majority vote almost always gets them right.
- **Two bugs found and fixed while building it** (both only happen with voting):
  - A tied cell was "unknown", and nothing ever sent the robot back to look. On `--hard` p02 it sat spinning in a
    dead end until the tick cap, because the only way east was a tied cell. That's why unknown cells became targets.
  - The first safety net counted any wall with even one stray "open" vote as doubtful *forever*. Two cells each
    pointed at the other as "the place to re-check", and it ping-ponged. Fixed with the small-lead rule, which
    re-checking settles, and by waiting in place when already next to the cell.
- **Where:** `_update_pose` (sure cells), `_is_open`, `_sense`, `_next_to`, `_route`, `decide`.
- **Result:**

| suite | before (#1) | after (#2) |
|---|---|---|
| practice | 304 | 298 |
| hard: solved / wall hits / score | 17/20, 70, 173 | **20/20, 4, 167** |
| bench far: solved / extra ticks / score | 98/100, 135.5, 26.5 | 98/100, 129.8, 26.1 |
| bench random: solved / extra ticks / score | 39/40, 101.1, 44.5 | 40/40, 105.2, 43.5 |
| bench wall hits | 178 | **37** |

- **What we learned:**
  - Scores barely moved, but the failure modes changed completely: wall hits dropped by 80% and every hard run now
    finishes. Being robust matters more than those few points, because the hidden mazes are noisier than the practice ones.
  - Practice dropped 6 points (p01 +2 ticks, p04 +1). These are tiny: `wait` ticks spent confirming a tied cell.
  - The 2 bench failures are no longer bugs:
    - far37 (29x27, range 1) is simply too slow: it visited 331 cells before the tick cap.
    - far68 explored 342 of 343 cells and was re-checking walls when time ran out.

    Both point at the real problem: **exploration order**.
  - On range-1 noisy mazes it spends ~55 ticks per maze on `wait`. Worth revisiting later.
- **Verdict:** kept.

---

## #3 Turn-aware routing: count turns as ticks when choosing where to go

- **What:** the search now plans over **(cell, heading)** instead of just cells. Each of forward, turn left and turn right
  costs one tick, exactly like the grader counts. So "nearest" now means "fewest ticks away", not "fewest cells away".
  The search returns the actions themselves, so `decide` just takes the first one. Forward is tried before turns,
  so among equally short routes it keeps going straight rather than turning early.
- **Why:** a cell 3 steps ahead costs 3 ticks. A cell 1 step behind costs 3 ticks too (turn, turn, forward). The old
  search called the one behind "nearest" and happily spun around for it. In a corridor this makes the robot finish
  what's ahead before doubling back, which is exactly the depth-first behaviour that made the wall follower good on big mazes.
- **Where:** `_route` (rewritten), `_cells_along` (for the viewer's plan line), `decide`.
- **Result:**

| suite | before (#2) | after (#3) |
|---|---|---|
| practice | 298 | **370** (p02 and p03 now match the shortest possible route: 100 each) |
| hard: solved / wall hits / score | 20/20, 4, 167 | 20/20, 8, **194** |
| bench far: solved / extra ticks / score | 98/100, 129.8, 26.1 | **100/100, 102.0**, 26.9 |
| bench random: solved / extra ticks / score | 40/40, 105.2, 43.5 | 39/40, 111.5, 42.4 |

- **What we learned:**
  - The biggest single gain so far, and it costs nothing: same information, better arithmetic.
  - The one failure (rand10033) is a goal 2 cells from the start, in a side pocket, while the explorer went the
    other way. When the goal is that close, the tick cap is tiny (6 x 14 + 300 = 384). Exploration order again.
  - Spotted: at the start (t000-t002 of rand10033) it turns left to look behind, then needs two more turns to face
    the open corridor on the right. Turning right first would have looked behind *and* faced the corridor.
- **Verdict:** kept.

---

## #4 Skip cells that provably can't be the goal

- **The observation:** in all 4 practice mazes the goal is the single cell **farthest from the start**, and a dead end.
  That's very unlikely to be chance, so the maze generator probably places goals that way.
- **What:** every tick, `_could_be_goal` works out which cells could still be the farthest one:
  1. `shortest_known`: distance from the start through cells we *know* are open. The real distance is this or shorter.
  2. `at_least`: distance from the start pretending every unknown cell is open. The real distance is this or longer.
  3. Some open cell is at least `beat = max(at_least)` away, so the goal is at least that far too.
     A cell whose `shortest_known` is less than `beat` can't be the goal. We skip it: the viewer draws it with a small x.
  4. A pocket of unknown cells walled in on every side can't hide anything farther than its entrance distance + its size.
     If that's less than `beat`, we don't go and look inside.
  5. **SLACK = 3:** the practice mazes can't tell whether "farthest" means steps or ticks-with-turns. On generated mazes
     those two definitions pick different cells 19% of the time, but never more than 3 steps apart. So we only skip
     cells that are more than 3 short.
  6. **Safety net:** if nothing is left that fits the rule (noise fooled us, or this maze doesn't follow it),
     go back to exploring everything. The rule can only reorder our exploration, never strand us.
- **Where:** `_bfs`, `_could_be_goal`, `_next_to(among=...)`, `decide`. Viewer: the "ruled out" legend item.
- **Result:** bench far extra ticks 102.0 -> 95.6. Random-goal set 39/40 -> 38/40: when the goal is near the start the
  rule sends us away from it first, and the tick cap is tight on short mazes. Practice unchanged at 370.
- **What we learned:** smaller gain than hoped. `beat` only grows once we've been deep into the maze, so early on
  almost nothing can be ruled out. What matters more is *which way we go first*. That's #5.
- **Verdict:** kept. It's the foundation for #5.

---

## #5 Prefer targets deeper in the maze

- **What:** instead of always going to the nearest possible-goal spot, pick the one with the lowest
  `ticks to get there - W x (its at_least distance from the start)`. So a spot 8 steps deeper is worth a walk of up to
  2 ticks longer (W = 0.25). `_route` now searches all reachable states when given a `value` function.
- **Why:** the goal is the farthest cell. At a fork, the branch reaching deeper is more likely to hold it, and a
  wrong branch costs twice (in and back out).
- **Choosing W** (swept on everything):

| W | practice | hard | bench far: extra ticks, score | bench random: solved, extra ticks |
|---|---|---|---|---|
| 0 (= #4) | 370 | 187 | 95.6, 27.6 | 38/40, 98.3 |
| **0.25** | 370 | **197** | 89.7, **32.8** | **40/40**, 112.4 |
| 0.5 | 370 | 197 | **88.7**, 32.8 | 40/40, 127.0 |
| 1 | 370 | 190 | 89.2, 34.3 | 40/40, 133.8 |
| 2 | 374 | 179 | 113.0, 30.8 (1 unsolved) | 39/40, 107.4 |

- **What we learned:** a little depth preference helps, and too much hurts: at W = 2 it charges off deep and leaves
  things behind that it has to walk back for. 0.25 and 0.5 are about the same on the farthest-goal set. 0.25 wastes
  less when the goal isn't far, which is our insurance if the hidden mazes don't follow the rule.
- **Verdict:** kept with W = 0.25.

---

## #6 When two turns are equally good, turn toward the more open side

- **What:** when the best plan starts with a turn and turning left or right would be equally good, turn toward the
  side whose distance sensor reads farther. Before, it always picked left.
- **Why:** seen on p04 (t000-t002). The robot starts facing a wall with an unknown cell behind it. Turning either
  way brings that cell into view, so both cost 1 tick. It picked left (a wall), then needed 2 more turns to face the
  open corridor on the right. Turning right first looks behind *and* ends up facing the way we'll go.
- **Where:** `_route(right_first=...)`, set in `decide` from `dist_right > dist_left`.
- **Result:** practice 370 -> 376 (p01 45 -> 43, p04 65 -> 64). Hard 197 -> 204. Bench scores 32.8 -> 34.0 and
  41.2 -> 43.6, though farthest-goal extra ticks moved 89.7 -> 91.8. That's within the benchmark's noise: a tiny change
  early in a run changes everything after it, sometimes for the better and sometimes worse.
- **Verdict:** kept. Free, and it helps where it's aimed.

---

## #7 (tried, reverted) Drop the 3-step safety margin from the farthest-cell rule

- **Idea:** SLACK = 3 keeps cells up to 3 steps short of the deepest known point as candidates, so some get visited
  for nothing. Instead of a fixed margin, rule a cell out only if it can't be the farthest under **both** definitions:
  steps, and ticks-with-turns (a second pair of searches over (cell, heading)).
- **To test it fairly** we added the farthest-by-ticks set to `--bench`. That tooling stays.
- **Result:**

| variant | practice | hard | bench far: extra ticks | bench ticks-far: extra ticks | unsolved |
|---|---|---|---|---|---|
| **current: steps + SLACK 3** | **376** | 204 | 91.8 | 128.3 | 0 |
| both definitions, no slack | 352 | 218 | 96.2 | 130.5 | 1 |
| steps only, no slack (unsafe) | 352 | -- | 89.9 | 129.6 | 2 |

- **What we learned:** the margin isn't just insurance, it also helps. Ruling cells out more aggressively made the
  robot skip cells next to its path that were cheap to grab right then, and later the fallback walked back for them.
  Practice dropped 24 points. The two-definition check also cost more thinking time (slowest tick 120 ms vs ~20).
- **Verdict:** reverted. `robot.py` is identical to #6.

---

## #8 (tried, reverted) Other ways to handle a tie between "open" and "wall" votes

- **Today:** a tied cell counts as unknown. If it's in view, the robot `wait`s one tick for a fresh reading.
  That's 2.8% of all ticks on the benchmark.
- **Tried:**
  - **A:** don't go out of our way to look at tied cells; leave them to the fallback.
  - **B:** break a tie with the most recent reading, so there are no ties at all.
  - **C:** like B, but never drive *into* a cell that is only "open" by a tie-break; wait there instead.
- **Result** ("bench total" = sum of all 190 benchmark scores):

| variant | hard | bench total | bench wall hits |
|---|---|---|---|
| **current** | 204 | 6639 | **54** |
| A | 100 | -- (far set 30.9 vs 34.0) | 65 |
| B | 220 | 6680 | 117 |
| C | 219 | 6594 | 65 |

- **What we learned:**
  - A is clearly bad: a tied cell is often the only way forward, and leaving it for later means a long walk back.
  - B and C are within 1% of the current version on the benchmark, which is noise. B doubles the wall hits: it gambles.
- **Verdict:** kept the current, simplest behaviour.

---

## #9 (tuning sweep) SLACK and DEPTH_WEIGHT together

Re-tuned both knobs after #6, since changes can shift the best setting. Bench total for each:

| SLACK \ W | 0.25 | 0.5 |
|---|---|---|
| 2 | 6657 (1 unsolved) | 6676 |
| **3** | **6639** | 6644 |
| 4 | 6681 | 6671 |
| 5 | 6641 | 6601 (1 unsolved) |

Everything lands within 1% with no pattern, so it's a plateau and moving the knobs gains nothing real. Practice (376)
and hard (204-209) barely move either. **Kept SLACK = 3, W = 0.25.** We don't pick the top number from a noisy table:
that just tunes to our benchmark's luck, not to the hidden mazes.

---

## #10 (tried, reverted) "The goal must be a dead end"

- **Idea:** all 4 practice goals are dead ends (one open neighbour), and in a perfect maze the farthest cell always is.
  So once a cell has 2+ known open neighbours, stop treating it as a goal candidate.
- **Result:** practice 376 -> 352, one extra unsolved maze in the farthest-goal set and one in the random set.
  Bench total +41 (noise level).
- **What we learned:** like #7, ruling cells out more aggressively backfires. A goal-shaped rule that holds in
  perfect mazes breaks in open rooms, where the farthest cell can be a room corner. The benchmark has rooms, and
  the hidden set is said to have "open chambers".
- **Verdict:** reverted.

---

## #11 Speed: the same decisions, 5x faster

- **Why this mattered:** a stress test on bigger mazes than the benchmark (61x61) showed the robot needing
  **31-36 seconds** of thinking for one maze. The final round allows **30 s per maze** (and 10 minutes in total), so
  a big hidden maze would have scored 0 no matter how well it was solved.
- **What (profiled first, then fixed the top items):**
  1. **The map is kept up to date cell by cell** (`_mark`) instead of being rebuilt from all votes every tick.
  2. **Targets are worked out once per tick** (`_watchers`). Before, the route search re-derived "is there
     something unknown next to this cell?" for every state it touched: 7.6 million calls on one maze.
  3. **The route search stops early.** Once no state further away can beat the best target found, it stops.
  4. **Nothing is recomputed unless the map changed.** A version counter goes up only when a cell's state flips or
     we stand on a new cell. When backtracking through explored corridors, nothing changes, so the "could be the
     goal" analysis is reused.
  5. The two distance searches in `_bfs` no longer call a function per cell.
- **How we proved nothing changed:** before touching anything we recorded a fingerprint: ticks, wall hits and
  solved for all 214 runs (190 benchmark + 4 practice + 20 hard). After each step, all 214 were identical.
- **Result:**

| maze | before | after |
|---|---|---|
| 61x61, range 4 | 31.1 s | **5.9 s** |
| 61x61, range 1, 10% noise | 36.1 s | **6.9 s** |
| typical benchmark tick | ~2 ms | ~1 ms |

- **Verdict:** kept.

---

## #12 Safety net: an error never crashes the robot

- **What:** `decide()` now runs the strategy (`_explore`) inside a try/except. If anything raises, it prints the error
  to **stderr** (allowed: the grader returns stderr to us) and finishes that maze with the kit's original right-hand
  wall follower (`_wall_follower`).
- **Why:** a crash ends the run and scores the maze 0. Our code is tested on 214 runs, but the hidden mazes can do
  things ours don't. The wall follower keeps no map, so it can't be broken by a bad map, and it solved 174 of our
  190 benchmark mazes on its own.
- **Tested:** injected a fake bug at tick 30. All 4 practice mazes were still solved (85 / 112 / 152 / 63 ticks), and the
  viewer shows "SAFETY NET" in the Why line from tick 30 on. Normal behaviour: all 214 fingerprint runs identical.
- **Verdict:** kept.

---

## Compliance check against the contract (done on the final `robot.py`)

| rule (CONTRACT.md / README.md) | status | how we checked |
|---|---|---|
| One file, Python 3.11+, standard library only | ok | imports are only `json`, `sys`, `collections.deque`. Runs on 3.11 **and** 3.9 |
| Don't edit the `DO NOT EDIT` block | ok | byte-for-byte diff against the kit's original: identical |
| Never print to stdout except the action | ok | our only `print` goes to `sys.stderr` (safety-net message) |
| `{"ready": true}` within 10 s, no heavy work at import | ok | ready after ~20 ms. Import only defines functions |
| Answer each tick within 0.5 s (final) | ok | slowest tick seen: ~40 ms, on a 61x61 maze with 6 runs in parallel |
| 30 s per maze, 10 min in total (final) | ok | 61x61 maze: ~6 s total. Benchmark mazes: ~1 s or less |
| Only the 4 legal actions | ok | every action comes from forward / turn_left / turn_right / wait. The viewer stops a run on anything else, and never did |
| Don't read other files, find hidden mazes, or touch the grader | ok | no file, network or process calls (grep-checked) |
| Decide from the sensor stream; no hard-coded moves for a specific maze | ok | every move comes from the map built from readings. No maze-specific code |
| `selftest.py` passes | ok | PASSED on 3.11 and 3.9 |
| Real plumbing matches the viewer | ok | `sim_lite.run` (subprocess, like `play.py`) gives the same ticks and hits on all 4 practice mazes |

**One judgement call to be aware of:** #4/#5 use a pattern from the practice mazes (the goal is the cell farthest from
the start). That's a strategy, not hard-coded moves. The robot still decides everything from its own sensor readings,
and if the pattern doesn't hold it falls back to exploring everything. On the random-goal benchmark set, where the
pattern is false on purpose, it still solves 40/40. If the hidden mazes don't follow the pattern, we lose some
efficiency, not correctness. The mock round will tell us which: compare the random-goal-like mazes' scores there.

---

## #13 Code-review fixes

A line-by-line review of `robot.py` (the only submitted file) after #12. It found:

1. **(Important) The "walled-in pocket" rule wasn't actually a proof.** In `_could_be_goal`, a pocket of unknown cells
   was dismissed if `entrance + size < beat`, using the pocket's *closest* entrance. But hidden walls can split a
   pocket, so its far half may only be reachable through a *farther* entrance. The goal could hide there and be ruled
   out wrongly. The robot wouldn't get stuck (the fallback explores everything), but it would waste a whole
   exploration pass first.
   **Fix:** use the *farthest* entrance. Whatever route reaches a cell inside, it enters the pocket for the last
   time from one of the entrances, so `farthest entrance + size` really is an upper bound. And if an open neighbour
   of the pocket isn't reachable yet, its distance is unknown, so the pocket stays a candidate.
2. **(Minor) The viewer showed some cells as "ruled out" that weren't.** An open cell seen but not yet reachable has no
   known distance, so it can't be ruled out. Display only: the route search can't reach such a cell anyway.
3. **(Minor) Worst-case thinking time.** When the map looks fully explored with no goal, the doubtful-wall search
   widened its net one step at a time, up to 50 searches in one tick. On a huge maze that could approach the
   0.5 s limit. **Fix:** double the net (1, 2, 4 ... 64): at most 7 searches.
4. **(Minor) Wrong reason text.** While re-checking a doubtful wall, the Why line said "tied votes". Now it says
   "a doubtful wall is in view".

Checked and fine: the protected block is byte-identical, the only `print` goes to stderr, every return is one of the
4 legal actions, nothing heavy at import, no crash paths found (every dictionary lookup that could miss is guarded,
and the safety net covers the rest).

- **Result:** 55 of the 214 fingerprint runs took a different path, costing 243 more ticks in total (+0.6%).
  No run became unsolved.

| suite | before (#12) | after (#13) |
|---|---|---|
| practice | 376 | 376 |
| hard | 204 | 206 |
| bench total (190 mazes) | 6639 | 6629 |
| bench far / ticks-far / random: extra ticks | 91.8 / 128.3 / 116.6 | 93.0 / 137.2 / 110.7 |
| 61x61 maze thinking time | 5.9 s | 6.0 s |

- **What we learned:** the wrong rule was sometimes "right by luck": it ruled out pockets that happened not to hold
  the goal. The correct rule costs 0.6% ticks on our benchmark, which is within noise. But on a hidden maze where the
  wrong rule dismisses the goal's own pocket, the robot would explore the entire rest of the maze first, costing far
  more than 0.6%.
- **Verdict:** kept, for correctness. The log's claim that ruled-out cells "provably can't be the goal" is now true
  (given a correct map).
