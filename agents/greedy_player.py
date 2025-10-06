import random
from collections import Counter
from typing import Dict, Tuple, List, Optional

# Relative import to ColoredTrails logic and constants
from game.colored_trails import ColoredTrails, GameState, COLORS


class LLMPlayer:
    """
    A computational agent designed to play Colored Trails using a greedy heuristic
    in place of a sophisticated LLM API call for negotiation.

    This agent's 'intelligence' focuses solely on maximizing its own score
    with the trade, ignoring the opponent's utility or recursive theory of mind.
    """

    def __init__(self, player_id: str, game_env: ColoredTrails):
        self.player_id = player_id
        self.opponent_id = 'p2' if player_id == 'p1' else 'p1'
        self.game = game_env
        self.COLORS = COLORS  # Uses the updated constant from the game module

    def calculate_utility(self, new_chips: Dict[str, int]) -> int:
        """
        Calculates the maximum score (utility) if the player were to have `new_chips`.
        This is the core evaluation function for any trade.
        """
        # Create a temporary GameState with the hypothetical chips
        temp_state = GameState(
            goal_pos=self.game.states[self.player_id].goal_pos,
            chips=new_chips
        )

        # Create a temporary game environment to calculate the score
        # Note: Only the current player's state is modified for calculation
        temp_states = {
            self.player_id: temp_state,
            self.opponent_id: self.game.states[self.opponent_id]  # Keep opponent's state stable
        }
        temp_game = ColoredTrails(self.game.board, temp_states)

        # Get the max score (utility) from the environment logic
        max_score, _, _ = temp_game.get_max_score_and_path(self.player_id)
        return max_score

    def propose_trade(self) -> Tuple[str, str]:
        """
        Agent's primary action: Propose a trade (Give_Chip, Receive_Chip).

        DUMMY LLM LOGIC: Propose the trade that maximizes personal utility gain.
        """

        current_chips = self.game.states[self.player_id].chips
        opponent_chips = self.game.states[self.opponent_id].chips

        # If the player has no chips to give, they must pass
        if not current_chips:
            return "Pass", "Pass"

        current_utility = self.calculate_utility(dict(current_chips))

        best_gain = -float('inf')
        best_proposal: Tuple[str, str] = ("Pass", "Pass")

        # Iterate over all possible trades: Give 1 chip, Receive 1 chip
        for give_color in current_chips.keys():
            if current_chips[give_color] == 0:
                continue

            for receive_color in opponent_chips.keys():
                if opponent_chips[receive_color] == 0:
                    continue

                # --- Hypothetical New Chip State ---
                hypo_chips = current_chips.copy()

                # 1. Give the chip
                hypo_chips[give_color] -= 1
                if hypo_chips[give_color] == 0:
                    del hypo_chips[give_color]

                # 2. Receive the chip
                hypo_chips[receive_color] = hypo_chips.get(receive_color, 0) + 1

                # 3. Calculate new utility
                new_utility = self.calculate_utility(dict(hypo_chips))
                gain = new_utility - current_utility

                # 4. Check if this is the best trade
                if gain > best_gain:
                    best_gain = gain
                    best_proposal = (give_color, receive_color)

        return best_proposal

    def evaluate_proposal(self, proposal: Tuple[str, str]) -> bool:
        """
        Agent's secondary action: Decide whether to accept an opponent's proposal.
        The proposal is (OPPONENT_GIVE_CHIP_COLOR, OPPONENT_RECEIVE_CHIP_COLOR).

        We accept if the trade strictly increases utility.
        """
        opp_give_color, opp_receive_color = proposal

        if opp_give_color == "Pass":
            return True  # If opponent passes, we accept the round ending.

        current_chips = self.game.states[self.player_id].chips

        # 1. Check if the player has the chip the opponent is asking for
        if current_chips.get(opp_receive_color, 0) < 1:
            return False  # Cannot accept: Don't have the chip to give

        # 2. Calculate utility of accepting the proposal
        hypo_chips = current_chips.copy()

        # Player receives opp_give_color
        hypo_chips[opp_give_color] = hypo_chips.get(opp_give_color, 0) + 1

        # Player gives opp_receive_color
        hypo_chips[opp_receive_color] -= 1
        if hypo_chips[opp_receive_color] == 0:
            del hypo_chips[opp_receive_color]

        new_utility = self.calculate_utility(dict(hypo_chips))
        current_utility = self.calculate_utility(dict(current_chips))

        # Accept if the trade strictly increases utility.
        return new_utility > current_utility
