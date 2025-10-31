import logging
import random
import json
import re
from typing import Dict, Tuple, Set, List, Any
from collections import Counter

from google import genai
from google.genai import types

from game.colored_trails import ColoredTrails, GameState, COLORS


def read_api_key(filepath="API_token_gemini.txt"):
    # Ensure this file contains your Gemini API Key
    with open(filepath, "r") as f:
        return f.read().strip()


api_key = read_api_key()
print(f"used api key: {api_key}")


class LLMPlayer:
    def __init__(self, player_id: str, game_env: ColoredTrails):
        self.player_id = player_id
        self.opponent_id = "p2" if player_id == "p1" else "p1"
        self.game = game_env
        self.COLORS = COLORS
        self.proposed_trades: Set[Tuple[Tuple[str, ...], Tuple[str, ...]]] = set()
        self.history: List[str] = []

        try:
            self.client = genai.Client(api_key=api_key)
        except Exception as e:
            print(f"Error initializing Gemini client: {e}")
            raise

        self.model_name = "gemini-2.5-flash"

        # These are the schemas that we are using for the JSON mode of Gemini, in order to only receive a valid JSON
        self.trade_schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "give": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(type=types.Type.STRING, enum=COLORS + ["PASS"])
                ),
                "receive": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(type=types.Type.STRING, enum=COLORS + ["PASS"])
                ),
            },
            required=["give", "receive"],
        )

        self.decision_schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "action": types.Schema(type=types.Type.STRING, enum=["ACCEPT", "REJECT"])
            },
            required=["action"],
        )

    def _gen_json(self, prompt: str, schema: types.Schema) -> dict | None:
        # This function is used for the JSON mode with the made schemas for Gemini
        try:
            cfg = types.GenerateContentConfig(
                response_mime_type="application/json",  # this forces JSON
                response_schema=schema,  # this enforces the shape of our made schemas
                temperature=0,      # as told by Yftah to include for reproducability
            )
            resp = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=cfg,
            )
            return json.loads(resp.text)
        except Exception as e:
            print(f"[{self.player_id}] JSON call failed: {e}")
            return None

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

    def query_llm(self, prompt: str, stop: List[str] | None = None) -> str:
        # Queries the Gemini model with the given prompt.

        try:
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
            # If something goes wrong we will default to pass action
            print(f"[{self.player_id}] LLM call failed ({e}). Defaulting to 'Pass'.")
            return "Pass"

    def _parse_trade_response(self, text: str) -> Tuple[List[str], List[str]]:
        # Function to help extract the JSON or default to Pass
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
- {"give": ["COLOR", ...], "receive": ["COLOR", ...]}'
- If you don't need any trade, output:
- {"give": "PASS", "receive": "PASS"}
"""

        print(
            f"\n========== LLM PROMPT ({self.player_id}) ==========\n{prompt}\n==============================================\n")

        data = self._gen_json(prompt, self.trade_schema)
        # Fallback to pass action
        if not data:
            return ["Pass"], ["Pass"]

        give = data.get("give", [])
        receive = data.get("receive", [])

        def normalize(lst):
            # normalize the output
            return [str(x).upper() for x in lst if isinstance(x, str)]

        give = normalize(give)
        receive = normalize(receive)

        def is_pass_pair(g, r):
            return g == ["PASS"] and r == ["PASS"]

        # If one side says PASS, force pass
        if "PASS" in give or "PASS" in receive:
            logging.warning("PASS NOT FULLY GIVEN")
            give, receive = ["PASS"], ["PASS"]

        # Final validation against allowed tokens
        allowed = set(COLORS + ["PASS"])
        if not all(x in allowed for x in give) or not all(x in allowed for x in receive):
            logging.error("NOT ALLOWED RESPONSE GIVEN")
            return ["Pass"], ["Pass"]

        give_out = ["Pass"] if is_pass_pair(give, receive) else give
        receive_out = ["Pass"] if is_pass_pair(give, receive) else receive

        trade_key = (tuple(sorted(give_out)), tuple(sorted(receive_out)))
        self.proposed_trades.add(trade_key)
        log_msg = f"{self.player_id} proposed trade: GIVE {give_out} for RECEIVE {receive_out}"
        print(f"  [{self.player_id}] {log_msg}")
        self.history.append(log_msg)
        return give_out, receive_out


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

        data = self._gen_json(prompt, self.decision_schema)

        # Fallback if JSON failed to reject
        if not data:
            logging.error("JSON FAILED IN EVALUATION")
            action_upper = "REJECT"
        else:
            action_upper = str(data.get("action", "")).upper()
            if action_upper not in {"ACCEPT", "REJECT"}:
                action_upper = "ACCEPT" if gain > 0 else "REJECT"

        accept = action_upper == "ACCEPT"
        if accept:
            print(f"  [{self.player_id}] LLM decision: ACCEPT")
            self.history.append(f"{self.player_id} ACCEPTED offer ({opp_give} for {opp_receive}).")
        else:
            print(f"  [{self.player_id}] LLM decision: REJECT")
            self.history.append(f"{self.player_id} REJECTED offer ({opp_give} for {opp_receive}).")
        return accept
