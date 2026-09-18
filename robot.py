"""
Azisly Hackathon -- Round 2 submission template.

Rename this file to your team id (e.g. team17.py) and submit it. One file, Python 3,
standard library only.

You edit ONE function: decide(). Everything below the DO NOT EDIT line handles talking
to the grader for you -- you never have to think about processes or JSON.

Read CONTRACT.md first. It is short and it is the whole ruleset.
"""

import json
import sys
from collections import deque

# Headings in the robot's own frame: 0 = N, 1 = E, 2 = S, 3 = W, y grows down.
# The robot never learns its true heading; "N" just means "the way it faced at the start".
DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))


def _ahead(cell, h, n=1):
    return cell[0] + DIRS[h][0] * n, cell[1] + DIRS[h][1] * n


def _update_pose(sensors, memory):
    """Apply what the previous action actually did. Moves are exact, so only a wall hit can surprise us."""
    last = memory["last"]
    if last == "turn_left":
        memory["h"] = (memory["h"] - 1) % 4
    elif last == "turn_right":
        memory["h"] = (memory["h"] + 1) % 4
    elif last == "forward":
        # Moving wheels read 120 +-5; a stalled wheel reads exactly 0. 60 splits them with a big margin.
        if sensors["rpm_left"] > 60 and sensors["rpm_right"] > 60:
            memory["pos"] = _ahead(memory["pos"], memory["h"])
        else:
            _mark(memory, _ahead(memory["pos"], memory["h"]), sure=False)  # we hit it: certainly a wall
    if memory["pos"] not in memory["visited"]:
        memory["visited"].add(memory["pos"])
        memory["version"] += 1
    _mark(memory, memory["pos"], sure=True)  # we're standing on it: certainly open


def _mark(memory, cell, vote=None, sure=None):
    """Record a vote (True = open, False = wall) or a certainty for one cell, and update the map entry for it.

    memory["known"] is the map: {cell: True open / False wall}; cells we don't know are simply absent.
    It is updated here, one cell at a time, so nothing has to rebuild it every tick. memory["version"] counts
    real changes (a cell's state flipping, a new cell visited) so work based on the map can be reused until then.
    """
    if sure is not None:
        memory["sure"][cell] = sure
    if vote is not None:
        memory["votes"].setdefault(cell, [0, 0])[0 if vote else 1] += 1
    state = memory["sure"].get(cell)
    if state is None:
        opens, walls = memory["votes"].get(cell, (0, 0))
        state = True if opens > walls else False if walls > opens else None
    if memory["known"].get(cell) is not state:
        memory["version"] += 1  # the map changed: anything worked out from it must be redone
    if state is None:
        memory["known"].pop(cell, None)
    else:
        memory["known"][cell] = state


def _is_open(memory, cell):
    """True = open, False = wall, None = don't know (never sensed, or the readings are tied)."""
    return memory["known"].get(cell)


def _sense(sensors, memory):
    """Add this tick's front/left/right readings to the map as votes.

    Noise makes a single reading wrong now and then, so no single reading decides a cell: every reading is a
    vote for "open" or "wall", and the majority wins. We pass most cells several times, so a bad vote gets outvoted.
    """
    pos, h = memory["pos"], memory["h"]
    readings = ((sensors["dist_front"], h), (sensors["dist_left"], (h - 1) % 4),
                (sensors["dist_right"], (h + 1) % 4))
    # A reading equal to the sensor range means "at least that far", so it tells us nothing about the
    # next cell. We aren't told the range; the largest reading seen so far is a safe lower bound.
    memory["range"] = max(memory["range"], *(d for d, _ in readings))
    for d, dh in readings:
        for i in range(1, d + 1):
            _mark(memory, _ahead(pos, dh, i), vote=True)
        if d < memory["range"]:
            _mark(memory, _ahead(pos, dh, d + 1), vote=False)


def _next_to(memory, cell, doubt=0, among=None):
    """Directions from `cell` whose neighbour is uncertain.

    doubt=0: unknown (never sensed, or tied votes) -- and in `among`, if given.
    doubt=k: a wall we never touched whose wall votes lead by at most k -- maybe a noise-made wall.
    """
    out = []
    for h in range(4):
        n = _ahead(cell, h)
        state = _is_open(memory, n)
        if state is None and not doubt and (among is None or n in among):
            out.append(h)
        elif state is False and doubt and n not in memory["sure"]:
            opens, walls = memory["votes"][n]
            if walls - opens <= doubt:
                out.append(h)
    return out


