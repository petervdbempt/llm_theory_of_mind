import json
import random
from collections import Counter, deque
from typing import List, Tuple, Dict, Set, Optional

# --- Configuration Constants ---
BOARD_SIZE = 5
COLORS = ["RE", "BL", "YE", "GR", "OR"]
START_POS = (2, 2)

# --- Scoring Constants (from the paper's general scoring scheme) ---
STEP_POINTS = 100
GOAL_BONUS = 500
UNUSED_CHIP_POINTS = 50
PENALTY_PER_ROUND = 1


class GameState:
    """Represents the current state of a single player."""

    def __init__(self, goal_pos: Tuple[int, int], chips: Dict[str, int]):
        self.current_pos = START_POS
        self.goal_pos = goal_pos
        self.chips = Counter(chips)
        self.initial_chips = Counter(chips)  # Store initial chips for reference
        self.steps_taken = 0


class ColoredTrails:
    """
    Environment logic for the Colored Trails game.
    Handles board generation, movement checks, pathfinding, and scoring.
    """

    def __init__(self, board_map: List[List[str]], player_states: Dict[str, GameState]):
        self.board = board_map
        self.states = player_states

    @staticmethod
    def _is_valid(r: int, c: int) -> bool:
        """Checks if a coordinate is within the 5x5 board boundaries."""
        return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE

    def _get_manhattan_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        """Calculates Manhattan distance between two positions."""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def get_max_score_and_path(self, player_id: str) -> Tuple[int, int, int]:
        """
        Calculates the maximum score a player can achieve from the start position
        to the goal, given their current chip inventory, using a Breadth-First Search (BFS).

        The result is the utility (max score) used for negotiation.

        :param player_id: The ID of the player to score.
        :return: (max_score, min_steps_to_goal, max_unused_chips_value)
        """
        state = self.states[player_id]
        goal = state.goal_pos
        start_chips = state.chips

        # Pathfinding state: (position, steps, chips_remaining_counter)
        queue = deque([(START_POS, 0, start_chips)])

        # Visited: (position, chips_tuple) -> steps
        # Stores the minimum steps required to reach a (position, chip_configuration) state.
        visited: Dict[Tuple[Tuple[int, int], Tuple], int] = {}

        best_path_data: Optional[Tuple[int, int]] = None  # (min_steps, max_remaining_chips)

        # BFS guarantees finding the shortest path in terms of steps first.
        while queue:
            current_pos, steps, remaining_chips = queue.popleft()

            # Hashable representation of chips for the visited set
            chips_tuple = tuple(sorted(remaining_chips.items()))

            if (current_pos, chips_tuple) in visited and visited[(current_pos, chips_tuple)] <= steps:
                continue
            visited[(current_pos, chips_tuple)] = steps

            remaining_chip_count = sum(remaining_chips.values())

            # Goal Check:
            if current_pos == goal:
                if best_path_data is None or \
                        steps < best_path_data[0] or \
                        (steps == best_path_data[0] and remaining_chip_count > best_path_data[1]):
                    # Update if shorter path found, or same length but more chips remaining
                    best_path_data = (steps, remaining_chip_count)

            # Pruning: Don't explore paths longer than the current best known path to the goal
            if best_path_data is not None and steps >= best_path_data[0]:
                continue

            # Explore neighbors
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                next_r, next_c = current_pos[0] + dr, current_pos[1] + dc
                next_pos = (next_r, next_c)

                if self._is_valid(next_r, next_c):
                    target_color = self.board[next_r][next_c]

                    if remaining_chips.get(target_color, 0) > 0:
                        # Make the move: use one chip
                        new_chips = remaining_chips.copy()
                        new_chips[target_color] -= 1

                        if new_chips[target_color] == 0:
                            del new_chips[target_color]

                        queue.append((next_pos, steps + 1, new_chips))

        # --- Scoring Calculation ---

        if best_path_data:
            # Case 1: Goal is reachable
            min_steps_to_goal, max_remaining_chips = best_path_data

            score = (min_steps_to_goal * STEP_POINTS) + GOAL_BONUS
            final_unused_chip_value = max_remaining_chips * UNUSED_CHIP_POINTS
            max_score = score + final_unused_chip_value
            final_steps = min_steps_to_goal

        else:
            # Case 2: Goal not reachable

            # Find the best reachable position (closest to the goal)
            min_dist_to_goal = self._get_manhattan_distance(START_POS, goal)
            max_remaining_chips = sum(start_chips.values())

            if visited:
                best_reach = None  # (min_dist, max_chips, position)

                for (pos, chips_tuple), steps in visited.items():
                    dist = self._get_manhattan_distance(pos, goal)
                    chip_count = sum(c for _, c in chips_tuple)

                    if best_reach is None or \
                            dist < best_reach[0] or \
                            (dist == best_reach[0] and chip_count > best_reach[1]):
                        best_reach = (dist, chip_count, pos)

                if best_reach:
                    min_dist_to_goal, max_remaining_chips, best_pos_reached = best_reach

                    initial_dist = self._get_manhattan_distance(START_POS, goal)
                    distance_moved_points = (initial_dist - min_dist_to_goal) * STEP_POINTS

                    final_unused_chip_value = max_remaining_chips * UNUSED_CHIP_POINTS
                    max_score = distance_moved_points + final_unused_chip_value
                    final_steps = self._get_manhattan_distance(START_POS, best_pos_reached)

            else:
                # No moves possible
                max_score = 0
                final_steps = 0
                final_unused_chip_value = 0

        return max_score, final_steps, final_unused_chip_value

    def apply_trade(self, p1_id: str, p2_id: str, p1_give: List[str], p1_receive: List[str]):
        """
        Applies a successful trade between two players.
        Now supports multi-chip trades (e.g., 2-for-1, 3-for-2, etc.)

        :param p1_id: ID of the proposing player
        :param p2_id: ID of the responding player
        :param p1_give: List of chips p1 gives away
        :param p1_receive: List of chips p1 receives
        """

        # Validate that p1 has all the chips they're offering
        p1_give_counter = Counter(p1_give)
        for chip, count in p1_give_counter.items():
            if self.states[p1_id].chips.get(chip, 0) < count:
                print(
                    f"ERROR: {p1_id} doesn't have enough {chip} chips to trade (needs {count}, has {self.states[p1_id].chips.get(chip, 0)})")
                return False

        # Validate that p2 has all the chips p1 wants to receive
        p1_receive_counter = Counter(p1_receive)
        for chip, count in p1_receive_counter.items():
            if self.states[p2_id].chips.get(chip, 0) < count:
                print(
                    f"ERROR: {p2_id} doesn't have enough {chip} chips to trade (needs {count}, has {self.states[p2_id].chips.get(chip, 0)})")
                return False

        # Execute the trade
        # P1 gives chips to P2
        for chip in p1_give:
            self.states[p1_id].chips[chip] -= 1
            if self.states[p1_id].chips[chip] == 0:
                del self.states[p1_id].chips[chip]
            self.states[p2_id].chips[chip] = self.states[p2_id].chips.get(chip, 0) + 1

        # P1 receives chips from P2
        for chip in p1_receive:
            self.states[p2_id].chips[chip] -= 1
            if self.states[p2_id].chips[chip] == 0:
                del self.states[p2_id].chips[chip]
            self.states[p1_id].chips[chip] = self.states[p1_id].chips.get(chip, 0) + 1

        return True

    @staticmethod
    def generate_random_game(seed: Optional[int] = None) -> Tuple[List[List[str]], Dict[str, GameState]]:
        """Generates a new, random game instance."""

        rng = random.Random(seed)

        # 1. Generate Board (5x5, random colors)
        board_map = [[rng.choice(COLORS) for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

        # 2. Generate Goal Locations (at least 3 steps away from START_POS (2,2))
        possible_goals = []
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if ColoredTrails._is_valid(r, c) and abs(r - START_POS[0]) + abs(c - START_POS[1]) >= 3:
                    possible_goals.append((r, c))

        if len(possible_goals) < 2:
            possible_goals = [(0, 0), (4, 4)]

        goal_p1, goal_p2 = rng.sample(possible_goals, 2)

        # 3. Generate Initial Chips (4 random chips each)
        chips_p1 = Counter([rng.choice(COLORS) for _ in range(4)])
        chips_p2 = Counter([rng.choice(COLORS) for _ in range(4)])

        # 4. Create Player States
        player_states = {
            'p1': GameState(goal_p1, chips_p1),
            'p2': GameState(goal_p2, chips_p2),
        }

        return board_map, player_states



def scenario_to_dict(board_map: List[List[str]], states: Dict[str, GameState], seed: Optional[int]) -> dict:
    """Serialize a full scenario (board, goals, chips, optional seed) to a Python dict."""
    return {
        "meta": {"board_size": BOARD_SIZE, "colors": COLORS, "start_pos": START_POS, "seed": seed},
        "board": board_map,
        "players": {
            "p1": {"goal": states['p1'].goal_pos, "chips": dict(states['p1'].chips)},
            "p2": {"goal": states['p2'].goal_pos, "chips": dict(states['p2'].chips)},
        },
    }

def save_scenario_json(path: str, board_map: List[List[str]], states: Dict[str, GameState],
                       seed: Optional[int] = None):
    """Write scenario JSON to disk."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scenario_to_dict(board_map, states, seed), f, indent=2)


def load_scenario_json(path: str) -> Tuple[List[List[str]], Dict[str, GameState]]:
    """Load a scenario JSON and reconstruct board & player states."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    board_map = data["board"]
    p1 = data["players"]["p1"]
    p2 = data["players"]["p2"]
    states = {
        "p1": GameState(tuple(p1["goal"]), p1["chips"]),
        "p2": GameState(tuple(p2["goal"]), p2["chips"]),
    }
    return board_map, states
