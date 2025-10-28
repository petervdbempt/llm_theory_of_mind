import random
import json
import re
from typing import Dict, Tuple, Set, List, Any
from collections import Counter

# 👇 NEW IMPORTS for Gemini
from google import genai
from google.genai import types
# 👆 NEW IMPORTS

# Assuming you still have game.colored_trails and COLORS defined elsewhere
from game.colored_trails import ColoredTrails, GameState, COLORS


def read_api_key(filepath="API_token_gemini.txt"):
    # Ensure this file contains your Gemini API Key
    with open(filepath, "r") as f:
        return f.read().strip()


api_key = read_api_key()
print(f"used api key: {api_key}")


class LLMPlayer:
    """
    LLM-backed player that supports multi-chip trades, now using the Gemini API.
    """

    def __init__(self, player_id: str, game_env: ColoredTrails):
        self.player_id = player_id
        self.opponent_id = "p2" if player_id == "p1" else "p1"
        self.game = game_env
        self.COLORS = COLORS
        self.proposed_trades: Set[Tuple[Tuple[str, ...], Tuple[str, ...]]] = set()
        self.history: List[str] = []

        # 👇 MODIFICATION: Initialize Gemini client
        try:
            # The client will automatically use the API key from the environment
            # or explicitly passed (though often it's best practice to use
            # the GEMINI_API_KEY environment variable).
            # Since you are explicitly passing it, we use it here.
            self.client = genai.Client(api_key=api_key)
        except Exception as e:
            print(f"Error initializing Gemini client: {e}")
            raise

        # Recommended model for instruction following tasks
        self.model_name = "gemini-2.5-flash"
        # 👆 MODIFICATION

    # (The utility, parsing, and formatting methods remain the same)
    def calculate_utility(self, new_chips: Dict[str, int]) -> int:
        # ... (implementation remains the same)
        temp_state = GameState(goal_pos=self.game.states[self.player_id].goal_pos,
                               chips=Counter(new_chips))
        temp_states = {
            self.player_id: temp_state,
            self.opponent_id: self.game.states[self.opponent_id]
        }
        temp_game = ColoredTrails(self.game.board, temp_states)
        max_score, _, _ = temp_game.get_max_score_and_path(self.player_id)
        return max_score

    def query_llm(self, prompt: str, stop: List[str] | None = None) -> str:
        """
        Queries the Gemini model with the given prompt.
        """
        # 👇 MODIFICATION: Rewrite to use genai.Client.models.generate_content
        try:
            # Gemini accepts the entire prompt as a single string for this usage

            # Configure generation settings
            config = types.GenerateContentConfig(
                stop_sequences=stop or ["\n\n"]
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )

            print(f"Raw response: {response}")
            return response.text.strip()

        except Exception as e:
            # Simplification: Removed conversational fallback as it's not standard
            # with the new SDK and the current model is robust for instructions.
            print(f"[{self.player_id}] LLM call failed ({e}). Defaulting to 'Pass'.")
            return "Pass"
        # 👆 MODIFICATION

    def _parse_trade_response(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Robustly extracts the first valid JSON block and parses give/receive lists.
        Falls back to ["Pass"], ["Pass"] if invalid.
        """
        text_raw = (text or "").strip()

        # Try to extract the first {...} JSON block using regex
        match = re.search(r"\{\s*\"(?:give|receive)\"\s*:\s*\[.*?\}\s*", text_raw, re.DOTALL)
        if match:
            json_str = match.group(0)
        else:
            json_str = text_raw  # fallback if no braces found

        try:
            parsed = json.loads(json_str)
            give = parsed.get("give", "Pass")
            receive = parsed.get("receive", "Pass")

            def normalize(field):
                if isinstance(field, str):
                    return ["Pass"] if field.upper() == "PASS" else [field]
                elif isinstance(field, list):
                    return field if field else ["Pass"]
                else:
                    return ["Pass"]

            give_list = normalize(give)
            receive_list = normalize(receive)
            return give_list, receive_list

        except Exception as e:
            print(f"[WARN] _parse_trade_response failed to parse JSON: {e}")
            print(f"Raw model output:\n{text_raw}")
            return ["Pass"], ["Pass"]

    def _format_board_state(self) -> str:
        # ... (implementation remains the same)
        board_str = ""
        for r in range(5):
            row = []
            for c in range(5):
                cell = self.game.board[r][c]
                row.append(cell[:2])
            board_str += " ".join(f"{item:4}" for item in row) + "\n"
        return board_str.strip()

    def propose_trade(self) -> Tuple[List[str], List[str]]:
        # ... (implementation remains the same)
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
- Respond with ONLY the proposed trade in the JSON format below:
- {{"give": ["COLOR1", "COLOR2", ...], "receive": ["COLOR1", "COLOR2", ...]}}
- If you don't need any trade, output:
- {{"give": ["PASS"], "receive": ["PASS"]}}
"""

        print(
            f"\n========== LLM PROMPT ({self.player_id}) ==========\n{prompt}\n==============================================\n")

        llm_output = self.query_llm(prompt, stop=["\n\n"])
        give_list, receive_list = self._parse_trade_response(llm_output)

        # Record proposed trade to avoid repetition
        trade_key = (tuple(sorted(give_list)), tuple(sorted(receive_list)))
        self.proposed_trades.add(trade_key)

        log_msg = f"{self.player_id} proposed trade: GIVE {give_list} for RECEIVE {receive_list}"
        print(f"  [{self.player_id}] {log_msg}")
        self.history.append(log_msg)
        return give_list, receive_list

    def evaluate_proposal(self, proposal: Tuple[List[str], List[str]]) -> bool:
        # ... (implementation remains the same)
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
- Respond with ONLY your decision in the JSON format below: 
- {{"action": "ACCEPT"}}
- OR
- {{"action": "REJECT"}}
"""

        print(
            f"\n========== LLM PROMPT ({self.player_id}) ==========\n{prompt}\n==============================================\n")

        llm_output = self.query_llm(prompt, stop=["\n\n"]).strip()
        out_upper = llm_output.upper()

        # Try to extract valid JSON even if mixed with text
        match = re.search(r"\{\s*\"action\"\s*:\s*\"(ACCEPT|REJECT)\".*?\}", llm_output, re.DOTALL | re.IGNORECASE)
        if match:
            json_str = match.group(0)
        else:
            json_str = llm_output

        try:
            parsed = json.loads(json_str)
            action = parsed.get("action", "")
            action_upper = action.upper() if isinstance(action, str) else str(action).upper()
        except Exception:
            print("[WARN] evaluate_proposal failed to parse JSON")
            if "ACCEPT" in llm_output.upper() and "REJECT" not in llm_output.upper():
                action_upper = "ACCEPT"
            elif "REJECT" in llm_output.upper() and "ACCEPT" not in llm_output.upper():
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