def _watchers(memory, doubt=0, among=None):
    """{open cell: directions from it to an uncertain neighbour}, for every open cell (see _next_to).

    Worked out once per tick, so the route search can ask "does standing here show us something?" instantly.
    """
    out = {}
    for cell, is_open in memory["known"].items():
        if is_open:
            dirs = _next_to(memory, cell, doubt, among)
            if dirs:
                out[cell] = dirs
    return out


TURN = {"turn_left": -1, "turn_right": 1}

# The goal has been the cell FARTHEST from the start in every maze we've seen (all 4 practice mazes). We only use
# that to skip cells that provably can't be the farthest. SLACK keeps a margin in case "farthest" is measured in
# ticks (with turns) rather than steps: on generated mazes those two picks differ by at most 3 steps.
SLACK = 3
DEPTH_WEIGHT = 0.25  # swept 0 / 0.25 / 0.5 / 1 / 2 on the benchmark; see OPTIMIZATIONS.md #5


def _bfs(known, box=None):
    """Steps from the start to every cell reachable through known-open cells.

    With `box`: through every cell that isn't a known wall (unknown counts as open), staying inside the box.
    """
    dist = {(0, 0): 0}
    queue = deque([(0, 0)])
    while queue:
        cell = queue.popleft()
        x, y = cell
        d = dist[cell] + 1
        for nxt in ((x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)):
            if nxt in dist:
                continue
            state = known.get(nxt)
            if box is None:
                if state is not True:
                    continue
            elif state is False or not (box[0] <= nxt[0] <= box[1] and box[2] <= nxt[1] <= box[3]):
                continue
            dist[nxt] = d
            queue.append(nxt)
    return dist


def _could_be_goal(memory):
    """Which unvisited open cells and which unknown cells could still be the farthest cell from the start.

    Two distances from the start, (0, 0):
      shortest_known: through cells we believe are open. The real distance can only be this or shorter.
      at_least:       pretending every unknown cell is open. The real distance can only be this or longer.
    Some open cell is at least `beat` = max(at_least) away, so the goal is at least that far. A cell whose
    shortest_known route is shorter than that (minus SLACK) can't be the goal -- skip it.
    A pocket of unknown cells walled in on all sides can't hide anything farther than its farthest entrance +
    its size: whatever route reaches a cell inside, it last enters the pocket from one of those entrances.
    Returns (candidate cells, candidate unknown cells, beat, at_least).
    """
    known = memory["known"]
    xs = [c[0] for c in known]
    ys = [c[1] for c in known]
    x0, x1, y0, y1 = min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1  # one unknown ring around the map
    inside = lambda c: x0 <= c[0] <= x1 and y0 <= c[1] <= y1
    # Clamping any path into this box never makes it longer, so the box doesn't break the at_least bound.
    at_least = _bfs(known, (x0, x1, y0, y1))
    shortest_known = _bfs(known)
    beat = max(at_least.get(c, 0) for c, v in known.items() if v) - SLACK

    cells = {c for c, v in known.items() if v and c not in memory["visited"]
             and shortest_known.get(c, beat) >= beat}  # not reachable yet = distance unknown = still possible
    unknown, seen = set(), set()
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if (x, y) in seen or (x, y) in known:
                continue
            pocket, stack, open_edge, entrance = [], [(x, y)], False, 0
            seen.add((x, y))
            while stack:
                c = stack.pop()
                pocket.append(c)
                for n in ((c[0], c[1] - 1), (c[0] + 1, c[1]), (c[0], c[1] + 1), (c[0] - 1, c[1])):
                    if not inside(n):
                        open_edge = True  # reaches past everything we know: could be any size
                    elif known.get(n) is True:
                        if n in shortest_known:
                            entrance = max(entrance, shortest_known[n])
                        else:
                            open_edge = True  # an open neighbour we can't reach yet: its distance is unbounded
                    elif n not in known and n not in seen:
                        seen.add(n)
                        stack.append(n)
            if open_edge or entrance + len(pocket) >= beat:
                unknown.update(pocket)
    return cells, unknown, beat, at_least


