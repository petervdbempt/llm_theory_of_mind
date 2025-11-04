import random
from typing import Dict, List, Tuple, Optional
from collections import Counter
from game.colored_trails import ColoredTrails, GameState, COLORS, BOARD_SIZE
from utils.text_logger import TextLogger


class ToM0Model:
    """
    Order 0 Theory of Mind: Basic statistical learner.
    Learns acceptance rates for different offer types based on observed negotiations.
    """

    def __init__(self, player_id: str, learning_speed: float = 0.8, logger: TextLogger | None = None):
        self.player_id = player_id
        self.opponent_id = "p2" if player_id == "p1" else "p1"
        self.learning_speed = learning_speed
        self.logger = logger

        # Statistics: [chips_given][chips_received] -> counts
        # Max 8 chips given/received (since each player starts with 4)
        self.cnt_beliefs = [[5.0] * 9 for _ in range(9)]  # Accepted offers
        self.ttl_beliefs = [[5.0] * 9 for _ in range(9)]  # Total offers

        # Initialize with some prior beliefs (Laplace smoothing)
        # Mimics the JS initialization with slight bias toward balanced trades
        for i in range(9):
            for j in range(9):
                if i <= 4 and j <= 4:
                    self.ttl_beliefs[i][j] = 20.0
                    # Favor balanced trades slightly
                    if abs(i - j) <= 1:
                        self.cnt_beliefs[i][j] = 15.0
                    else:
                        self.cnt_beliefs[i][j] = 8.0

    def _log(self, msg: str):
            if self.logger:
                self.logger.log(f"[{self.player_id}] {msg}")
            else:
                print(f"[{self.player_id}] {msg}")
                
    def _count_chip_difference(self, current_chips: Dict[str, int],
                               new_chips: Dict[str, int]) -> Tuple[int, int]:
        """
        Calculate how many chips are gained vs lost.
        Returns (chips_gained, chips_lost)
        """
        gained = 0
        lost = 0

        all_colors = set(current_chips.keys()) | set(new_chips.keys())
        for color in all_colors:
            diff = new_chips.get(color, 0) - current_chips.get(color, 0)
            if diff > 0:
                gained += diff
            else:
                lost += abs(diff)

        return gained, lost

    def get_acceptance_rate(self, game: ColoredTrails,
                            offer_give: List[str], offer_receive: List[str]) -> float:
        """
        Returns believed probability that an offer will be accepted.
        """
        current_chips = dict(game.states[self.player_id].chips)

        # Simulate the chip change
        temp_chips = current_chips.copy()
        for chip in offer_give:
            temp_chips[chip] = temp_chips.get(chip, 0) - 1
        for chip in offer_receive:
            temp_chips[chip] = temp_chips.get(chip, 0) + 1

        gained, lost = self._count_chip_difference(current_chips, temp_chips)

        # Ensure indices are within bounds
        gained = min(gained, 8)
        lost = min(lost, 8)

        return self.cnt_beliefs[gained][lost] / self.ttl_beliefs[gained][lost]

    def observe(self, game: ColoredTrails, offer_give: List[str],
                offer_receive: List[str], is_accepted: bool, proposer_id: str):
        """
        Update beliefs based on observed offer acceptance/rejection.
        """
        current_chips = dict(game.states[self.player_id].chips)
        temp_chips = current_chips.copy()

        for chip in offer_give:
            temp_chips[chip] = temp_chips.get(chip, 0) - 1
        for chip in offer_receive:
            temp_chips[chip] = temp_chips.get(chip, 0) + 1

        gained, lost = self._count_chip_difference(current_chips, temp_chips)
        gained = min(gained, 8)
        lost = min(lost, 8)

        self.ttl_beliefs[gained][lost] += 1

        # Update acceptance count if:
        # - Opponent made the offer (always counts as signal)
        # - We made the offer and it was accepted
        if proposer_id != self.player_id or is_accepted:
            self.cnt_beliefs[gained][lost] += 1

    def get_expected_value(self, game: ColoredTrails,
                           offer_give: List[str], offer_receive: List[str]) -> float:
        """
        Calculate expected utility change from making this offer.
        """
        acceptance_rate = self.get_acceptance_rate(game, offer_give, offer_receive)

        # Calculate utility if accepted
        current_score, _, _ = game.get_max_score_and_path(self.player_id)

        # Simulate chip state after trade
        temp_chips = dict(game.states[self.player_id].chips)
        for chip in offer_give:
            if temp_chips.get(chip, 0) <= 0:
                return -999  # Invalid
            temp_chips[chip] -= 1
            if temp_chips[chip] == 0:
                del temp_chips[chip]
        for chip in offer_receive:
            temp_chips[chip] = temp_chips.get(chip, 0) + 1

        temp_state = GameState(game.states[self.player_id].goal_pos, temp_chips)
        temp_game = ColoredTrails(game.board, {
            self.player_id: temp_state,
            self.opponent_id: game.states[self.opponent_id]
        })
        new_score, _, _ = temp_game.get_max_score_and_path(self.player_id)

        utility_gain = new_score - current_score - 1  # -1 for negotiation cost

        # Expected value: P(accept) * utility_if_accept + P(reject) * utility_if_reject
        # If rejected, we lose 1 point from making the offer
        expected = acceptance_rate * utility_gain + (1 - acceptance_rate) * (-1)

        return expected


