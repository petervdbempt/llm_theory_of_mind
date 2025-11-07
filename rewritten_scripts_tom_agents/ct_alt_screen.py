# ct_controller.py
# Headless controller for Colored Trails using the previously ported CTgame/Agent utilities.

import random
from typing import List, Tuple, Dict, Any

# Bring in your earlier ports:
# from ct_helpers import convertCode, convertChips, getChipDifference, invertCode, getNumberOfTokens
# from ct_game import CTgame
# from tom_agents import Agent

# If they live in the same module, just import them accordingly.


class CTRunner:
    """
    Headless controller for the CT game.

    Mirrors the logic of the last JS file:
      - game setup (init/reset)
      - round loop (play_round)
      - human or agent offers (process, accept, withdraw)
      - accuracy/score bookkeeping

    UI/DOM has been removed; return dicts describing state changes instead.
    """

    def __init__(self, agent_orders: Tuple[int, int] = (2, 2), seed: int | None = None):
        """
        agent_orders: (initiator_order, responder_order), e.g., (2,2)
        """
        if seed is not None:
            random.seed(seed)

        # Visual/UI-related flags from JS kept as attributes for completeness
        self.boardColors: List[str] = ["white", "black", "purple", "gray", "yellow"]
        self.revealGoals: bool = False
        self.showOfferHelper: bool = False

        # Goal location indices (kept for parity but only needed if you visualize)
        self.goalLocationArray: List[int] = [0, 1, 3, 4, 5, 9, 15, 19, 20, 21, 23, 24]

        # Game objects
        self.ct = CTgame()

        # agents[side][order_index] where order_index 0,1,2 -> ToM0, ToM1, ToM2
        self.agents: List[List[Agent]] = [
            [Agent(0, 0), Agent(1, 0), Agent(2, 0)],
            [Agent(0, 1), Agent(1, 1), Agent(2, 1)],
        ]

        # Which agent level is active per side (human uses -1 like JS)
        self.agentLevels: List[int] = [agent_orders[0], agent_orders[1]]

        # Round state
        self.round: int = -1
        self.currentOffer: int = -1  # encoded offer last made (flipped to "view from initiator" in JS)
        self.scores: List[int] = [0, 0]

        # Accuracy tracking (for ToM1/ToM2, initiator & responder)
        self.accuracies: List[float] = [0.0, 0.0, 0.0, 0.0]  # [init_ToM1, init_ToM2, resp_ToM1, resp_ToM2]
        self.totalRounds: List[int] = [0, 0]  # [rounds_seen_by_initiator, rounds_seen_by_responder]

    # -------------------------
    # Setup & reset
    # -------------------------

    def reset_game(self):
        """Reset scores and accuracy counters; then init a new game."""
        self.scores = [0, 0]
        self.accuracies = [0.0, 0.0, 0.0, 0.0]
        self.totalRounds = [0, 0]
        return self.init_game()

    def init_game(self) -> Dict[str, Any]:
        """
        Initialize a new CT board and (re)initialize agents on it.
        Returns a dict with initial state.
        """
        self.ct.init()

        # Initialize all agent models with the new game and set their *own* location.
        # JS had a small bug here (passed an array). We pass ints correctly.
        for i in range(len(self.agents[0])):
            self.agents[0][i].init(self.ct, 0)
            self.agents[0][i].setLocation(self.ct.locations[0])
            self.agents[1][i].init(self.ct, 1)
            self.agents[1][i].setLocation(self.ct.locations[1])

        self.round = 0
        self.currentOffer = -1

        return {
            "round": self.round,
            "locations": tuple(self.ct.locations),
            "chipSets": tuple(self.ct.chipSets),
            "binMax": list(self.ct.binMax),
        }

    # -------------------------
    # Human interaction helpers
    # -------------------------

    def process_human_offer(self, new_offer_for_other: int) -> Dict[str, Any]:
        """
        Process a human-made offer. The human is the current player (self.round % 2).
        new_offer_for_other: offer code the human SENDS TO THE OTHER player (same convention as JS in playRound).

        Side effects:
          - all agents observe send/receive
          - accuracies updated
          - history-equivalent info returned
        """
        cur = self.round % 2  # current player making the offer
        other = 1 - cur

        # Notify agents (mirrors processHumanOffer in JS)
        for i in range(len(self.agents[cur])):
            self.agents[cur][i].sendOffer(self.ct, new_offer_for_other)
            self.agents[other][i].receiveOffer(self.ct, self.ct.flipArray[new_offer_for_other])

        # Update accuracies for the side that *received* the offer
        # (JS adds responder's lastAccuracy from ToM1 and ToM2)
        self.accuracies[2 * other + 0] += self.agents[other][1].lastAccuracy
        self.accuracies[2 * other + 1] += self.agents[other][2].lastAccuracy
        self.totalRounds[other] += 1

        # In the UI, they "showOffer" with a flipped perspective; we return both views
        return {
            "offered_by": cur,
            "offer_to_other": new_offer_for_other,
            "offer_to_self_view": self.ct.flipArray[new_offer_for_other],
        }

    def accept_offer(self) -> Dict[str, Any]:
        """
        Human accepts currentOffer (the previous offer made *to* them).
        Apply end of game scoring.
        """
        # In JS acceptOffer flips currentOffer depending on side; we compute the actual offer to score with.
        # The game ends with the last valid bilateral split applied from the initiator's perspective:
        offer_for_scoring = self.currentOffer if (self.round % 2 == 0) else self.ct.flipArray[self.currentOffer]
        state = self.end_game(offer_for_scoring)
        return {"action": "accept", **state}

    def withdraw_offer(self) -> Dict[str, Any]:
        """
        Human withdraws — equivalent to sending your current chip set to the other player.
        """
        cur = self.round % 2
        withdraw_code = self.ct.chipSets[1 - cur]
        self.process_human_offer(withdraw_code)
        # JS ends with ct.chipSets[0] scoring (status quo)
        state = self.end_game(self.ct.chipSets[0])
        return {"action": "withdraw", **state}

    # -------------------------
    # Round playing (AI or human)
    # -------------------------

    def make_human_offer(self, bins_for_side_id: int) -> Dict[str, Any]:
        """
        Human composes an offer by bins (vector) for the panel "side_id" (0 = left/initiator view, like JS).
        We encode it and transform to 'offer-to-other' perspective like JS.
        """
        from math import prod  # only used if you decide to re-validate radix length

        # Encode bins to offer code
        offer_code = convertChips(bins_for_side_id, self.ct.binMax)  # you likely have bins already consistent with binMax
        new_offer = self.ct.flipArray[offer_code]  # human sends to other

        # If identical to previous opponent offer -> accept
        if new_offer == self.ct.flipArray[self.currentOffer]:
            return self.accept_offer()

        # If it's a withdraw -> withdraw
        cur = self.round % 2
        if new_offer == self.ct.chipSets[1 - cur]:
            return self.withdraw_offer()

        # Otherwise proceed as a new offer
        info = self.process_human_offer(new_offer)
        self.round += 1
        self.currentOffer = new_offer
        return {"action": "human_offer", **info, "round": self.round}

    def play_round(self) -> Dict[str, Any]:
        """
        Play one round:
          - If game not started, initialize it
          - Active agent selects an offer
          - Everyone observes
          - Check end conditions (accept / withdraw / max rounds)
        Returns a dict describing what happened in the round or the game end state.
        """
        if self.round < 0:
            # JS restarts if game ended and playRound is called again
            return self.init_game()

        cur = self.round % 2
        other = 1 - cur
        level = self.agentLevels[cur]
        if level < 0:
            # Human turn; in headless mode we cannot auto-play human.
            # You can call make_human_offer/accept_offer/withdraw_offer externally.
            return {
                "turn": cur,
                "status": "awaiting_human",
                "round": self.round,
                "currentOffer": self.currentOffer,
            }

        # Agent chooses an offer to make TO OTHER (same as JS selectOffer)
        new_offer_to_other = self.agents[cur][level].selectOffer(self.ct, self.currentOffer)

        # Notify all agents of the send/receive (mirrors playRound body)
        for i in range(len(self.agents[cur])):
            self.agents[cur][i].sendOffer(self.ct, new_offer_to_other)
            self.agents[other][i].receiveOffer(self.ct, self.ct.flipArray[new_offer_to_other])
            if self.revealGoals:
                self.agents[0][i].informLocation(self.ct)
                self.agents[1][i].informLocation(self.ct)

        # Update accuracies for the receiving side
        self.accuracies[2 * other + 0] += self.agents[other][1].lastAccuracy
        self.accuracies[2 * other + 1] += self.agents[other][2].lastAccuracy
        self.totalRounds[other] += 1

        # For continuity with JS visualization, flip to "public/current" view
        new_offer_public = self.ct.flipArray[new_offer_to_other]

        # End conditions:
        # 1) If new_offer_public equals previous currentOffer (mutual acceptance), end with that split.
        if new_offer_public == self.ct.flipArray[self.currentOffer]:
            # Score with initiator-perspective selection:
            scoring_offer = self.currentOffer if (cur == 0) else new_offer_public
            end = self.end_game(scoring_offer)
            return {"action": "accepted", **end}

        # 2) Withdraw or too many rounds (> 38)
        if new_offer_public == self.ct.chipSets[1 - cur] or self.round > 38:
            end = self.end_game(self.ct.chipSets[0])
            return {"action": "withdraw_or_timeout", **end}

        # Otherwise continue
        self.round += 1
        self.currentOffer = new_offer_public
        return {
            "action": "agent_offer",
            "offered_by": cur,
            "offer_to_public_view": new_offer_public,
            "round": self.round,
        }

    # -------------------------
    # End & scoring
    # -------------------------

    def end_game(self, offer_from_initiator_view: int) -> Dict[str, Any]:
        """
        Apply final scoring and mark game ended.
        `offer_from_initiator_view` must be the split as seen from initiator’s perspective,
        exactly as the JS did in endGame(offer).
        """
        # Initiator gets utility at their location for 'offer'
        self.scores[0] += self.ct.utilityFunction[self.ct.locations[0]][offer_from_initiator_view]
        # Responder gets utility for the flipped offer
        self.scores[1] += self.ct.utilityFunction[self.ct.locations[1]][self.ct.flipArray[offer_from_initiator_view]]

        # Mark as ended
        self.round = -1

        return {
            "round": self.round,
            "final_offer_initiator_view": offer_from_initiator_view,
            "scores": tuple(self.scores),
            "locations": tuple(self.ct.locations),
        }
