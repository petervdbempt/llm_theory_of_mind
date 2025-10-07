import random
from typing import Dict, Tuple, Set
from game.colored_trails import ColoredTrails, GameState, COLORS
from huggingface_hub import InferenceClient


class LLMPlayer:
    """
    Player that uses an Instruct LLM (via Hugging Face) to decide on trades.

    It generates natural-language reasoning to propose or evaluate trades,
    but we enforce legality and structure of the output.
    """

    def __init__(self, player_id: str, game_env: ColoredTrails):
        self.player_id = player_id
        self.opponent_id = "p2" if player_id == "p1" else "p1"
        self.game = game_env
        self.COLORS = COLORS
        self.proposed_trades: Set[Tuple[str, str]] = set()
        # Initialize Llama inference client
        # NOTE: This model may be automatically routed to a provider (like fireworks-ai)
        # that restricts the task type. We will use 'conversational' to ensure compatibility.
        self.client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct")

    # -------------------------------------------------------------------------
    # Helper: Call the LLM with a structured prompt
    # -------------------------------------------------------------------------
    def query_llm(self, prompt: str) -> str:
        """
        Query the Llama model, adapting the call to use the 'conversational' task
        if 'text-generation' is not supported by the hosting provider.
        """
        try:
            # We use text_generation, but ensure we use the supported 'stop' argument.
            # NOTE: If the LLM call still fails, it may be necessary to switch to
            # client.conversational(prompt) and parse the resulting Conversation object,
            # or ensure the environment/API key is configured for a provider
            # that supports the generic text_generation task for this model.

            # The current error suggests the provider handles Llama 3.1 only via chat endpoints.
            # We will use the chat-optimized `text_generation` call structure:
            response_text = self.client.text_generation(
                prompt,
                max_new_tokens=128,
                temperature=0.4,
                top_p=0.9,
                # Use 'stop' instead of the deprecated 'stop_sequences'
                stop=["\n", "}", ")"],
            )
            return response_text.strip()

        except Exception as e:
            # The previous error indicated 'conversational' is available.
            # Let's try the conversational method as a fallback if the text_generation
            # attempt fails again due to routing/task mismatch.
            if "not supported" in str(e).lower() and "conversational" in str(e).lower():
                print(f"[{self.player_id}] Text-generation failed. Falling back to conversational task.")
                try:
                    # The conversational method takes a simple string and returns a Conversation object
                    conversation = self.client.conversational(prompt)
                    return conversation.generated_text.strip()
                except Exception as inner_e:
                    print(f"[{self.player_id}] Conversational call also failed ({inner_e}). Defaulting to 'Pass'.")
                    return "Pass"

            # For all other exceptions
            print(f"[{self.player_id}] LLM call failed ({e}). Defaulting to 'Pass'.")
            return "Pass"

    # -------------------------------------------------------------------------
    # Core logic: Proposal
    # -------------------------------------------------------------------------
    def propose_trade(self) -> Tuple[str, str]:
        """
        Use LLM reasoning to select a trade (Give_Chip, Receive_Chip) or ("Pass","Pass").
        The agent is guided to propose trades that help it reach its goal position.
        """

        current_chips = self.game.states[self.player_id].chips
        if not current_chips:
            print(f"  [{self.player_id}] No chips to trade.")
            return "Pass", "Pass"

        # Build list of *legal* candidate trades (give, receive)
        legal_trades = [
            (give, recv)
            for give in current_chips.keys()
            for recv in self.COLORS
            if give != recv and (give, recv) not in self.proposed_trades
        ]
        if not legal_trades:
            print(f"  [{self.player_id}] No legal trades remaining.")
            return "Pass", "Pass"

        # Prepare prompt for the LLM
        game = self.game
        my_state = game.states[self.player_id]
        opp_state = game.states[self.opponent_id]

        prompt = f"""
You are an intelligent negotiation agent playing the game Colored Trails.

Game rules summary:
- The board is a {len(game.board)}x{len(game.board)} grid of colors: {', '.join(self.COLORS)}.
- Each step costs 1 chip of the destination's color.
- You start at {my_state.current_pos} and want to reach your goal at {my_state.goal_pos}.
- You currently have chips: {dict(my_state.chips)}.
- Your opponent has chips: {dict(opp_state.chips)}.
- A legal trade means: you give one chip you have, and receive one chip from the set of colors {self.COLORS}.
- You may pass if no trade helps you get closer to your goal.

Your objective: maximize your ability to reach your goal (reduce distance, keep useful chips).

You can choose one of these possible trades:
{legal_trades}

Respond **only** with one of the tuples from above (e.g., ('BROWN','YELLOW')) or "Pass".
Which trade do you choose?
        """.strip()

        llm_output = self.query_llm(prompt)
        parsed = self._parse_llm_trade(llm_output, legal_trades)

        if parsed == ("Pass", "Pass"):
            print(f"  [{self.player_id}] LLM chose to pass.")
            return parsed

        # Record and announce
        self.proposed_trades.add(parsed)
        print(f"  [{self.player_id}] LLM proposed trade: Give {parsed[0]} for {parsed[1]}")
        return parsed

    # -------------------------------------------------------------------------
    # Core logic: Evaluation
    # -------------------------------------------------------------------------
    def evaluate_proposal(self, proposal: Tuple[str, str]) -> bool:
        """
        Ask LLM whether to accept a trade offered by the opponent.
        The proposal is (opponent_give, opponent_receive).
        """
        opp_give, opp_receive = proposal
        my_state = self.game.states[self.player_id]
        opp_state = self.game.states[self.opponent_id]

        if opp_give == "Pass":
            # Pass doesn't require evaluation logic
            return True

        # Construct a structured prompt
        prompt = f"""
You are a rational agent evaluating a trade in the game Colored Trails.

You currently have chips: {dict(my_state.chips)}.
Your goal position is {my_state.goal_pos}.
The opponent offers to GIVE you one {opp_give} chip,
but asks for one {opp_receive} chip in return.

Game reminder:
- You can only accept if you have at least one {opp_receive} chip.
- Accept only if it improves your chance to reach your goal (better color coverage, closer to goal).

Respond strictly with "ACCEPT" or "REJECT".
        """.strip()

        llm_output = self.query_llm(prompt).upper()

        # Apply legality check
        if my_state.chips.get(opp_receive, 0) < 1:
            print(f"  [{self.player_id}] Cannot accept — missing {opp_receive}")
            return False

        if "ACCEPT" in llm_output and "REJECT" not in llm_output:
            print(f"  [{self.player_id}] LLM accepts the trade.")
            return True
        else:
            print(f"  [{self.player_id}] LLM rejects the trade.")
            return False

    # -------------------------------------------------------------------------
    # Parsing helper
    # -------------------------------------------------------------------------
    def _parse_llm_trade(self, text: str, legal_trades: list[Tuple[str, str]]) -> Tuple[str, str]:
        """Extract a valid (give, receive) tuple from the LLM response text."""
        # Convert list of tuples to a set for fast lookup
        legal_set = set(legal_trades)

        text = text.strip().upper().replace('"', "").replace("'", "")

        # 1. Check for explicit PASS
        if "PASS" in text:
            return ("Pass", "Pass")

        # 2. Try to find a matching tuple in the text
        for give, recv in legal_set:
            # Check for the literal tuple string format, or just the two words
            if f"({give},{recv})" in text.replace(" ", "") or (give in text and recv in text):
                return (give, recv)

        # 3. Fallback: choose a random legal trade to avoid stalling
        print(f"  [{self.player_id}] Could not parse LLM output '{text}', choosing randomly.")
        # Ensure legal_trades is not empty before calling random.choice
        if legal_trades:
            return random.choice(legal_trades)

        return ("Pass", "Pass")
