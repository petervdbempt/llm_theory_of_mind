from typing import Dict, Tuple, List, Optional, Set
from game.colored_trails import ColoredTrails, GameState, COLORS
from utils.text_logger import TextLogger



class GreedyPlayer:
    def __init__(self, player_id: str, game_env: ColoredTrails, logger: TextLogger | None = None):
        self.player_id = player_id
        self.opponent_id = 'p2' if player_id == 'p1' else 'p1'
        self.game = game_env
        self.COLORS = COLORS
        self.proposed_trades: Set[Tuple[str, str]] = set()  # Track proposed trades to prevent repetition
        self.logger = logger
        
    def _log(self, msg: str):
        if self.logger:
            self.logger.log(f"[{self.player_id}] {msg}")
        else:
            print(f"[{self.player_id}] {msg}")

    def calculate_utility(self, new_chips: Dict[str, int]) -> int:
        temp_state = GameState(
            goal_pos=self.game.states[self.player_id].goal_pos,
            chips=new_chips
        )

        temp_states = {
            self.player_id: temp_state,
            self.opponent_id: self.game.states[self.opponent_id]
        }
        temp_game = ColoredTrails(self.game.board, temp_states)

        max_score, _, _ = temp_game.get_max_score_and_path(self.player_id)
        return max_score

    def propose_trade(self) -> Tuple[str, str]:
        current_chips = self.game.states[self.player_id].chips
        opponent_chips = self.game.states[self.opponent_id].chips  # Only used for debugging

        if not current_chips:
            self._log(f"  [{self.player_id}] No chips available to trade")
            return "Pass", "Pass"

        current_utility = self.calculate_utility(dict(current_chips))

        best_gain = 0  
        best_proposal: Tuple[str, str] = ("Pass", "Pass")

        evaluated_trades = []

        for give_color in current_chips.keys():
            if current_chips[give_color] == 0:
                continue

            for receive_color in self.COLORS:  

                if give_color == receive_color:
                    continue

                trade_tuple = (give_color, receive_color)
                if trade_tuple in self.proposed_trades:
                    continue

                hypo_chips = current_chips.copy()

                hypo_chips[give_color] -= 1
                if hypo_chips[give_color] == 0:
                    del hypo_chips[give_color]

                hypo_chips[receive_color] = hypo_chips.get(receive_color, 0) + 1

                new_utility = self.calculate_utility(dict(hypo_chips))
                gain = new_utility - current_utility

                evaluated_trades.append((give_color, receive_color, gain))

                if gain > best_gain:
                    best_gain = gain
                    best_proposal = (give_color, receive_color)

        if evaluated_trades:
            self._log(f"\n  [{self.player_id}] Evaluated {len(evaluated_trades)} possible trades:")
            self._log(f"  [{self.player_id}] Current utility: {current_utility}")
            sorted_trades = sorted(evaluated_trades, key=lambda x: x[2], reverse=True)
            for give, recv, gain in sorted_trades:
                self._log(f"    - Give {give} for {recv}: gain = {gain}")

        if best_proposal != ("Pass", "Pass"):
            self.proposed_trades.add(best_proposal)
            self._log(f"  [{self.player_id}] Selected trade: Give {best_proposal[0]} for {best_proposal[1]} (gain: {best_gain})")
        else:
            self._log(f"  [{self.player_id}] No beneficial trades found - passing")

        return best_proposal

    def evaluate_proposal(self, proposal: Tuple[str, str]) -> bool:
        opp_give_color, opp_receive_color = proposal

        if opp_give_color == "Pass":
            return True

        current_chips = self.game.states[self.player_id].chips

        if current_chips.get(opp_receive_color, 0) < 1:
            self._log(f"  [{self.player_id}] Cannot accept - missing {opp_receive_color}")
            return False

        hypo_chips = current_chips.copy()

        hypo_chips[opp_give_color] = hypo_chips.get(opp_give_color, 0) + 1

        hypo_chips[opp_receive_color] -= 1
        if hypo_chips[opp_receive_color] == 0:
            del hypo_chips[opp_receive_color]

        new_utility = self.calculate_utility(dict(hypo_chips))
        current_utility = self.calculate_utility(dict(current_chips))

        gain = new_utility - current_utility
        self._log(f"  [{self.player_id}] Evaluating: receive {opp_give_color}, give {opp_receive_color}")
        self._log(f"    Current utility: {current_utility}, New utility: {new_utility}, Gain: {gain}")

        return new_utility > current_utility