def _route(memory, is_target, value=None, right_first=False, value_max=0):
    """Fewest-ticks search from where we are to a state where is_target(cell, heading) holds.

    States are (cell, heading) and forward / turn_left / turn_right each cost one tick, so turns are counted
    exactly like the grader counts them. Forward is tried first, so among equally short routes the one that
    turns later -- usually straighter -- wins. When turning left or right from where we stand is equally good,
    right_first decides which one wins (we set it to whichever side looks more open).
    Without `value`: the nearest target. With it: the target with the lowest (ticks to get there - value);
    value never exceeds value_max, so once (ticks - value_max) can't beat the best found, we can stop searching.
    Returns the list of actions ([] if already there), or None.
    """
    known = memory["known"]
    start = (memory["pos"], memory["h"])
    came_from = {start: None}
    dist = {start: 0}
    queue = deque([start])
    best, best_key = None, None
    while queue:
        state = queue.popleft()
        if best is not None and dist[state] - value_max >= best_key:
            break  # every state from here on is at least this far away: none can beat the best
        if is_target(*state):
            key = dist[state] - value(*state) if value else 0
            if best is None or key < best_key:
                best, best_key = state, key
            if not value:
                break
        cell, h = state
        steps = [((cell, (h - 1) % 4), "turn_left"), ((cell, (h + 1) % 4), "turn_right")]
        if state == start and right_first:
            steps.reverse()
        ahead = (cell[0] + DIRS[h][0], cell[1] + DIRS[h][1])
        if known.get(ahead) is True:
            steps.insert(0, ((ahead, h), "forward"))
        for nxt, action in steps:
            if nxt not in came_from:
                came_from[nxt] = (state, action)
                dist[nxt] = dist[state] + 1
                queue.append(nxt)
    if best is None:
        return None
    actions = []
    while came_from[best]:
        best, action = came_from[best]
        actions.append(action)
    return actions[::-1]


def _cells_along(memory, actions):
    """The cells a list of actions walks through -- for the viewer's plan line."""
    cell, h, cells = memory["pos"], memory["h"], []
    for action in actions:
        if action == "forward":
            cell = _ahead(cell, h)
            cells.append(cell)
        else:
            h = (h + TURN[action]) % 4
    return cells


def decide(sensors, memory):
    """Choose one action for this tick.

    sensors : dict -- this tick's readings. See CONTRACT.md for every field.
        sensors["dist_front"]  open cells ahead before a wall (0 = wall right there)
        sensors["dist_left"]   open cells to your left
        sensors["dist_right"]  open cells to your right
        sensors["rpm_left"]    left wheel speed from your PREVIOUS action
        sensors["rpm_right"]   right wheel speed from your PREVIOUS action
        sensors["accel_fwd"]   -2.0 means you just hit a wall
        sensors["accel_lat"]   +1.0 turned right, -1.0 turned left
        sensors["at_goal"]     True when you have arrived
        sensors["tick"]        tick counter

    memory : dict -- yours. It persists across ticks for the whole maze and starts
        empty. Put your map, your believed position, anything you like in here.

    Returns one of: "forward", "turn_left", "turn_right", "wait"

    ------------------------------------------------------------------------
    Strategy (see "for dev/OPTIMIZATIONS.md" for the history and the why of each part):
      1. Track our own position from our actions; the wheels tell us if a
         forward was blocked (a wall hit).                    _update_pose
      2. Map every cell by majority vote of all readings, so a single noisy
         reading can't fool us.                               _sense, _mark
      3. The goal has been the cell farthest from the start in every maze
         seen, so skip cells that provably can't be the farthest.
                                                              _could_be_goal
      4. Walk to the best remaining spot: fewest ticks away counting turns,
         with a slight preference for spots deeper in the maze.     _route
      5. If that runs out, explore everything; if the map is fully explored
         with no goal, re-check the walls we're least sure of.
      6. If anything ever raises an error, finish with the kit's wall follower
         rather than crash.                                   _wall_follower

    memory keys also read by the dev viewer (the grader ignores them):
        why (str), plan (list of cells), known ({cell: open?}), visited (set), pos, h,
        ruled_out (set: open cells that can't be the goal)
    ------------------------------------------------------------------------
    """
    if memory.get("fallback"):
        return _wall_follower(sensors, memory)
    try:
        return _explore(sensors, memory)
    except Exception as error:  # never crash: a crash scores 0 for the whole maze
        print(f"decide() failed on tick {sensors.get('tick')}: {error!r} -- finishing with the wall follower",
              file=sys.stderr)
        memory["fallback"] = True
        return _wall_follower(sensors, memory)


