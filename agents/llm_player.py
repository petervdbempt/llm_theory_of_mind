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
    LLM-backed player. Mirrors GreedyPlayer structure but asks an LLM to:
      - Propose a trade when it's this agent's turn.
      - Accept/Reject a proposal when evaluating an opponent offer.

    The prompt includes:
      - Your current chips
      - A list of legal candidate trades and *their precomputed utilities/gains* for this agent
      - Negotiation history (previous proposals/decisions)
    """

    def __init__(self, player_id: str, game_env: ColoredTrails):
        self.player_id = player_id
        self.opponent_id = "p2" if player_id == "p1" else "p1"
        self.game = game_env
        self.COLORS = COLORS
        self.proposed_trades: Set[Tuple[str, str]] = set()
        self.history: List[str] = []
        # Use the same client pattern you provided
        self.client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=api_key)

    # -- Utility calculation reused from greedy_player approach --
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

    # -- LLM query wrapper using your conversational style fallback logic --
    def query_llm(self, prompt: str, max_tokens: int = 256, stop: List[str] | None = None) -> str:
        try:
            _prompt = [{"role": "user", "content": prompt}]
            response = self.client.chat_completion(
                _prompt,
                max_tokens=max_tokens,
                stop=stop or ["\n\n"]
            )
            # depends on response shape; adapt defensively
            return response.choices[0].message.content.strip()
        except Exception as e:
            # fallback to conversational API if chat fails
            if "not supported" in str(e).lower() and "conversational" in str(e).lower():
                try:
                    conv = self.client.conversational(prompt)
                    return conv.generated_text.strip()
                except Exception as inner_e:
                    print(f"[{self.player_id}] Conversational fallback failed ({inner_e}). Defaulting to 'Pass'.")
                    return "Pass"
            print(f"[{self.player_id}] LLM call failed ({e}). Defaulting to 'Pass'.")
            return "Pass"

    # -- Parse LLM response for trade proposal (accept multiple formats) --
    def _parse_trade_response(self, text: str, legal_trades: List[Tuple[str, str]]) -> Tuple[str, str, str]:
        """
        Returns (give, receive, reasoning)
        If pass: returns ("Pass","Pass", reasoning)
        """
        text_raw = (text or "").strip()
        text_upper = text_raw.upper()

        # Try JSON first ({"action": {"give": "...", "receive": "..."}, "reasoning":"..."})
        try:
            parsed = json.loads(text_raw)
            action = parsed.get("action")
            reasoning = parsed.get("reasoning", "")
            if isinstance(action, dict):
                give = action.get("give", "Pass")
                receive = action.get("receive", "Pass")
                return give, receive, reasoning
            if isinstance(action, str) and action.upper() == "PASS":
                return "Pass", "Pass", reasoning
        except Exception:
            pass

        # If response contains PASS
        if "PASS" in text_upper:
            # extract possible appended reasoning
            return "Pass", "Pass", text_raw

        # Try tuple-like e.g. (BROWN, YELLOW) or "BROWN for YELLOW"
        legal_set = set(legal_trades)
        # normalize text for searching
        normalized = text_upper.replace("'", "").replace('"', "")
        # Look for "FOR" pattern
        if " FOR " in normalized:
            parts = [p.strip() for p in normalized.split(" FOR ")]
            if len(parts) >= 2:
                give = parts[0].strip().title()
                receive = parts[1].split()[0].strip().title()
                if (give, receive) in legal_set:
                    return give, receive, text_raw

        # Look for words matching a legal pair
        for give, recv in legal_set:
            if give.upper() in normalized and recv.upper() in normalized:
                return give, recv, text_raw

        # Last resort: pick the best trade by utility if available in legal_trades
        if legal_trades:
            # choose random fallback but also provide reasoning that LLM response couldn't be parsed
            fallback = random.choice(legal_trades)
            return fallback[0], fallback[1], f"Could not parse LLM response. Fallback to {fallback}."

        return "Pass", "Pass", "Could not parse LLM response."

    # -- Build list of legal trades with precomputed utility gains --
    def _compute_candidate_trades_with_gain(self) -> List[Dict[str, Any]]:
        my_chips = self.game.states[self.player_id].chips
        if not my_chips:
            return []

        current_utility = self.calculate_utility(dict(my_chips))
        candidates = []

        for give in list(my_chips.keys()):
            if my_chips[give] == 0:
                continue
            for receive in self.COLORS:
                if give == receive:
                    continue
                trade = (give, receive)
                if trade in self.proposed_trades:
                    continue
                # simulate
                hypo = dict(my_chips)
                hypo[give] -= 1
                if hypo[give] == 0:
                    del hypo[give]
                hypo[receive] = hypo.get(receive, 0) + 1
                new_util = self.calculate_utility(dict(hypo))
                gain = new_util - current_utility
                candidates.append({"give": give, "receive": receive, "gain": gain})
        return candidates

    # -- Proposer API: propose_trade() --
    def propose_trade(self) -> Tuple[str, str]:
        my_chips = self.game.states[self.player_id].chips
        if not my_chips:
            print(f"  [{self.player_id}] No chips to trade.")
            return "Pass", "Pass"

        candidates = self._compute_candidate_trades_with_gain()

        # Filter for positive gains only and sort by utility (descending)
        candidates = [c for c in candidates if c["gain"] > 0]
        candidates.sort(key=lambda x: x["gain"], reverse=True)

        if not candidates:
            print(f"  [{self.player_id}] No candidate trades with positive gain (or all previously proposed). Passing.")
            return "Pass", "Pass"

        # prepare a compact legal_trades for parsing/fallback
        legal_trades = [(c["give"], c["receive"]) for c in candidates]

        # Build prompt (includes possible trades + their gains and history)
        prompt = (
            f"You are Player {self.player_id.upper()} in the Colored Trails negotiation.\n"
            f"Your current chips: {dict(self.game.states[self.player_id].chips)}\n"
            f"Your goal: {self.game.states[self.player_id].goal_pos}\n"
            f"Your current utility (precomputed): {self.calculate_utility(dict(self.game.states[self.player_id].chips))}\n\n"
            "Below are legal candidate one-for-one trades and their precomputed utility GAIN if you propose that trade:\n"
            f"{json.dumps(candidates, indent=2)}\n\n"
            "Negotiation history (most recent last):\n"
            f"{chr(10).join(self.history) if self.history else '(none)'}\n\n"
            "Choose ONE trade to PROPOSE that maximizes your expected final outcome, taking into account that "
            "the opponent may accept or reject.\n"
            "If possible, use theory of mind based on the history of previous moves.\n"
            "Return a valid JSON like:\n"
            '{"action": {"give": "BROWN", "receive": "YELLOW"}, "reasoning": "your reasoning"}\n'
            "Respond ONLY with your chosen action plus reasoning."
        )

        print(
            f"\n========== LLM PROMPT ({self.player_id}) ==========\n{prompt}\n==============================================\n")

        llm_output = self.query_llm(prompt, max_tokens=256, stop=["\n\n"])
        give, receive, reasoning = self._parse_trade_response(llm_output, legal_trades)

        # # Normalize Pass
        # if give == "Pass" and receive == "Pass":
        #     print(f"  [{self.player_id}] LLM chose to PASS. Reasoning: {reasoning}")
        #     self.history.append(f"{self.player_id} PASSED (reason: {reasoning})")
        #     return "Pass", "Pass"

        # record proposed trade to avoid repetition
        self.proposed_trades.add((give, receive))
        log_msg = f"{self.player_id} proposed trade: GIVE {give} for RECEIVE {receive}"
        print(f"  [{self.player_id}] {log_msg}. Reasoning: {reasoning}")
        self.history.append(log_msg)
        return give, receive

    # -- Responder API: evaluate_proposal() --
    def evaluate_proposal(self, proposal: Tuple[str, str]) -> bool:
        opp_give, opp_receive = proposal
        my_state = self.game.states[self.player_id]

        if opp_give == "Pass":
            self.history.append(f"{self.opponent_id} PASSED")
            return True

        # Quick sanity check: if we don't have the requested chip, can't accept
        if my_state.chips.get(opp_receive, 0) < 1:
            print(f"  [{self.player_id}] Cannot accept - missing {opp_receive}")
            self.history.append(
                f"{self.opponent_id} proposed {opp_give} for {opp_receive}. {self.player_id} REJECT")
            return False

        # compute utility change
        current_util = self.calculate_utility(dict(my_state.chips))
        hypo = dict(my_state.chips)
        hypo[opp_give] = hypo.get(opp_give, 0) + 1
        hypo[opp_receive] -= 1
        if hypo[opp_receive] == 0:
            del hypo[opp_receive]
        new_util = self.calculate_utility(dict(hypo))
        gain = new_util - current_util

        prompt = (
            f"You are Player {self.player_id.upper()} evaluating a proposed trade.\n"
            f"Your chips: {dict(my_state.chips)}\n"
            f"Your goal: {my_state.goal_pos}\n"
            f"Current utility (precomputed): {current_util}\n"
            f"Offer: Opponent will GIVE you {opp_give} and wants {opp_receive} in return.\n"
            f"If accepted, your new utility would be {new_util} (gain = {gain}).\n\n"
            "History (most recent last):\n"
            f"{chr(10).join(self.history) if self.history else '(none)'}\n\n"
            "Decide whether to ACCEPT or REJECT the trade.\n"
            'Respond with JSON: {"action": "ACCEPT" or "REJECT", "reasoning": "your reasoning here"}.'
        )

        print(
            f"\n========== LLM PROMPT ({self.player_id}) ==========\n{prompt}\n==============================================\n")

        llm_output = self.query_llm(prompt, max_tokens=180, stop=["\n\n"]).strip()
        out_upper = llm_output.upper()

        # default parse: JSON then plain words
        try:
            parsed = json.loads(llm_output)
            action = parsed.get("action", "")
            reasoning = parsed.get("reasoning", "")
            if isinstance(action, str):
                action_upper = action.upper()
            else:
                action_upper = str(action).upper()
        except Exception:
            # fallback: look for words
            reasoning = llm_output
            if "ACCEPT" in out_upper and "REJECT" not in out_upper:
                action_upper = "ACCEPT"
            elif "REJECT" in out_upper and "ACCEPT" not in out_upper:
                action_upper = "REJECT"
            else:
                # if neither clear, decide based on utility: accept if gain>0, else reject
                action_upper = "ACCEPT" if gain > 0 else "REJECT"
                reasoning += f" (ambiguous LLM output, fallback to utility: gain={gain})"

        accept = action_upper == "ACCEPT"

        if accept:
            print(f"  [{self.player_id}] LLM decision: ACCEPT. Reasoning: {reasoning}")
            self.history.append(f"{self.player_id} ACCEPTED offer ({opp_give} for {opp_receive}).")
        else:
            print(f"  [{self.player_id}] LLM decision: REJECT. Reasoning: {reasoning}")
            self.history.append(f"{self.player_id} REJECTED offer ({opp_give} for {opp_receive}).")

        return accept
