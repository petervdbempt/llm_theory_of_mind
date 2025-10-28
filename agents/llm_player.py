import random
import json
from typing import Dict, Tuple, Set, List, Any
from collections import Counter

from game.colored_trails import ColoredTrails, GameState, COLORS
from huggingface_hub import InferenceClient


def read_api_key(filepath="API_token.txt"):
    with open(filepath, "r") as f:
        return f.read().strip()


api_key = read_api_key()
print(f"used api key: {api_key}")


class LLMPlayer:
    """
    LLM-backed player that supports multi-chip trades.
    The prompt allows any chip redistribution (e.g., 1-for-1, 3-for-1, 1-for-2, etc.)
    """

    def __init__(self, player_id: str, game_env: ColoredTrails):
        self.player_id = player_id
        self.opponent_id = "p2" if player_id == "p1" else "p1"
        self.game = game_env
        self.COLORS = COLORS
        self.proposed_trades: Set[Tuple[Tuple[str, ...], Tuple[str, ...]]] = set()
        self.history: List[str] = []
        self.client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=api_key)

    def calculate_utility(self, new_chips: Dict[str, int]) -> int:
        temp_state = GameState(goal_pos=self.game.states[self.player_id].goal_pos,
                               chips=Counter(new_chips))
        temp_states = {
            self.player_id: temp_state,
            self.opponent_id: self.game.states[self.opponent_id]
        }
        temp_game = ColoredTrails(self.game.board, temp_states)
        max_score, _, _ = temp_game.get_max_score_and_path(self.player_id)
        return max_score

    def query_llm(self, prompt: str, max_tokens: int = 256, stop: List[str] | None = None) -> str:
        try:
            _prompt = [{"role": "user", "content": prompt}]
            response = self.client.chat_completion(
                _prompt,
                max_tokens=max_tokens,
                stop=stop or ["\n\n"]
            )
            print(f"Raw response: {response}")
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "not supported" in str(e).lower() and "conversational" in str(e).lower():
                try:
                    conv = self.client.conversational(prompt)
                    return conv.generated_text.strip()
                except Exception as inner_e:
                    print(f"[{self.player_id}] Conversational fallback failed ({inner_e}). Defaulting to 'Pass'.")
                    return "Pass"
            print(f"[{self.player_id}] LLM call failed ({e}). Defaulting to 'Pass'.")
            return "Pass"

    def _parse_trade_response(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Returns (give_list, receive_list)
        If pass: returns (["Pass"], ["Pass"])
        Only accepts valid JSON format.
        """
        text_raw = (text or "").strip()

        try:
            parsed = json.loads(text_raw)
            give = parsed.get("give", "Pass")
            receive = parsed.get("receive", "Pass")

            # Handle both string and list formats
            if isinstance(give, str):
                if give.upper() == "PASS":
                    give_list = ["Pass"]
                else:
                    give_list = [give]
            elif isinstance(give, list):
                give_list = give if give else ["Pass"]
            else:
                give_list = ["Pass"]

            if isinstance(receive, str):
                if receive.upper() == "PASS":
                    receive_list = ["Pass"]
                else:
                    receive_list = [receive]
            elif isinstance(receive, list):
                receive_list = receive if receive else ["Pass"]
            else:
                receive_list = ["Pass"]

            return give_list, receive_list
        except Exception:
            pass

        print("WRONG FORMAT - Expected valid JSON only")
        return ["Pass"], ["Pass"]

    def _format_board_state(self) -> str:
        """Creates a clean board representation with only color codes."""
        board_str = ""
        for r in range(5):
            row = []
            for c in range(5):
                cell = self.game.board[r][c]
                row.append(cell[:2])
            board_str += " ".join(f"{item:4}" for item in row) + "\n"
        return board_str.strip()

    def propose_trade(self) -> Tuple[List[str], List[str]]:
        my_chips = self.game.states[self.player_id].chips
        if not my_chips:
            print(f"  [{self.player_id}] No chips to trade.")
            return ["Pass"], ["Pass"]

        goal_pos = self.game.states[self.player_id].goal_pos
        prompt = f"""
GAME RULES:
- You are Player {self.player_id.upper()} in the Colored Trails game, and your opponent is Player {self.opponent_id.upper()}.
- Your objective is to move as close as possible to your goal location.
- You can only move to adjacent tiles, not diagonally.
- Each move costs one chip of the same color as the tile you move onto.
- You do not need to pay for the start location, but you do need to pay for the goal location.
- Before moving, a negotiation phase takes place, where the two players may propose any redistribution of chips (e.g., 1-for-1, 3-for-1, 1-for-2, etc.).
- If the proposal is rejected, it becomes the other player's turn to propose. If the proposal is accepted or if a player passes, the redistribution becomes final and the negotiation immediately ends.
- Negotiation can continue for up to 5 rounds, alternating turns after each rejection.
- After a trade or a pass, both players immediately try to move as close as possible to their goal location.

SCORING:
- +100 points per step closer to your goal
- +500 points for reaching your goal
- +50 points for each unused chip
- -1 point per negotiation round

GAME STATE (5x5):
{self._format_board_state()}
- Start position: row 2, column 2
- Goal position: row {goal_pos[0]}, column {goal_pos[1]}
- Your chips: {dict(self.game.states[self.player_id].chips)}
- Opponent's chips: {dict(self.game.states[self.opponent_id].chips)}
- Negotiation history:
{chr(10).join(self.history) if self.history else '(none)'}

WHAT TO DO:
- You are allowed to propose ONE trade
- Output ONLY the proposed trade in the JSON format below:
- {{"give": ["COLOR1", "COLOR2", ...], "receive": ["COLOR1", "COLOR2", ...]}}
- If you don't need any trade, output:
- {{"give": ["PASS"], "receive": ["PASS"]}}
"""

        print(
            f"\n========== LLM PROMPT ({self.player_id}) ==========\n{prompt}\n==============================================\n")

        llm_output = self.query_llm(prompt, max_tokens=256, stop=["\n\n"])
        give_list, receive_list = self._parse_trade_response(llm_output)

        # Record proposed trade to avoid repetition
        trade_key = (tuple(sorted(give_list)), tuple(sorted(receive_list)))
        self.proposed_trades.add(trade_key)

        log_msg = f"{self.player_id} proposed trade: GIVE {give_list} for RECEIVE {receive_list}"
        print(f"  [{self.player_id}] {log_msg}")
        self.history.append(log_msg)
        return give_list, receive_list

    def evaluate_proposal(self, proposal: Tuple[List[str], List[str]]) -> bool:
        opp_give, opp_receive = proposal
        my_state = self.game.states[self.player_id]

        if opp_give == ["Pass"] or (len(opp_give) == 1 and opp_give[0] == "Pass"):
            self.history.append(f"{self.opponent_id} PASSED")
            return True

        # Validate we have all requested chips
        opp_receive_counter = Counter(opp_receive)
        for chip, count in opp_receive_counter.items():
            if my_state.chips.get(chip, 0) < count:
                print(f"  [{self.player_id}] Cannot accept - missing {count}x {chip}")
                self.history.append(
                    f"{self.opponent_id} proposed {opp_give} for {opp_receive}. {self.player_id} REJECT")
                return False

        # Compute utility change
        current_util = self.calculate_utility(dict(my_state.chips))
        hypo = dict(my_state.chips)

        # Add chips we receive
        for chip in opp_give:
            hypo[chip] = hypo.get(chip, 0) + 1

        # Remove chips we give
        for chip in opp_receive:
            hypo[chip] -= 1
            if hypo[chip] == 0:
                del hypo[chip]

        new_util = self.calculate_utility(dict(hypo))
        gain = new_util - current_util

        goal_pos = self.game.states[self.player_id].goal_pos
        prompt = f"""
GAME RULES:
- You are Player {self.player_id.upper()} in the Colored Trails game, and your opponent is Player {self.opponent_id.upper()}.
- Your objective is to move as close as possible to your goal location.
- You can only move to adjacent tiles, not diagonally.
- Each move costs one chip of the same color as the tile you move onto.
- You do not need to pay for the start location, but you do need to pay for the goal location.
- Before moving, a negotiation phase takes place, where the two players may propose any redistribution of chips (e.g., 1-for-1, 3-for-1, 1-for-2, etc.).
- If the proposal is rejected, it becomes the other player's turn to propose. If the proposal is accepted or if a player passes, the redistribution becomes final and the negotiation immediately ends.
- Negotiation can continue for up to 5 rounds, alternating turns after each rejection.
- After a trade or a pass, both players immediately try to move as close as possible to their goal location.

SCORING:
- +100 points per step closer to your goal
- +500 points for reaching your goal
- +50 points for each unused chip
- -1 point per negotiation round

GAME STATE (5x5):
{self._format_board_state()}
- Start position: row 2, column 2
- Goal position: row {goal_pos[0]}, column {goal_pos[1]}
- Your chips: {dict(self.game.states[self.player_id].chips)}
- Opponent's chips: {dict(self.game.states[self.opponent_id].chips)}
- Negotiation history:
{chr(10).join(self.history) if self.history else '(none)'}

PROPOSED TRADE:
- Opponent offers: GIVE you {opp_give}, wants {opp_receive} in return

WHAT TO DO:
- Decide whether to accept or reject the trade.
- Output ONLY your decision in the JSON format below: 
- {{"action": "ACCEPT"}}
- OR
- {{"action": "REJECT"}}
"""

        print(
            f"\n========== LLM PROMPT ({self.player_id}) ==========\n{prompt}\n==============================================\n")

        llm_output = self.query_llm(prompt, max_tokens=180, stop=["\n\n"]).strip()
        out_upper = llm_output.upper()

        try:
            parsed = json.loads(llm_output)
            action = parsed.get("action", "")
            if isinstance(action, str):
                action_upper = action.upper()
            else:
                action_upper = str(action).upper()
        except Exception:
            print("WRONG FORMAT - Expected valid JSON only")
            if "ACCEPT" in out_upper and "REJECT" not in out_upper:
                action_upper = "ACCEPT"
            elif "REJECT" in out_upper and "ACCEPT" not in out_upper:
                action_upper = "REJECT"
            else:
                action_upper = "ACCEPT" if gain > 0 else "REJECT"

        accept = action_upper == "ACCEPT"

        if accept:
            print(f"  [{self.player_id}] LLM decision: ACCEPT")
            self.history.append(f"{self.player_id} ACCEPTED offer ({opp_give} for {opp_receive}).")
        else:
            print(f"  [{self.player_id}] LLM decision: REJECT")
            self.history.append(f"{self.player_id} REJECTED offer ({opp_give} for {opp_receive}).")

        return accept