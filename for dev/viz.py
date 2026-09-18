"""
Dev viewer for the maze robot. NOT part of the submission -- only robot.py is uploaded.

    python3.11 "for dev/viz.py"               # GUI: step through a run, hover anything for help
    python3.11 "for dev/viz.py" --text        # score table for every practice maze
    python3.11 "for dev/viz.py" --text p02    # tick-by-tick log for one maze
    python3.11 "for dev/viz.py" --hard        # same mazes with worst-case sensors (range 1, noise, jitter)
    python3.11 "for dev/viz.py" team17.py --text # test a different robot file

Use python3.11: the macOS system python3 (Tk 8.5) freezes any window.

Runs decide() in-process against sim_lite's physics (the same code play.py uses), with the
FINAL round limits: 6 x shortest + 300 ticks and 500 ms per tick.

The robot may leave these optional keys in `memory` for the viewer (the grader ignores them):
    why      str                    one-line reason for this tick's action
    plan     list of (x, y)         cells it intends to walk through next
    known    {(x, y): bool}         its map: True = believes open, False = believes wall
    visited  set of (x, y)          cells it has stood on
Cells are in the robot's own frame: start = (0, 0), heading 0 = N, 1 = E, 2 = S, 3 = W, y grows down.
"""

import argparse
import importlib.util
import sys
import time
import traceback
from collections import deque
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))
import sim_lite as S  # noqa: E402

TICK_LIMIT_MS = 500  # final round; mock allows 750


# ----------------------------------------------------------------------------- simulation

def shortest(maze):
    """Fewest ticks to the goal if the map were known, counting turns (the grader's 'optimal')."""
    start = (maze.start, maze.start_heading)
    dist = {start: 0}
    queue = deque([start])
    while queue:
        (x, y), h = queue.popleft()
        if (x, y) == maze.goal:
            return dist[((x, y), h)]
        dx, dy = S.DELTA[h]
        nexts = [((x, y), S.turn(h, "left")), ((x, y), S.turn(h, "right"))]
        if maze.is_open(x + dx, y + dy):
            nexts.append(((x + dx, y + dy), h))
        for n in nexts:
            if n not in dist:
                dist[n] = dist[((x, y), h)] + 1
                queue.append(n)
    return None


def score(solved, ticks, best, hits):
    return max(10, 100 - 2 * (ticks - best) - 5 * hits) if solved else 0