def _wall_follower(sensors, memory):
    """The kit's right-hand wall follower. Our safety net: dumb, but it needs no memory, so it can't be broken."""
    turned_right_last_tick = memory.get("turned_right", False)
    memory["turned_right"] = False
    if sensors["dist_right"] > 0 and not turned_right_last_tick:
        memory["turned_right"] = True
        memory["why"] = "SAFETY NET (an error happened): right side open -> turn right"
        return "turn_right"
    if sensors["dist_front"] > 0:
        memory["why"] = "SAFETY NET (an error happened): front open -> forward"
        return "forward"
    memory["why"] = "SAFETY NET (an error happened): right and front blocked -> turn left"
    return "turn_left"


def _explore(sensors, memory):
    """The real strategy -- see decide()."""
    if not memory:
        memory.update(pos=(0, 0), h=0, last=None, range=1, votes={}, sure={}, known={}, visited=set(), version=0)

    _update_pose(sensors, memory)
    _sense(sensors, memory)

    h, pos = memory["h"], memory["pos"]
    # Targets, in order: a cell we haven't stood on (any could be the goal), or a spot next to a cell we
    # know nothing about (unsensed, or noise left its votes tied). Arriving there senses it.
    def sees(watch):  # standing on c facing h: is an uncertain neighbour in front/left/right (not behind)?
        return lambda c, h: any(d != (h + 2) % 4 for d in watch.get(c, ()))

    if memory.get("cache_version") != memory["version"]:  # recompute only when the map actually changed
        cells, unknown, beat, at_least = _could_be_goal(memory)
        memory["cache"] = cells, unknown, beat, at_least, _watchers(memory, among=unknown)
        memory["cache_version"] = memory["version"]
    cells, unknown, beat, at_least, watch = memory["cache"]

    def depth(c, h):  # how far from the start this target reaches: deeper = likelier to hold the farthest cell
        if c in cells:
            return DEPTH_WEIGHT * at_least.get(c, 0)
        return DEPTH_WEIGHT * max((at_least.get(_ahead(c, d), 0) for d in watch.get(c, ()) if d != (h + 2) % 4),
                                  default=0)

    memory["ruled_out"] = {c for c, v in memory["known"].items() if v and c not in cells} - memory["visited"]
    doubt = 0
    right_first = sensors["dist_right"] > sensors["dist_left"]
    in_view = sees(watch)
    actions = _route(memory, lambda c, h: c in cells or in_view(c, h), depth if DEPTH_WEIGHT else None,
                     right_first, DEPTH_WEIGHT * max(at_least.values()))
    reason = f"nearest spot that could still be the goal (>= {beat} steps from start)"
    if actions is None:
        # The rule "goal = farthest cell" found nothing left. Maybe noise misled it, maybe the rule doesn't
        # hold in this maze -- either way, fall back to exploring everything.
        in_view = sees(_watchers(memory))
        actions = _route(memory, lambda c, h: c not in memory["visited"] or in_view(c, h))
        reason = "nothing left that fits 'goal = farthest cell' -> nearest unvisited or unsensed spot"
    while actions is None and doubt < 50:
        # Everything reachable is explored and still no goal: noise must have faked a wall somewhere.
        # Re-check the walls we are least sure about; widen the net if that finds nothing.
        doubt = memory["doubt"] = max(doubt * 2, memory.get("doubt", 1))  # 1, 2, 4 ... 64: at most 7 searches
        actions = _route(memory, sees(_watchers(memory, doubt)))
        reason = "map explored, no goal -> re-checking a doubtful wall"
    actions = actions or []
    memory["plan"] = _cells_along(memory, actions)
    if not actions:
        action = "wait"
        memory["why"] = ("a doubtful wall is in view -> wait one tick for a fresh reading" if doubt else
                         "a cell in view is uncertain (tied votes) -> wait one tick for a fresh reading")
    else:
        action = actions[0]
        n = len(actions)
        memory["why"] = f"{reason} (ring) is {n} tick{'s' if n > 1 else ''} away, counting turns -> {action}"

    memory["last"] = action
    return action


# =============================================================================
# DO NOT EDIT BELOW THIS LINE
# This is the plumbing that talks to the grader. Changing it will break your
# submission and score you zero.
# =============================================================================

def _main():
    print(json.dumps({"ready": True}), flush=True)
    memory = {}
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        sensors = json.loads(line)
        action = decide(sensors, memory)
        print(json.dumps({"action": action}), flush=True)
        if sensors.get("at_goal"):
            break


if __name__ == "__main__":
    _main()
