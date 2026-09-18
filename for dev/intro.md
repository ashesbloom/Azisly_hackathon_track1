What it is
A maze game for a robot. The robot is dropped into an unknown maze and has to reach a hidden goal cell. You write one function, decide() in robot.py. Every tick it gets sensor readings and returns one action: forward, turn_left, turn_right or wait.

What the robot knows

Distance sensors: how many open cells are ahead, to the left and to the right. The range can be as short as 1 cell, and on hard mazes a reading is sometimes off by ±1.
Wheel speeds: whether the last move actually happened. If you pressed forward and the wheels read 0, you hit a wall.
It is never told its position, which way it's facing, the map, or where the goal is. It only finds out it reached the goal when it steps onto that cell, and the run ends right there.
Scoring per maze

Not solved: 0 points.
Solved: 100 minus 2 per tick over the optimal route, minus 5 per wall hit. The minimum for a solve is 10.
Turns cost a tick, same as moves.
The problem
The current code is a right-hand wall follower. It has no memory, so it re-walks the same corridors and can loop forever in open rooms. It also trusts every sensor reading, so noisy readings make it hit walls. It can solve the easy practice mazes but will score poorly on the harder hidden ones.

Proposed solution

Track position. Keep (x, y, heading) in memory starting from (0, 0). Moves are exact, so the only thing to catch is a wall hit, which shows up as wheels reading 0 after forward.
Build a map. Each reading is a vote that a cell is open or a wall, and the majority wins. That handles the noisy readings.
Explore smartly. Every tick, go to the cheapest cell not yet visited, counting turns as part of the cost. The goal could be any open cell, so the robot never re-walks explored ground unless it has to.
Stay safe. Only drive forward when the map says the cell ahead is open.
Test it. Write a small local benchmark that runs the practice mazes plus about 200 random ones, and reports how many were solved, wall hits, and a score using the contract's formula. play.py doesn't give a score, so this is how we'd tell whether a change helps.