def load_decide(path):
    spec = importlib.util.spec_from_file_location("robot_under_test", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.decide


def to_world(maze, cell):
    """Robot frame (start = 0,0 facing 'N') -> maze coordinates."""
    x, y = cell
    for _ in range(S.HEADINGS.index(maze.start_heading)):
        x, y = -y, x  # rotate 90 degrees clockwise (y points down)
    return maze.start[0] + x, maze.start[1] + y


def snapshot(maze, memory):
    """Copy the optional viewer keys out of memory, converted to maze coordinates."""
    out = {"why": str(memory.get("why", "")), "plan": [], "known": None, "visited": set(), "est": None}
    try:
        if "pos" in memory and "h" in memory:
            h = int(memory["h"])
            out["est"] = (tuple(memory["pos"]), h, to_world(maze, memory["pos"]),
                          S.HEADINGS[(S.HEADINGS.index(maze.start_heading) + h) % 4])
        out["plan"] = [to_world(maze, c) for c in memory.get("plan", [])]
        if "known" in memory:
            out["known"] = {to_world(maze, c): bool(v) for c, v in memory["known"].items()}
        out["visited"] = {to_world(maze, c) for c in memory.get("visited", ())}
    except (TypeError, ValueError):
        pass  # robot stored something odd -- just don't draw it
    return out


def simulate(robot_path, maze):
    """Mirror of sim_lite.run, but in-process so we can read memory every tick."""
    best = shortest(maze)
    cap = 6 * best + 300
    decide = load_decide(robot_path)
    memory = {}
    x, y = maze.start
    heading = maze.start_heading
    motion = {"rpm": (0, 0), "accel": (0.0, 0.0)}
    frames, hits, solved, problem, slowest = [], 0, False, None, 0.0
    tick = 0
    while True:
        packet = S._build_packet(maze, x, y, heading, tick, motion)
        frame = {"tick": tick, "x": x, "y": y, "heading": heading, "packet": packet,
                 "action": None, "collided": False, "ms": 0.0, "hits": hits}
        if (x, y) == maze.goal:
            solved = True
            frame.update(snapshot(maze, memory), why="reached the goal -- run ends here")
            frames.append(frame)
            break
        if tick >= cap:
            problem = f"tick cap: no goal after {cap} ticks (final limit = 6 x shortest + 300)"
            frame.update(snapshot(maze, memory), why=problem)
            frames.append(frame)
            break

        t0 = time.perf_counter()
        try:
            action = decide(packet, memory)
        except Exception:
            problem = "decide() crashed: " + traceback.format_exc().strip().splitlines()[-1]
            frame.update(snapshot(maze, memory), why=problem)
            frames.append(frame)
            break
        ms = (time.perf_counter() - t0) * 1000
        slowest = max(slowest, ms)
        if action not in S.ACTIONS:
            problem = f"illegal action {action!r} -- the real grader scores this maze 0"
            frame.update(snapshot(maze, memory), why=problem)
            frames.append(frame)
            break

        collided = False
        if action == "forward":
            dx, dy = S.DELTA[heading]
            if maze.is_open(x + dx, y + dy):
                x, y = x + dx, y + dy
                motion = {"rpm": (S.CRUISE_RPM, S.CRUISE_RPM), "accel": (1.0, 0.0)}
            else:
                collided = True
                hits += 1
                motion = {"rpm": (0, 0), "accel": (S.IMPACT_ACCEL, 0.0)}
        elif action in ("turn_left", "turn_right"):
            left = action == "turn_left"
            heading = S.turn(heading, "left" if left else "right")
            motion = {"rpm": (-S.TURN_RPM, S.TURN_RPM) if left else (S.TURN_RPM, -S.TURN_RPM),
                      "accel": (0.0, -1.0 if left else 1.0)}
        else:
            motion = {"rpm": (0, 0), "accel": (0.0, 0.0)}

        frame.update(snapshot(maze, memory), action=action, collided=collided, ms=ms, hits=hits)
        frames.append(frame)
        tick += 1

    return {"maze": maze, "solved": solved, "ticks": tick, "best": best, "hits": hits,
            "score": score(solved, tick, best, hits), "slowest": slowest,
            "problem": problem, "frames": frames}


def fmt_ms(ms):
    return f"{ms * 1000:.0f} microseconds" if ms < 1 else f"{ms:.1f} ms"


def maze_files():
    return sorted((KIT / "mazes").glob("*.txt"))


def resolve_maze(name):
    p = Path(name)
    return p if p.is_file() else KIT / "mazes" / (name if name.endswith(".txt") else name + ".txt")


# ----------------------------------------------------------------------------- text mode

def text_line(f):
    p = f["packet"]
    hit = "  -> HIT WALL" if f["collided"] else ""
    return (f"t{f['tick']:03d} ({f['x']},{f['y']}){f['heading']} "
            f"F{p['dist_front']} L{p['dist_left']} R{p['dist_right']} "
            f"{(f['action'] or '-'):<10}| {f['why']}{hit}")


def hard_mode(robot_path, seeds=5):
    """Practice mazes re-run with the hidden set's worst sensors: range 1, 10% noise, jitter, several noise seeds."""
    import dataclasses
    print(f"{'maze':<6}{'solved':>8}{'avg ticks':>11}{'shortest':>10}{'wall hits':>11}{'avg score':>11}")
    total = 0
    for p in maze_files():
        m = S.load_maze(p)
        runs = [simulate(robot_path, dataclasses.replace(m, sensor_range=1, noise=0.10, encoder_jitter=True,
                                                         seed=m.seed + k)) for k in range(seeds)]
        avg = sum(r["score"] for r in runs) / seeds
        total += avg
        print(f"{m.name:<6}{sum(r['solved'] for r in runs):>6}/{seeds}{sum(r['ticks'] for r in runs) / seeds:>11.0f}"
              f"{runs[0]['best']:>10}{sum(r['hits'] for r in runs):>11}{avg:>11.0f}")
    print(f"{'TOTAL':<46}{total:>11.0f} / {100 * len(maze_files())}")


def text_mode(robot_path, which):
    if which != "ALL":
        r = simulate(robot_path, S.load_maze(resolve_maze(which)))
        for f in r["frames"]:
            print(text_line(f))
        print()
        rows = [r]
    else:
        rows = [simulate(robot_path, S.load_maze(p)) for p in maze_files()]
    print(f"{'maze':<6}{'solved':<8}{'ticks':>6}{'shortest':>10}{'wall hits':>11}{'score':>7}{'slowest ms':>12}")
    for r in rows:
        m = r["maze"]
        print(f"{m.name:<6}{'yes' if r['solved'] else 'NO':<8}{r['ticks']:>6}{r['best']:>10}"
              f"{r['hits']:>11}{r['score']:>7}{r['slowest']:>12.3f}"
              + (f"   <- {r['problem']}" if r["problem"] else ""))
    print(f"{'TOTAL':<41}{sum(r['score'] for r in rows):>7} / {100 * len(rows)}")


# ----------------------------------------------------------------------------- GUI

TIPS = {
    "maze": "Practice maze to run. Files live in mazes/. The robot never sees these files -- only sensor readings.",
    "run": "Run your robot on this maze from the start, in-process, with the final-round limits.",
    "result": "SOLVED = reached the goal. Otherwise why it stopped: tick cap, crash, or illegal action.",
    "ticks": "How many actions your robot took. One action = one tick; turns cost a tick just like moves.",
    "best": "Shortest possible: the fewest ticks to the goal if you already knew the whole maze, "
            "counting turns. The grader calls this 'optimal'. The viewer can compute it because it "
            "reads the maze file; your robot cannot.",
    "score": "Score = 100 - 2 x (your ticks - shortest possible) - 5 x wall hits, minimum 10. "
             "Not solved = 0. Same formula as the grader.",
    "hits": "Times the robot drove into a wall. Each costs 5 points plus the wasted tick (7 in total).",
    "slowest": f"Slowest single decide() call. The final round allows {TICK_LIMIT_MS} ms per tick "
               "(mock 750 ms); going over scores the maze 0.",
    "setup": "This maze's sensor settings. Range = how far the distance sensors can see (a reading "
             "equal to the range means 'at least that far'). Noise = chance a reading is off by 1. "
             "Jitter = wheel speeds wobble by about 5.",
    "tick": "Which tick of the run you are looking at, out of the total. Drag the slider or use the arrow keys.",
    "pos": "The robot's TRUE cell (x across, y down from the top-left) and compass heading. Only the "
           "viewer knows this, because it reads the maze file like the referee does. The robot is never told.",
    "est": "The robot's OWN estimate, from memory['pos'] and memory['h']. It has no GPS, so it invents its "
           "own coordinates: wherever it starts is (0, 0), and whichever way it first faces it calls 'N' "
           "(heading 0). Each turn adds or subtracts 90 degrees; each forward whose wheels read about +120 "
           "moves it one cell. The line below converts that into maze terms so you can check it against the truth.",
    "action": "What decide() returned on this tick. The maze shows the robot BEFORE this action.",
    "why": "The robot's own reason for this action, from memory['why'].",
    "sensors": "Distance readings the robot received this tick: open cells before a wall to the "
               "front / left / right. May be off by 1 on noisy mazes.",
    "wheels": "Wheel speeds caused by the PREVIOUS action: +120/+120 = moved one cell, "
              "-60/+60 = turned left, +60/-60 = turned right, 0/0 = waited or hit a wall.",
    "hits_now": "Wall hits so far, up to this tick. 0 is the goal: each hit costs 7 points. Turns red on the "
                "tick a hit happens. The practice mazes rarely cause hits; run --hard to see them.",
    "ms": f"How long decide() took on this tick. Limit {TICK_LIMIT_MS} ms.",
}

LEGEND = [
    ("#3D3D3D", "wall", "A wall cell the robot has sensed (or any wall, if the robot shares no map)."),
    ("#F5FFF0", "open", "An open cell the robot has sensed (or any open cell, if the robot shares no map)."),
    ("#C4C4C4", "unsensed wall", "A wall the robot has not sensed yet. Only shown when the robot shares "
                                  "its map in memory['known']."),
    ("#e9ebee", "unsensed open", "An open cell the robot has not sensed yet. Only shown when the robot "
                                  "shares its map in memory['known']."),
    ("#f08c00", "wrong belief", "The robot's map disagrees with the truth here, e.g. a noisy reading "
                                 "made it think a wall is open. Driving on a wrong belief causes wall hits."),
    ("#7a8ca3", "visited", "Cells the robot has stood on (memory['visited'])."),
    ("#2f6fdb", "plan", "The route the robot intends to take next (memory['plan']); the ring marks its target."),
    ("#2fa84f", "start", "Where the robot started."),
    ("#d6336c", "goal", "The goal. The robot doesn't know where it is until it steps on it."),
]
COL = {name: color for color, name, _ in LEGEND}
GRID = "#414141"
HIT = "#e03131"


class Tip:
    """Hover tooltip for any widget."""

    def __init__(self, widget, text):
        self.widget, self.text, self.top = widget, text, None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")

    def show(self, _event):
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.top = tk.Toplevel(self.widget)
        self.top.wm_overrideredirect(True)
        self.top.wm_geometry(f"+{x}+{y}")
        tk.Label(self.top, text=self.text, justify="left", wraplength=340, bg="#fffbe6",
                 fg="#222", relief="solid", bd=1, padx=8, pady=5).pack()

    def hide(self, _event):
        if self.top:
            self.top.destroy()
            self.top = None


class Viewer:
    SIDE = 280

    def __init__(self, root, robot_path):
        self.root, self.robot_path = root, robot_path
        self.run_result, self.frames, self.i, self.playing = None, [], 0, False
        root.title(f"Maze viewer -- {robot_path.name}")

        top = tk.Frame(root, padx=8, pady=6)
        top.pack(fill="x")
        self.maze_var = tk.StringVar(value=maze_files()[0].name)
        box = ttk.Combobox(top, textvariable=self.maze_var, state="readonly", width=10,
                           values=[p.name for p in maze_files()])
        box.pack(side="left")
        Tip(box, TIPS["maze"])
        run = tk.Button(top, text="Run", command=self.run)
        run.pack(side="left", padx=6)
        Tip(run, TIPS["run"])
        self.result = {}
        self.fg = tk.Label(root).cget("fg")  # "systemTextColor" on macOS: follows light/dark mode
        for key in ("result", "ticks", "best", "score", "hits", "slowest"):
            lbl = tk.Label(top, text="", padx=6)
            lbl.pack(side="left")
            Tip(lbl, TIPS[key])
            self.result[key] = lbl

        mid = tk.Frame(root)
        mid.pack(fill="both", expand=True)
        left = tk.Frame(mid, padx=8)
        left.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(left, width=560, height=560, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw())
        legend = tk.Frame(left, pady=4)
        legend.pack(fill="x")
        for color, name, tip in LEGEND:
            item = tk.Frame(legend)
            item.pack(side="left", padx=3)
            tk.Label(item, bg=color, width=2, relief="solid", bd=1).pack(side="left")
            tk.Label(item, text=name, font=("TkDefaultFont", 10)).pack(side="left")
            for w in (item, *item.winfo_children()):
                Tip(w, tip)

        side = tk.Frame(mid, width=self.SIDE, padx=10)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        self.side = {}
        for key, title in (("setup", "Maze setup"), ("tick", "Tick"), ("pos", "True position (referee's view)"),
                           ("est", "Robot thinks it is at"),
                           ("action", "Action"), ("why", "Why"), ("sensors", "Sensors"),
                           ("wheels", "Wheels (from previous action)"), ("hits_now", "Wall hits so far"),
                           ("ms", "decide() time")):
            head = tk.Label(side, text=title, font=("TkDefaultFont", 10, "bold"), anchor="w")
            head.pack(fill="x", pady=(8, 0))
            val = tk.Label(side, text="", anchor="w", justify="left", wraplength=self.SIDE - 20)
            val.pack(fill="x")
            Tip(head, TIPS[key])
            Tip(val, TIPS[key])
            self.side[key] = val

        bottom = tk.Frame(root, padx=8, pady=6)
        bottom.pack(fill="x")
        for text, cmd, tip in (("|<", lambda: self.go(0), "First tick (Home)"),
                               ("<", lambda: self.go(self.i - 1), "Previous tick (Left arrow)"),
                               ("Play", self.toggle, "Play / pause (Space)"),
                               (">", lambda: self.go(self.i + 1), "Next tick (Right arrow)"),
                               (">|", lambda: self.go(len(self.frames) - 1), "Last tick (End)")):
            b = tk.Button(bottom, text=text, width=4, command=cmd)
            b.pack(side="left")
            Tip(b, tip)
            if text == "Play":
                self.play_btn = b
        self.slider = tk.Scale(bottom, from_=0, to=0, orient="horizontal", showvalue=False,
                               command=lambda v: self.go(int(float(v))))
        self.slider.pack(side="left", fill="x", expand=True, padx=8)
        Tip(self.slider, TIPS["tick"])
        speed_lbl = tk.Label(bottom, text="speed")
        speed_lbl.pack(side="left")
        self.speed = tk.Scale(bottom, from_=1, to=30, orient="horizontal", showvalue=False, length=90)
        self.speed.set(8)
        self.speed.pack(side="left")
        Tip(speed_lbl, "Playback speed in ticks per second.")
        Tip(self.speed, "Playback speed in ticks per second.")

        root.bind("<Left>", lambda e: self.go(self.i - 1))
        root.bind("<Right>", lambda e: self.go(self.i + 1))
        root.bind("<Home>", lambda e: self.go(0))
        root.bind("<End>", lambda e: self.go(len(self.frames) - 1))
        root.bind("<space>", lambda e: self.toggle())
        box.bind("<<ComboboxSelected>>", lambda e: self.run())
        self.run()

    # -- actions

    def run(self):
        self.playing = False
        self.play_btn.config(text="Play")
        r = simulate(self.robot_path, S.load_maze(KIT / "mazes" / self.maze_var.get()))
        self.run_result, self.frames = r, r["frames"]
        m = r["maze"]
        ok = r["solved"]
        self.result["result"].config(text="SOLVED" if ok else "NOT SOLVED: " + (r["problem"] or "").split(":")[0] + " (see Why)",
                                     fg="#2b8a3e" if ok else HIT)
        self.result["ticks"].config(text=f"Your ticks: {r['ticks']}")
        self.result["best"].config(text=f"Shortest possible: {r['best']}")
        self.result["score"].config(text=f"Score: {r['score']} / 100")
        self.result["hits"].config(text=f"Wall hits: {r['hits']}")
        self.result["slowest"].config(text=f"Slowest tick: {fmt_ms(r['slowest'])}",
                                      fg=HIT if r["slowest"] > TICK_LIMIT_MS else self.fg)
        self.side["setup"].config(text=f"range {m.sensor_range} | noise {m.noise:.0%} | "
                                       f"jitter {'on' if m.encoder_jitter else 'off'}")
        self.slider.config(to=len(self.frames) - 1)
        self.go(0)

    def go(self, i):
        if not self.frames:
            return
        self.i = max(0, min(i, len(self.frames) - 1))
        if int(self.slider.get()) != self.i:
            self.slider.set(self.i)
        self.draw()

    def toggle(self):
        self.playing = not self.playing
        self.play_btn.config(text="Pause" if self.playing else "Play")
        if self.playing:
            if self.i >= len(self.frames) - 1:
                self.go(0)
            self.tick_playback()

    def tick_playback(self):
        if not self.playing:
            return
        if self.i >= len(self.frames) - 1:
            self.toggle()
            return
        self.go(self.i + 1)
        self.root.after(int(1000 / self.speed.get()), self.tick_playback)

    # -- drawing

    def draw(self):
        if not self.frames:
            return
        f, m, c = self.frames[self.i], self.run_result["maze"], self.canvas
        c.delete("all")
        s = max(6, min(c.winfo_width() // m.width, c.winfo_height() // m.height, 48))

        def center(cell):
            return cell[0] * s + s / 2, cell[1] * s + s / 2

        known = f["known"]
        for y, row in enumerate(m.rows):
            for x, ch in enumerate(row):
                wall = ch == S.WALL
                sensed = known is None or (x, y) in known
                fill = COL["wall" if sensed else "unsensed wall"] if wall else \
                    COL["open" if sensed else "unsensed open"]
                c.create_rectangle(x * s, y * s, x * s + s, y * s + s, fill=fill, outline=GRID)
                if known is not None and (x, y) in known and known[(x, y)] == wall:
                    c.create_rectangle(x * s + 2, y * s + 2, x * s + s - 2, y * s + s - 2,
                                       outline=COL["wrong belief"], width=3)

        for cell in f["visited"]:
            cx, cy = center(cell)
            c.create_oval(cx - s * .12, cy - s * .12, cx + s * .12, cy + s * .12,
                          fill=COL["visited"], outline="")
        sx, sy = center(m.start)
        c.create_rectangle(sx - s * .3, sy - s * .3, sx + s * .3, sy + s * .3, outline=COL["start"], width=2)
        gx, gy = center(m.goal)
        c.create_oval(gx - s * .38, gy - s * .38, gx + s * .38, gy + s * .38, outline=COL["goal"], width=3)
        if f["plan"]:
            pts = [center((f["x"], f["y"]))] + [center(p) for p in f["plan"]]
            c.create_line(*[v for p in pts for v in p], fill=COL["plan"], width=2, dash=(4, 3))
            tx, ty = pts[-1]
            c.create_oval(tx - s * .25, ty - s * .25, tx + s * .25, ty + s * .25, outline=COL["plan"], width=2)

        cx, cy = center((f["x"], f["y"]))
        dx, dy = S.DELTA[f["heading"]]
        r = s * .38
        c.create_polygon(cx + dx * r, cy + dy * r,
                         cx - dx * r * .7 - dy * r * .7, cy - dy * r * .7 + dx * r * .7,
                         cx - dx * r * .7 + dy * r * .7, cy - dy * r * .7 - dx * r * .7,
                         fill=HIT if f["collided"] else COL["plan"], outline="")

        p = f["packet"]
        self.side["tick"].config(text=f"{f['tick']}  ({self.i + 1} of {len(self.frames)} frames)")
        self.side["pos"].config(text=f"({f['x']}, {f['y']}) facing {f['heading']}")
        if f["action"] is None:
            self.side["est"].config(text="(run over -- the robot never gets another tick, so it never "
                                         "updates for its last move)", fg=self.fg)
        elif f["est"]:
            (ex, ey), eh, world, wh = f["est"]
            ok = world == (f["x"], f["y"]) and wh == f["heading"]
            self.side["est"].config(
                text=f"({ex}, {ey}) of its own grid, facing {['its start direction', '90 deg right of start', 'back toward start direction', '90 deg left of start'][eh % 4]}\n"
                     f"= maze ({world[0]}, {world[1]}) facing {wh}  {'-- matches the truth' if ok else '-- WRONG, the robot is lost'}",
                fg=self.fg if ok else HIT)
        else:
            self.side["est"].config(text="(robot doesn't share memory['pos'] / memory['h'])", fg=self.fg)
        self.side["action"].config(text=(f["action"] or "none (run over)") +
                                   ("   -> HIT WALL" if f["collided"] else ""),
                                   fg=HIT if f["collided"] else self.fg)
        self.side["why"].config(text=f["why"] or "(robot gave no reason)")
        self.side["sensors"].config(text=f"front {p['dist_front']}   left {p['dist_left']}   "
                                         f"right {p['dist_right']}")
        self.side["wheels"].config(text=f"left {p['rpm_left']:+d}   right {p['rpm_right']:+d}")
        self.side["hits_now"].config(text=str(f["hits"]))
        self.side["ms"].config(text=fmt_ms(f["ms"]), fg=HIT if f["ms"] > TICK_LIMIT_MS else self.fg)


def main():
    ap = argparse.ArgumentParser(description="Dev viewer for the maze robot (not submitted).")
    ap.add_argument("robot", nargs="?", default=str(KIT / "robot.py"), help="robot file (default robot.py)")
    ap.add_argument("--text", nargs="?", const="ALL", metavar="MAZE",
                    help="no GUI: score table for all mazes, or a tick-by-tick log for one maze")
    ap.add_argument("--hard", action="store_true",
                    help="no GUI: practice mazes with range-1 sensors, 10%% noise and jitter, 5 noise seeds each")
    args = ap.parse_args()
    robot_path = Path(args.robot).resolve()
    if args.hard:
        hard_mode(robot_path)
        return
    if args.text:
        text_mode(robot_path, args.text)
        return
    global tk, ttk
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    Viewer(root, robot_path)
    root.mainloop()


if __name__ == "__main__":
    main()
