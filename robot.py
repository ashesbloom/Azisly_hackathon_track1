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
    What is below is a RIGHT-HAND WALL FOLLOWER. It works: it will solve the
    early mazes. It is deliberately not good enough to win, because it has no
    memory -- it never learns the maze, so it walks the same long way round
    every time and it can loop forever in an open room.

    Your job is to do better. Some directions worth taking:

      1. Track where you are. The wheels tell you what you actually did:
         both wheels near +120 means you advanced one cell; wheels
         counter-rotating means you turned 90 degrees. Keep (x, y, heading)
         in memory and update it every tick.

      2. Build a map. Once you know where you are, record the walls you
         sense into memory. Now you know which parts of the maze you have
         not explored yet.

      3. Route with what you know. With a map, you can flood-fill or BFS to
         the nearest unexplored cell instead of wandering, and once you have
         found the goal you know the short way back.

      4. Handle the nasty mazes. On the hardest ones you only feel adjacent
         walls, distance readings are occasionally wrong by one, and the
         wheel encoders wobble by about 5. Compare RPM with a tolerance, not
         with ==, and consider ignoring a single odd sensor reading rather
         than trusting it immediately.

    Scoring, briefly: reaching the goal is worth far more than reaching it
    quickly, and every wall you hit costs you 5 points plus a wasted tick.
    Get it solving first. Optimise second.
    ------------------------------------------------------------------------
    """
    # --- example strategy: right-hand wall follower --- replace this ---

    # Don't turn right twice in a row: after turning into an opening we want to
    # actually drive into it before looking right again.
    turned_right_last_tick = memory.get("turned_right", False)
    memory["turned_right"] = False

    if sensors["dist_right"] > 0 and not turned_right_last_tick:
        memory["turned_right"] = True
        memory["why"] = "right side open -> turn right (right-hand rule)"
        return "turn_right"

    if sensors["dist_front"] > 0:
        memory["why"] = ("just turned right, so drive into the opening" if turned_right_last_tick
                         else "right is a wall, front is open -> keep following the wall")
        return "forward"

    memory["why"] = "right and front blocked -> turn left"
    return "turn_left"


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
