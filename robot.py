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
            memory["sure"][_ahead(memory["pos"], memory["h"])] = False  # we hit it: certainly a wall
    memory["visited"].add(memory["pos"])
    memory["sure"][memory["pos"]] = True  # we're standing on it: certainly open


def _is_open(memory, cell):
    """True = open, False = wall, None = don't know (never sensed, or the readings are tied)."""
    sure = memory["sure"].get(cell)
    if sure is not None:
        return sure
    opens, walls = memory["votes"].get(cell, (0, 0))
    return True if opens > walls else False if walls > opens else None


def _sense(sensors, memory):
    """Add this tick's front/left/right readings to the map as votes.

    Noise makes a single reading wrong now and then, so no single reading decides a cell: every reading is a
    vote for "open" or "wall", and the majority wins. We pass most cells several times, so a bad vote gets outvoted.
    """
    pos, h, votes = memory["pos"], memory["h"], memory["votes"]
    readings = ((sensors["dist_front"], h), (sensors["dist_left"], (h - 1) % 4),
                (sensors["dist_right"], (h + 1) % 4))
    # A reading equal to the sensor range means "at least that far", so it tells us nothing about the
    # next cell. We aren't told the range; the largest reading seen so far is a safe lower bound.
    memory["range"] = max(memory["range"], *(d for d, _ in readings))
    for d, dh in readings:
        for i in range(1, d + 1):
            votes.setdefault(_ahead(pos, dh, i), [0, 0])[0] += 1
        if d < memory["range"]:
            votes.setdefault(_ahead(pos, dh, d + 1), [0, 0])[1] += 1


def _next_to(memory, cell, doubt=0):
    """Directions from `cell` whose neighbour is uncertain.

    doubt=0: unknown (never sensed, or tied votes).
    doubt=k: a wall we never touched whose wall votes lead by at most k -- maybe a noise-made wall.
    """
    out = []
    for h in range(4):
        n = _ahead(cell, h)
        state = _is_open(memory, n)
        if state is None and not doubt:
            out.append(h)
        elif state is False and doubt and n not in memory["sure"]:
            opens, walls = memory["votes"][n]
            if walls - opens <= doubt:
                out.append(h)
    return out


TURN = {"turn_left": -1, "turn_right": 1}


def _route(memory, is_target):
    """Fewest-ticks search from where we are to the nearest state where is_target(cell, heading) holds.

    States are (cell, heading) and forward / turn_left / turn_right each cost one tick, so turns are counted
    exactly like the grader counts them. Forward is tried first, so among equally short routes the one that
    turns later -- usually straighter -- wins. Returns the list of actions ([] if already there), or None.
    """
    start = (memory["pos"], memory["h"])
    came_from = {start: None}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        if is_target(*state):
            actions = []
            while came_from[state]:
                state, action = came_from[state]
                actions.append(action)
            return actions[::-1]
        cell, h = state
        steps = [((cell, (h - 1) % 4), "turn_left"), ((cell, (h + 1) % 4), "turn_right")]
        if _is_open(memory, _ahead(cell, h)):
            steps.insert(0, ((_ahead(cell, h), h), "forward"))
        for nxt, action in steps:
            if nxt not in came_from:
                came_from[nxt] = (state, action)
                queue.append(nxt)
    return None


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
    Strategy (see "for dev/OPTIMIZATIONS.md" for the history and the why):
    track our own position, map every wall we sense, and always walk to the
    nearest cell we have not stood on yet -- any of them could be the goal.

    memory keys also read by the dev viewer (the grader ignores them):
        why (str), plan (list of cells), known ({cell: open?}), visited (set), pos, h
    ------------------------------------------------------------------------
    """
    if not memory:
        memory.update(pos=(0, 0), h=0, last=None, range=1, votes={}, sure={}, visited=set())

    _update_pose(sensors, memory)
    _sense(sensors, memory)
    # for the dev viewer only: the map as it currently stands
    memory["known"] = {c: _is_open(memory, c) for c in set(memory["votes"]) | set(memory["sure"])
                       if _is_open(memory, c) is not None}

    h, pos = memory["h"], memory["pos"]
    # Targets, in order: a cell we haven't stood on (any could be the goal), or a spot next to a cell we
    # know nothing about (unsensed, or noise left its votes tied). Arriving there senses it.
    def sees(c, h, doubt=0):  # standing on c facing h, is an uncertain neighbour in front/left/right?
        return any(d != (h + 2) % 4 for d in _next_to(memory, c, doubt))

    doubt = 0
    actions = _route(memory, lambda c, h: c not in memory["visited"] or sees(c, h))
    reason = "nearest unvisited or unsensed spot"
    while actions is None and doubt < 50:
        # Everything reachable is explored and still no goal: noise must have faked a wall somewhere.
        # Re-check the walls we are least sure about; widen the net if that finds nothing.
        doubt = memory["doubt"] = max(doubt + 1, memory.get("doubt", 1))
        actions = _route(memory, lambda c, h: sees(c, h, doubt))
        reason = "map explored, no goal -> re-checking a doubtful wall"
    actions = actions or []
    memory["plan"] = _cells_along(memory, actions)
    if not actions:
        action = "wait"
        memory["why"] = "a cell in view is uncertain (tied votes) -> wait one tick for a fresh reading"
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