class ToMAgent:
    """
    Theory of Mind agent with recursive opponent modeling.
    Order 0: Statistical learner (ToM0Model)
    Order N: Recursive reasoning about Order N-1 opponent
    """

    def __init__(self, player_id: str, game_env: ColoredTrails, order: int = 1, learning_speed: float = 0.8, logger: TextLogger | None = None ):
        self.player_id = player_id
        self.opponent_id = "p2" if player_id == "p1" else "p1"
        self.game = game_env
        self.order = order
        self.learning_speed = learning_speed
        self.confidence = 1.0  # Confidence in current order reasoning
        self.history: List[str] = []
        self.logger = logger
        

        if order > 0:
            # Higher order: maintain opponent model and self model
            self.opponent_model = ToMAgent(self.opponent_id, game_env, order - 1, learning_speed)
            self.opponent_model.confidence = 1.0  # Lock confidence for simulations
            self.self_model = ToMAgent(player_id, game_env, order - 1, learning_speed)

            # Beliefs about opponent's goal location
            self.location_beliefs = {}
            self._init_location_beliefs()
        else:
            # Order 0: use statistical model
            self.base_model = ToM0Model(player_id, learning_speed)
            
    def _log(self, msg: str):
        if self.logger:
            self.logger.log(f"[{self.player_id}] {msg}")
        else:
            print(f"[{self.player_id}] {msg}")

    def _init_location_beliefs(self):
        """Initialize uniform beliefs about opponent location."""
        self.location_beliefs = {}
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                self.location_beliefs[(r, c)] = 1.0 / (BOARD_SIZE * BOARD_SIZE)

    def _get_all_possible_offers(self) -> List[Tuple[List[str], List[str]]]:
        """
        Generate all reasonable trade offers.
        Limit to single-chip and two-chip exchanges for tractability.
        ONLY generates offers where opponent has the requested chips.
        """
        my_chips = self.game.states[self.player_id].chips
        opp_chips = self.game.states[self.opponent_id].chips

        offers = []

        # Pass option
        offers.append((["Pass"], ["Pass"]))

        # Single chip trades (1-for-1)
        for my_color in my_chips:
            for opp_color in opp_chips:
                offers.append(([my_color], [opp_color]))

        # Two-for-one trades (give 2, receive 1)
        my_colors = list(my_chips.elements())
        if len(my_colors) >= 2:
            seen = set()
            for i, c1 in enumerate(my_colors):
                for j, c2 in enumerate(my_colors):
                    if i <= j:  # Avoid duplicates
                        give_pair = [c1, c2]
                        key = tuple(sorted(give_pair))
                        if key not in seen:
                            seen.add(key)
                            # Only request chips opponent actually has
                            for opp_color in opp_chips:
                                offers.append((give_pair, [opp_color]))

        # One-for-two trades (give 1, receive 2)
        opp_colors = list(opp_chips.elements())
        if len(opp_colors) >= 2:
            for my_color in my_chips:
                seen = set()
                for i, c1 in enumerate(opp_colors):
                    for j, c2 in enumerate(opp_colors):
                        if i <= j:  # Avoid duplicates
                            receive_pair = [c1, c2]
                            key = tuple(sorted(receive_pair))

                            # Check if opponent actually HAS both chips
                            temp_opp = Counter(opp_chips)
                            can_give = True
                            for chip in receive_pair:
                                if temp_opp[chip] <= 0:
                                    can_give = False
                                    break
                                temp_opp[chip] -= 1

                            if can_give and key not in seen:
                                seen.add(key)
                                offers.append(([my_color], receive_pair))

        return offers

    def get_value(self, offer_give: List[str], offer_receive: List[str]) -> float:
        """
        Calculate expected value of making an offer.
        """
        # Check if offer improves our position
        current_score, _, _ = self.game.get_max_score_and_path(self.player_id)

        temp_chips = dict(self.game.states[self.player_id].chips)
        for chip in offer_give:
            if temp_chips.get(chip, 0) <= 0:
                return -999  # Invalid offer - we don't have this chip
            temp_chips[chip] -= 1
            if temp_chips[chip] == 0:
                del temp_chips[chip]
        for chip in offer_receive:
            temp_chips[chip] = temp_chips.get(chip, 0) + 1

        temp_state = GameState(self.game.states[self.player_id].goal_pos, temp_chips)
        temp_game = ColoredTrails(self.game.board, {
            self.player_id: temp_state,
            self.opponent_id: self.game.states[self.opponent_id]
        })
        new_score, _, _ = temp_game.get_max_score_and_path(self.player_id)

        if new_score <= current_score:
            return -1  # Not beneficial for us

        if self.order == 0:
            return self.base_model.get_expected_value(self.game, offer_give, offer_receive)

        # Higher order: simulate opponent's response
        # We'll use a simplified model: just check if trade helps opponent at their ACTUAL location

        opp_chips = dict(self.game.states[self.opponent_id].chips)

        # Validate opponent has the chips we want
        opp_check = Counter(opp_chips)
        for chip in offer_receive:
            if opp_check[chip] <= 0:
                return -999  # They don't have what we want
            opp_check[chip] -= 1

        # Calculate how the trade affects opponent
        opp_current_score, _, _ = self.game.get_max_score_and_path(self.opponent_id)

        opp_new_chips = opp_chips.copy()
        for chip in offer_give:  # They receive what we give
            opp_new_chips[chip] = opp_new_chips.get(chip, 0) + 1
        for chip in offer_receive:  # They give what we receive
            opp_new_chips[chip] -= 1
            if opp_new_chips[chip] == 0:
                del opp_new_chips[chip]

        # Use their ACTUAL goal position to evaluate
        opp_goal = self.game.states[self.opponent_id].goal_pos
        opp_temp_state = GameState(opp_goal, opp_new_chips)
        opp_temp_game = ColoredTrails(self.game.board, {
            self.opponent_id: opp_temp_state,
            self.player_id: self.game.states[self.player_id]
        })
        opp_new_score, _, _ = opp_temp_game.get_max_score_and_path(self.opponent_id)

        # Simple acceptance model: opponent accepts if it improves their score
        # with some probability based on improvement magnitude
        opp_improvement = opp_new_score - opp_current_score

        if opp_improvement > 0:
            # They benefit - high chance of acceptance
            acceptance_prob = 0.9
        elif opp_improvement == 0:
            # Neutral for them - medium chance
            acceptance_prob = 0.3
        else:
            # Hurts them - low chance
            acceptance_prob = 0.1

        # Expected value
        my_improvement = new_score - current_score
        expected = acceptance_prob * (my_improvement - 1) + (1 - acceptance_prob) * (-1)

        return expected

    def propose_trade(self) -> Tuple[List[str], List[str]]:
        """
        Select best offer to propose based on expected utility.
        """
        possible_offers = self._get_all_possible_offers()

        best_offers = []
        best_value = -999

        # Debug: track all offer values
        offer_values = []

        for give, receive in possible_offers:
            if give == ["Pass"]:
                value = 0
            else:
                value = self.get_value(give, receive)

            offer_values.append((value, give, receive))

            if value > best_value + 0.001:
                best_value = value
                best_offers = [(give, receive)]
            elif abs(value - best_value) < 0.001:
                best_offers.append((give, receive))

        # Debug output
        if self.order <= 1:  # Only for lower orders to avoid spam
            self._log(f"  [DEBUG {self.player_id}] Evaluated {len(possible_offers)} offers, best_value={best_value:.2f}")
            # Show top 3 offers
            offer_values.sort(reverse=True)
            for i, (val, g, r) in enumerate(offer_values[:3]):
                self._log(f"    #{i + 1}: value={val:.2f}, give={g}, receive={r}")

        # Choose randomly among equally good offers
        give, receive = random.choice(best_offers) if best_offers else (["Pass"], ["Pass"])

        log_msg = f"{self.player_id} (ToM-{self.order}) proposed: GIVE {give} for RECEIVE {receive}"
        self._log(f"  {log_msg}")
        self.history.append(log_msg)

        return give, receive

    def evaluate_proposal(self, proposal: Tuple[List[str], List[str]]) -> bool:
        """
        Decide whether to accept opponent's proposal.
        """
        opp_give, opp_receive = proposal

        if opp_give == ["Pass"]:
            self.history.append(f"{self.opponent_id} PASSED")
            return True

        # Check if we have required chips
        my_chips = self.game.states[self.player_id].chips
        required = Counter(opp_receive)
        for chip, count in required.items():
            if my_chips.get(chip, 0) < count:
                self.history.append(f"{self.player_id} REJECT (missing chips)")
                # Still observe the offer even if we reject due to missing chips
                if self.order > 0:
                    self._observe(opp_give, opp_receive, False, self.opponent_id)
                else:
                    self.base_model.observe(self.game, opp_give, opp_receive, False, self.opponent_id)
                return False

        # Calculate utility change
        current_score, _, _ = self.game.get_max_score_and_path(self.player_id)

        temp_chips = dict(my_chips)
        for chip in opp_give:
            temp_chips[chip] = temp_chips.get(chip, 0) + 1
        for chip in opp_receive:
            temp_chips[chip] -= 1
            if temp_chips[chip] == 0:
                del temp_chips[chip]

        temp_state = GameState(self.game.states[self.player_id].goal_pos, temp_chips)
        temp_game = ColoredTrails(self.game.board, {
            self.player_id: temp_state,
            self.opponent_id: self.game.states[self.opponent_id]
        })
        new_score, _, _ = temp_game.get_max_score_and_path(self.player_id)

        accept = new_score > current_score

        # Update beliefs after observing the offer
        # Note: offer_give and offer_receive are from opponent's perspective
        if self.order > 0:
            self._observe(opp_give, opp_receive, accept, self.opponent_id)
        else:
            self.base_model.observe(self.game, opp_give, opp_receive, accept, self.opponent_id)

        action = "ACCEPTED" if accept else "REJECTED"
        self.history.append(f"{self.player_id} {action} offer ({opp_give} for {opp_receive})")

        return accept

    def _observe(self, offer_give: List[str], offer_receive: List[str],
                 is_accepted: bool, proposer_id: str):
        """
        Update beliefs based on observed negotiation action.
        Parameters represent the offer from the PROPOSER's perspective:
        - offer_give: what proposer gives away
        - offer_receive: what proposer receives
        """
        if self.order == 0:
            self.base_model.observe(self.game, offer_give, offer_receive, is_accepted, proposer_id)
        else:
            # Update location beliefs if opponent made the offer
            if proposer_id == self.opponent_id:
                self._update_location_beliefs(offer_give, offer_receive)

            # Propagate to sub-models
            self.opponent_model._observe(offer_give, offer_receive, is_accepted, proposer_id)
            self.self_model._observe(offer_give, offer_receive, is_accepted, proposer_id)

    def _update_location_beliefs(self, offer_give: List[str], offer_receive: List[str]):
        """
        Update beliefs about opponent's goal location based on their offer.
        Uses Bayesian update: offers are more likely from certain goal locations.

        Parameters are from OPPONENT's perspective (they give offer_give, receive offer_receive)
        """
        if self.order == 0:
            return

        new_beliefs = {}
        total = 0.0

        for loc, prior in self.location_beliefs.items():
            # Calculate how good this offer would be for opponent at this location
            opp_chips = dict(self.game.states[self.opponent_id].chips)

            opp_current_state = GameState(loc, opp_chips)
            opp_current_game = ColoredTrails(self.game.board, {
                self.opponent_id: opp_current_state,
                self.player_id: self.game.states[self.player_id]
            })
            current_score, _, _ = opp_current_game.get_max_score_and_path(self.opponent_id)

            temp_chips = opp_chips.copy()

            # Validate that opponent has all chips they're offering to give
            can_make_offer = True
            for chip in offer_give:
                if temp_chips.get(chip, 0) <= 0:
                    can_make_offer = False
                    break

            if not can_make_offer:
                # This location is incompatible with the observed offer
                # Set very low probability (but not zero for numerical stability)
                new_beliefs[loc] = prior * 0.01
                total += new_beliefs[loc]
                continue

            # Apply the trade to get new chip state
            for chip in offer_give:
                temp_chips[chip] -= 1
                if temp_chips[chip] == 0:
                    del temp_chips[chip]
            for chip in offer_receive:
                temp_chips[chip] = temp_chips.get(chip, 0) + 1

            temp_state = GameState(loc, temp_chips)
            temp_game = ColoredTrails(self.game.board, {
                self.opponent_id: temp_state,
                self.player_id: self.game.states[self.player_id]
            })
            new_score, _, _ = temp_game.get_max_score_and_path(self.opponent_id)

            # Likelihood: higher if offer improves score at this location
            utility_gain = max(0, new_score - current_score)
            likelihood = 1.0 + utility_gain / 100.0  # Scale factor

            posterior = prior * likelihood
            new_beliefs[loc] = posterior
            total += posterior

        # Normalize
        if total > 0:
            for loc in new_beliefs:
                new_beliefs[loc] /= total
            self.location_beliefs = new_beliefs