"""
Theory of Mind Agent for Colored Trails Game
Direct port of JavaScript implementation, adapted for Python game logic
"""

import random
import math
from typing import List, Dict, Tuple, Optional
from collections import Counter, deque
from game.colored_trails import ColoredTrails, GameState, COLORS, BOARD_SIZE

# Constants from JS implementation
DEFAULT_LEARNING_SPEED = 0.8
PRECISION = 0.00001
MODE_ONE_LOCATION = 0
MODE_ALL_LOCATION = 1


class ToM0Model:
    """
    Basic agent (order-0) that learns what offers tend to be accepted.
    This agent does NOT use Theory of Mind - it simply learns acceptance rates
    and multiplies them by its own utility gains.
    """

    def __init__(self, player_id: str, game_env: ColoredTrails, logger=None):
        self.player_id = player_id
        self.opponent_id = "p2" if player_id == "p1" else "p1"
        self.game = game_env
        self.logger = logger
        self.learning_speed = DEFAULT_LEARNING_SPEED

        # Initialize belief matrices (9x9 for pos/neg chip differences up to 8)
        self.cnt_beliefs = [[5]*9 for _ in range(9)]
        self.ttl_beliefs = [[5]*9 for _ in range(9)]

        # Pre-populate with priors from JS implementation
        self._init_belief_priors()

        # Belief about acceptance probability for each possible offer
        self.belief_offer = {}

        # For saving/restoring beliefs (used by higher order agents)
        self.saved_beliefs = []
        self.save_count = 0

        # Track belief history for visualization
        self.belief_history = []

    def _log(self, msg: str):
        if self.logger:
            self.logger.log(f"[ToM0-{self.player_id}] {msg}")

    def _init_belief_priors(self):
        """Initialize belief matrices with priors from JS implementation"""
        # Using simplified version of the JS priors
        self.cnt_beliefs = [
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [14, 248, 407, 5, 5, 5, 5, 5, 5],
            [26, 316, 196, 129, 5, 5, 5, 5, 5],
            [28, 19, 194, 62, 24, 5, 5, 5, 5],
            [26, 27, 18, 19, 10, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5]
        ]

        self.ttl_beliefs = [
            [226, 25, 27, 34, 45, 5, 5, 5, 5],
            [14, 495, 912, 26, 34, 5, 5, 5, 5],
            [26, 566, 392, 289, 23, 5, 5, 5, 5],
            [28, 19, 345, 122, 55, 5, 5, 5, 5],
            [26, 27, 18, 32, 17, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5]
        ]

    def init(self, game_env: ColoredTrails, player_id: str):
        """Initialize for a new game"""
        self.player_id = player_id
        self.opponent_id = "p2" if player_id == "p1" else "p1"
        self.game = game_env

        # Initialize belief_offer for all possible offers
        self.belief_offer = {}
        for offer in self._generate_all_possible_offers():
            self.belief_offer[offer] = self.get_acceptance_rate(offer[0], offer[1])

        self.save_count = 0
        self.saved_beliefs = []
        self.belief_history = []  # Reset history for new game

    def save_beliefs(self):
        """Save current beliefs to be restored later"""
        self.saved_beliefs.append(dict(self.belief_offer))
        self.save_count += 1

    def restore_beliefs(self):
        """Restore previously saved beliefs"""
        self.save_count -= 1
        self.belief_offer = self.saved_beliefs[self.save_count]
        self.saved_beliefs.pop()

    def _get_chip_difference(self, give_chips: List[str], receive_chips: List[str]) -> Tuple[int, int]:
        """Calculate positive and negative chip differences for a trade"""
        if give_chips == ["Pass"] or receive_chips == ["Pass"]:
            return 0, 0

        pos = len(receive_chips)  # chips we receive (positive for us)
        neg = len(give_chips)     # chips we give (negative for us)
        return min(pos, 8), min(neg, 8)  # cap at 8 for matrix bounds

    def get_acceptance_rate(self, give_chips: List[str], receive_chips: List[str]) -> float:
        """Returns the believed probability that a given offer will be accepted"""
        pos, neg = self._get_chip_difference(give_chips, receive_chips)

        if self.ttl_beliefs[pos][neg] == 0:
            return 0.5

        return self.cnt_beliefs[pos][neg] / self.ttl_beliefs[pos][neg]

    def observe(self, give_chips: List[str], receive_chips: List[str], is_accepted: bool, player_id: str):
        """Observe an offer being made and whether it was accepted"""
        pos, neg = self._get_chip_difference(give_chips, receive_chips)

        # Update total observations
        self.ttl_beliefs[pos][neg] += 1

        if player_id != self.player_id:
            # Observing opponent's behavior
            self.cnt_beliefs[pos][neg] += 1
            self.increase_color_belief(give_chips, receive_chips)
        elif is_accepted:
            self.cnt_beliefs[pos][neg] += 1
        else:
            self.decrease_color_belief(give_chips, receive_chips)

        # Record belief state for visualization
        self._record_belief_state(give_chips, receive_chips, is_accepted)

    def _record_belief_state(self, give_chips: List[str], receive_chips: List[str], is_accepted: bool):
        """Record current belief state for visualization"""
        # Sample some key acceptance rates
        sample_offers = [
            (["RE"], ["BL"]),
            (["BL"], ["RE"]),
            (["YE"], ["GR"]),
            (["Pass"], ["Pass"])
        ]

        belief_snapshot = {
            'round': len(self.belief_history),
            'offer': (give_chips, receive_chips),
            'accepted': is_accepted,
            'acceptance_rates': {}
        }

        for offer in sample_offers:
            if all(c in COLORS or c == "Pass" for c in offer[0] + offer[1]):
                rate = self.get_acceptance_rate(offer[0], offer[1])
                belief_snapshot['acceptance_rates'][str(offer)] = rate

        self.belief_history.append(belief_snapshot)

    def get_belief_summary(self) -> Dict:
        """Get a summary of current beliefs for display"""
        summary = {
            'player_id': self.player_id,
            'order': 0,
            'top_acceptance_rates': [],
            'belief_matrix_sample': []
        }

        # Get top 5 offers by acceptance rate
        offer_rates = []
        for offer, rate in self.belief_offer.items():
            if offer != (("Pass",), ("Pass",)):
                offer_rates.append((offer, rate))

        offer_rates.sort(key=lambda x: x[1], reverse=True)
        summary['top_acceptance_rates'] = offer_rates[:5]

        # Sample belief matrix (first 3x3)
        for i in range(min(3, len(self.cnt_beliefs))):
            row = []
            for j in range(min(3, len(self.cnt_beliefs[i]))):
                if self.ttl_beliefs[i][j] > 0:
                    rate = self.cnt_beliefs[i][j] / self.ttl_beliefs[i][j]
                else:
                    rate = 0.5
                row.append(f"{rate:.2f}")
            summary['belief_matrix_sample'].append(row)

        return summary

    def increase_color_belief(self, give_chips: List[str], receive_chips: List[str]):
        """Decrease belief that offers less generous than this will be successful"""
        offer_key = (tuple(sorted(give_chips)), tuple(sorted(receive_chips)))

        for test_offer in self.belief_offer:
            test_give, test_receive = test_offer

            # If test offer is less generous (gives less or asks for more)
            if (len(test_give) < len(give_chips) or
                len(test_receive) > len(receive_chips)):
                self.belief_offer[test_offer] *= (1 - self.learning_speed)

    def decrease_color_belief(self, give_chips: List[str], receive_chips: List[str]):
        """Decrease belief that offers no more generous than this will be successful"""
        offer_key = (tuple(sorted(give_chips)), tuple(sorted(receive_chips)))

        for test_offer in self.belief_offer:
            test_give, test_receive = test_offer

            # If test offer is no more generous
            if (len(test_give) <= len(give_chips) and
                len(test_receive) >= len(receive_chips)):
                self.belief_offer[test_offer] *= (1 - self.learning_speed)

    def _generate_all_possible_offers(self) -> List[Tuple[Tuple[str], Tuple[str]]]:
        """Generate all possible offers for initialization"""
        offers = []
        my_chips = self.game.states[self.player_id].chips
        opp_chips = self.game.states[self.opponent_id].chips

        # Pass option
        offers.append((("Pass",), ("Pass",)))

        # All single chip trades
        for my_color in COLORS:
            if my_chips.get(my_color, 0) > 0:
                for opp_color in COLORS:
                    if opp_chips.get(opp_color, 0) > 0:
                        offers.append(((my_color,), (opp_color,)))

        # Some 2-for-1 and 1-for-2 trades
        for my_color in COLORS:
            if my_chips.get(my_color, 0) >= 2:
                for opp_color in COLORS:
                    if opp_chips.get(opp_color, 0) > 0:
                        offers.append(((my_color, my_color), (opp_color,)))

            if my_chips.get(my_color, 0) > 0:
                for opp_color in COLORS:
                    if opp_chips.get(opp_color, 0) >= 2:
                        offers.append(((my_color,), (opp_color, opp_color)))

        return offers

    def set_id(self, new_player_id: str):
        """Set the player ID"""
        self.player_id = new_player_id
        self.opponent_id = "p2" if new_player_id == "p1" else "p1"


class ToMAgent:
    """
    Theory of Mind agent that models opponent's decision-making.
    Supports different orders of recursive reasoning.
    """

    def __init__(self, player_id: str, game_env: ColoredTrails, order: int = 1, logger=None):
        self.player_id = player_id
        self.opponent_id = "p2" if player_id == "p1" else "p1"
        self.game = game_env
        self.order = order
        self.logger = logger
        self.learning_speed = DEFAULT_LEARNING_SPEED
        self.confidence = 1.0  # confidence in current order model
        self.confidence_locked = False
        self.mode = MODE_ALL_LOCATION
        self.history = []

        # Location beliefs (probability distribution over opponent's possible goal locations)
        self.location_beliefs = []
        self.saved_beliefs = []
        self.save_count = 0
        self.last_accuracy = 0

        # Track belief history for visualization
        self.location_belief_history = []
        self.confidence_history = []

        # Initialize possible goal locations
        self.possible_locations = []
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if abs(r - 2) + abs(c - 2) > 2:
                    self.possible_locations.append((r, c))

        # Get our actual location index
        self.loc = self._get_location_index(self.game.states[player_id].goal_pos)

        # Initialize location beliefs (uniform distribution)
        self.location_beliefs = [1.0 / len(self.possible_locations)] * len(self.possible_locations)

        # Create sub-models based on order
        if order > 0:
            # Model of opponent at order-1
            self.opponent_model = ToMAgent(
                self.opponent_id, game_env, order - 1, logger
            )
            self.opponent_model.confidence_locked = True

            # Self model at order-1 (for mixing strategies)
            self.self_model = ToMAgent(
                player_id, game_env, order - 1, logger
            )
        else:
            # Order-0 uses basic learning model
            self.opponent_model = ToM0Model(player_id, game_env, logger)
            self.self_model = None

        self._log(f"Initialized ToM-{order} agent")

    def _log(self, msg: str):
        if self.logger:
            self.logger.log(f"[ToM{self.order}-{self.player_id}] {msg}")

    def _get_location_index(self, goal_pos: Tuple[int, int]) -> int:
        """Get the index of a goal position in the possible locations list"""
        try:
            return self.possible_locations.index(goal_pos)
        except ValueError:
            return 0

    def init(self, game_env: ColoredTrails, player_id: str):
        """Initialize for a new game"""
        self.player_id = player_id
        self.opponent_id = "p2" if player_id == "p1" else "p1"
        self.game = game_env
        self.loc = self._get_location_index(game_env.states[player_id].goal_pos)
        self.saved_beliefs = []
        self.save_count = 0

        if self.order > 0:
            self.opponent_model.init(game_env, self.opponent_id)
            self.self_model.init(game_env, player_id)
            # Reset location beliefs to uniform
            self.location_beliefs = [1.0 / len(self.possible_locations)] * len(self.possible_locations)
        else:
            self.opponent_model.init(game_env, player_id)

    def save_beliefs(self):
        """Save current beliefs"""
        if self.order > 0:
            self.saved_beliefs.append(list(self.location_beliefs))
            self.save_count += 1
        self.opponent_model.save_beliefs()

    def restore_beliefs(self):
        """Restore saved beliefs"""
        if self.order > 0:
            self.save_count -= 1
            self.location_beliefs = self.saved_beliefs[self.save_count]
            self.saved_beliefs.pop()
        self.opponent_model.restore_beliefs()

    def get_location_beliefs(self, location: int) -> float:
        """Get belief probability for a specific location"""
        if self.confidence_locked:
            return self.location_beliefs[location]

        if self.order == 0:
            return 1.0 / len(self.possible_locations)

        if self.confidence >= 1.0:
            return self.location_beliefs[location]

        # Mix with lower-order model
        return (self.confidence * self.location_beliefs[location] +
                (1 - self.confidence) * self.self_model.get_location_beliefs(location))

    def inform_location(self, game_env: ColoredTrails):
        """Inform agent of actual locations (for testing/oracle mode)"""
        self.loc = self._get_location_index(game_env.states[self.player_id].goal_pos)

        if self.order > 0:
            # Set location beliefs to actual location with certainty
            opp_loc = self._get_location_index(game_env.states[self.opponent_id].goal_pos)
            self.location_beliefs = [0.0] * len(self.possible_locations)
            self.location_beliefs[opp_loc] = 1.0

            self.self_model.inform_location(game_env)
            self.opponent_model.inform_location(game_env)

    def propose_trade(self) -> Tuple[List[str], List[str]]:
        """
        Propose a trade to the opponent.
        Returns (chips_to_give, chips_to_receive)
        """
        self._log(f"Generating trade proposal (Order-{self.order})")

        if self.order == 0:
            # For order-0, find the offer that maximizes expected utility
            best_offers = []
            best_value = -float('inf')

            for give_chips, receive_chips in self._generate_possible_offers():
                # Calculate expected value = utility_gain * acceptance_rate
                utility_gain = self._calculate_direct_utility_gain(give_chips, receive_chips)
                acceptance_rate = self.opponent_model.get_acceptance_rate(give_chips, receive_chips)
                expected_value = utility_gain * acceptance_rate

                if expected_value > best_value + PRECISION:
                    best_value = expected_value
                    best_offers = [(give_chips, receive_chips)]
                elif abs(expected_value - best_value) < PRECISION:
                    best_offers.append((give_chips, receive_chips))

            if not best_offers or best_value < 0:
                self._log("No beneficial trade found, passing")
                self.history.append(f"{self.player_id} PASSED")
                return ["Pass"], ["Pass"]

            give_chips, receive_chips = random.choice(best_offers)
            self._log(f"Proposing: give {give_chips} for {receive_chips} (expected value: {best_value:.2f})")
            self.history.append(f"{self.player_id} offers {give_chips} for {receive_chips}")

            # Update ToM0Model's beliefs optimistically
            self.opponent_model.observe(give_chips, receive_chips, True, self.player_id)

            return give_chips, receive_chips
        else:
            # Higher-order: use existing logic
            valid_offers = self.get_valid_offers(offer_to_me=None)

            if not valid_offers:
                self._log("No valid offers found, passing")
                self.history.append(f"{self.player_id} PASSED")
                return ["Pass"], ["Pass"]

            selected = random.choice(valid_offers)

            if selected == (["Pass"], ["Pass"]):
                self._log("Best option is to pass")
                self.history.append(f"{self.player_id} PASSED")
                return ["Pass"], ["Pass"]

            give_chips, receive_chips = selected
            self._log(f"Proposing: give {give_chips} for {receive_chips}")
            self.history.append(f"{self.player_id} offers {give_chips} for {receive_chips}")

            self.send_offer(give_chips, receive_chips)

            return give_chips, receive_chips

    def evaluate_proposal(self, proposal: Tuple[List[str], List[str]]) -> bool:
        """
        Evaluate whether to accept a trade proposal from the opponent.
        proposal = (opponent_gives, opponent_receives)
        """
        opp_give, opp_receive = proposal

        self._log(f"Evaluating proposal: receive {opp_give}, give {opp_receive}")

        # Handle pass
        if opp_give == ["Pass"]:
            self.history.append(f"{self.opponent_id} PASSED")
            return True

        # Check if we have the chips they want
        my_chips = self.game.states[self.player_id].chips
        needed = Counter(opp_receive)

        for chip, count in needed.items():
            if my_chips.get(chip, 0) < count:
                self._log(f"Cannot accept: missing {chip}")
                self.history.append(f"{self.player_id} REJECT (insufficient {chip})")
                return False

        if self.order == 0:
            # Order-0: Accept if utility gain is positive
            utility_gain = self._calculate_direct_utility_gain(opp_receive, opp_give)
            accept = utility_gain > 0

            # Update beliefs based on the outcome
            self.opponent_model.observe(opp_receive, opp_give, accept, self.opponent_id)

            if accept:
                self._log(f"ACCEPTING (utility gain: {utility_gain:.2f})")
                self.history.append(f"{self.player_id} ACCEPTED")
            else:
                self._log(f"REJECTING (utility gain: {utility_gain:.2f})")
                self.history.append(f"{self.player_id} REJECTED")

            return accept
        else:
            # Higher-order: use existing logic
            # Receive the offer (update models)
            self.receive_offer(opp_give, opp_receive)

            # Get our best alternative
            best_offers = self.get_valid_offers(offer_to_me=(opp_give, opp_receive))

            # If the opponent's offer is among our best options, accept
            if (opp_give, opp_receive) in best_offers:
                self._log("ACCEPTING (offer is among best options)")
                self.history.append(f"{self.player_id} ACCEPTED")
                return True
            else:
                self._log("REJECTING (have better alternatives)")
                self.history.append(f"{self.player_id} REJECTED")
                return False

    def get_valid_offers(self, offer_to_me: Optional[Tuple[List[str], List[str]]]) -> List[Tuple[List[str], List[str]]]:
        """Get all offers that maximize expected utility"""
        all_offers = []
        best_value = 0

        # Generate possible offers
        possible = self._generate_possible_offers()

        for give_chips, receive_chips in possible:
            value = self.get_value(give_chips, receive_chips)

            if value > best_value - PRECISION:
                if value > best_value + PRECISION:
                    all_offers = []
                    best_value = value
                all_offers.append((give_chips, receive_chips))

        # If offered something, check if it's better than our best counter-offer
        if offer_to_me is not None:
            opp_give, opp_receive = offer_to_me
            offer_value = self._calculate_direct_utility_gain(opp_receive, opp_give)

            if offer_value > best_value - PRECISION:
                if offer_value > best_value + PRECISION:
                    all_offers = [(opp_give, opp_receive)]
                    best_value = offer_value
                elif (opp_give, opp_receive) not in all_offers:
                    all_offers.append((opp_give, opp_receive))

        # If best value is negative, passing/withdrawing is better
        if best_value < PRECISION:
            all_offers = [(["Pass"], ["Pass"])]

        return all_offers

    def get_location_value(self, give_chips: List[str], receive_chips: List[str]) -> float:
        """
        Get expected value of making an offer, assuming (predicting) the opponent's goal
        is the one currently set in the opponent_model (loc attribute).

        This method is called inside a loop over location beliefs in get_value(). So there is no leakage of the actual
        goal location.
        """
        direct_gain = self._calculate_direct_utility_gain(give_chips, receive_chips)

        if self.order == 0:
            # Order-0 case (should only be hit in edge cases, get_value handles this)
            acceptance = self.opponent_model.get_acceptance_rate(give_chips, receive_chips)
            return direct_gain * acceptance

        # --- Higher Order (Order > 0) Logic ---
        # The opponent_model (Order - 1) is currently set to the hypothesized location.
        # We ask the opponent_model for the expected value of *receiving* this offer,
        # which acts as the opponent's acceptance probability for us.

        # 1. Flip the offer: Opponent receives `give_chips` and gives `receive_chips`
        opp_value_of_receiving_offer = self.opponent_model.get_value(receive_chips, give_chips)

        # 2. Get the opponent's best possible value
        opp_best_value = self.opponent_model.get_best_value()

        # 3. Model Acceptance Probability (Likelihood of acceptance)
        # We assume the opponent is more likely to accept if the offer is close to
        # or better than their best possible counter-offer (opp_best_value).

        # Calculate how good our offer is for the opponent relative to their best move.
        if opp_best_value < PRECISION:
            # If opponent's best alternative is to pass (value close to 0),
            # any positive value for them is good.
            likelihood = 1.0 if opp_value_of_receiving_offer > 0 else 0.0
        else:
            # Compare the offer's value to the opponent's best value (normalized)
            # Add a small buffer to avoid division by zero and smooth the curve
            likelihood = max(0, min(1.0, (opp_value_of_receiving_offer + PRECISION) / (opp_best_value + PRECISION)))

        # 4. Calculate the Final Expected Value for *US*
        # Our Value = Our Utility Gain * Acceptance Likelihood - Negotiation Cost

        # Use 1.0 as a default negotiation cost if it's not defined elsewhere.
        NEGOTIATION_COST = 1.0

        return (direct_gain * likelihood) - NEGOTIATION_COST

    def get_value(self, give_chips: List[str], receive_chips: List[str]) -> float:
        """Get expected value of making an offer"""
        # Check if this trade improves our position
        direct_gain = self._calculate_direct_utility_gain(give_chips, receive_chips)

        if direct_gain <= 0 and give_chips != ["Pass"]:
            return -1  # Don't make trades that hurt us

        if self.order == 0:
            # Order-0: Simple expected value = utility_gain * acceptance_probability
            # No Theory of Mind - just learned acceptance rates
            acceptance_rate = self.opponent_model.get_acceptance_rate(give_chips, receive_chips)

            return direct_gain * acceptance_rate

        # Higher order: consider opponent's likely response
        if self.confidence > 0 or self.confidence_locked:
            self.opponent_model.save_beliefs()
            self.opponent_model.receive_offer(receive_chips, give_chips)  # Flipped for opponent

            if self.mode == MODE_ONE_LOCATION:
                # Use most likely location
                best_locs = []
                max_belief = max(self.location_beliefs)

                for l in range(len(self.location_beliefs)):
                    if self.location_beliefs[l] >= max_belief - PRECISION:
                        best_locs.append(l)

                loc = random.choice(best_locs)
                if hasattr(self.opponent_model, 'loc'):
                    self.opponent_model.loc = loc

                value = self.get_location_beliefs(give_chips, receive_chips)
            else:
                # Average over all locations weighted by belief
                value = 0
                for l in range(len(self.location_beliefs)):
                    if self.location_beliefs[l] > 0:
                        if hasattr(self.opponent_model, 'loc'):
                            self.opponent_model.loc = l
                        value += self.location_beliefs[l] * self.get_location_value(give_chips, receive_chips)

            self.opponent_model.restore_beliefs()
        else:
            value = 0

        # Mix with lower-order estimate if confidence < 1
        if self.confidence >= 1 or self.confidence_locked:
            return value

        low_value = self.self_model.get_value(give_chips, receive_chips)
        return self.confidence * value + (1 - self.confidence) * low_value

    def _estimate_opponent_gain(self, give_chips: List[str], receive_chips: List[str]) -> float:
        """
        Estimate opponent's utility gain from accepting our offer by averaging
        utility gain over all possible goal locations, weighted by our belief.

        The chips are flipped: opponent receives `receive_chips` and gives `give_chips`.
        """
        # Calculate the opponent's chips after the hypothetical trade
        opp_chips_after_trade = dict(self.game.states[self.opponent_id].chips)

        for chip in give_chips:  # Opponent receives these chips
            if chip != "Pass":
                opp_chips_after_trade[chip] = opp_chips_after_trade.get(chip, 0) + 1

        for chip in receive_chips:  # Opponent gives these chips
            if chip != "Pass" and chip in opp_chips_after_trade:
                opp_chips_after_trade[chip] -= 1
                if opp_chips_after_trade[chip] == 0:
                    del opp_chips_after_trade[chip]

        # Use the opponent's actual game state object for calculation setup
        temp_state = self.game.states[self.opponent_id]
        original_chips = temp_state.chips

        # 🔒 CRITICAL FIX: Save the true goal position before simulation
        # The game environment (temp_state) should not be modified by modeling.
        true_goal_pos = temp_state.goal_pos

        expected_gain = 0.0

        # --- Iterate over belief distribution to model opponent's utility ---
        for l_idx, belief_prob in enumerate(self.location_beliefs):
            if belief_prob <= PRECISION:
                continue

            # 1. Temporarily set the opponent's goal to the hypothesized location
            hypothesized_goal = self.possible_locations[l_idx]
            temp_state.goal_pos = hypothesized_goal

            # Calculate opponent's current max score assuming this hypothesized goal
            temp_state.chips = original_chips  # Use *actual* current chips
            opp_current_score, _, _ = self.game.get_max_score_and_path(self.opponent_id)

            # Calculate opponent's new max score assuming this hypothesized goal
            temp_state.chips = Counter(opp_chips_after_trade)  # Use *simulated* post-trade chips
            opp_new_score, _, _ = self.game.get_max_score_and_path(self.opponent_id)

            # Calculate utility gain for this specific location
            gain_at_location = opp_new_score - opp_current_score

            # Weight the gain by the belief probability
            expected_gain += belief_prob * gain_at_location
        # --- END MODELING ---

        # CRITICAL RESTORATION: Reset the opponent's state to its original, true values
        temp_state.goal_pos = true_goal_pos
        temp_state.chips = original_chips

        return expected_gain

    def get_best_value(self) -> float:
        """Get the best achievable value"""
        best = 0
        for give_chips, receive_chips in self._generate_possible_offers():
            value = self.get_value(give_chips, receive_chips)
            if value > best:
                best = value
        return max(0, best)

    def update_location_beliefs(self, give_chips: List[str], receive_chips: List[str]):
        """Update beliefs about opponent's location based on their offer"""
        if self.order == 0:
            return

        accuracy = 0
        sum_beliefs = 0

        for l in range(len(self.location_beliefs)):
            # Temporarily set opponent model to this location
            if hasattr(self.opponent_model, 'loc'):
                old_loc = self.opponent_model.loc
                self.opponent_model.loc = l

            # How likely is opponent to make this offer from location l?
            if hasattr(self.opponent_model, 'get_value'):
                offer_value = self.opponent_model.get_value(give_chips, receive_chips)
                best_value = self.opponent_model.get_best_value()

                if offer_value <= 0:
                    self.location_beliefs[l] = 0
                else:
                    likelihood = max((offer_value + 1) / (best_value + 1), 0)
                    self.location_beliefs[l] *= likelihood
                    accuracy += self.location_beliefs[l]

                if hasattr(self.opponent_model, 'loc'):
                    self.opponent_model.loc = old_loc

            sum_beliefs += self.location_beliefs[l]

        # Normalize
        if sum_beliefs > 0:
            for l in range(len(self.location_beliefs)):
                self.location_beliefs[l] /= sum_beliefs
        else:
            # Reset to uniform if no beliefs
            self.location_beliefs = [1.0 / len(self.possible_locations)] * len(self.possible_locations)

        self.last_accuracy = accuracy

        # Update confidence
        if not self.confidence_locked:
            self.confidence = (1 - self.learning_speed) * self.confidence + self.learning_speed * accuracy

        # Record belief state
        self._record_location_beliefs()

    def _record_location_beliefs(self):
        """Record current location beliefs for visualization"""
        # Find top 3 most likely locations
        location_probs = list(enumerate(self.location_beliefs))
        location_probs.sort(key=lambda x: x[1], reverse=True)

        belief_snapshot = {
            'round': len(self.location_belief_history),
            'top_locations': [(self.possible_locations[idx], prob) for idx, prob in location_probs[:3]],
            'confidence': self.confidence
        }

        self.location_belief_history.append(belief_snapshot)
        self.confidence_history.append(self.confidence)

    def get_belief_summary(self) -> Dict:
        """Get a summary of current beliefs for display"""
        summary = {
            'player_id': self.player_id,
            'order': self.order,
            'confidence': self.confidence
        }

        if self.order == 0:
            # For order-0, delegate to the ToM0Model
            if hasattr(self.opponent_model, 'get_belief_summary'):
                return self.opponent_model.get_belief_summary()
        else:
            # For higher orders, show location beliefs
            location_probs = list(enumerate(self.location_beliefs))
            location_probs.sort(key=lambda x: x[1], reverse=True)

            summary['top_goal_beliefs'] = []
            for idx, prob in location_probs[:3]:
                summary['top_goal_beliefs'].append({
                    'location': self.possible_locations[idx],
                    'probability': f"{prob:.3f}"
                })

            summary['confidence_in_order'] = f"{self.confidence:.3f}"

        return summary

    def receive_offer(self, give_chips: List[str], receive_chips: List[str]):
        """Process receiving an offer from opponent"""
        if give_chips == ["Pass"]:
            return

        if self.order > 0:
            # Update location beliefs based on the offer
            self.update_location_beliefs(give_chips, receive_chips)

            # Update sub-models
            self.self_model.receive_offer(give_chips, receive_chips)
            self.opponent_model.send_offer(receive_chips, give_chips)  # They sent this
        else:
            # Order-0: just observe
            self.opponent_model.observe(give_chips, receive_chips, True, self.opponent_id)

    def send_offer(self, give_chips: List[str], receive_chips: List[str]):
        """Process sending an offer"""
        if self.order > 0:
            self.self_model.send_offer(give_chips, receive_chips)
            self.opponent_model.receive_offer(receive_chips, give_chips)  # They receive flipped
        else:
            # Order-0: observe our own offer as accepted (optimistic)
            self.opponent_model.observe(give_chips, receive_chips, True, self.player_id)

    def _calculate_direct_utility_gain(self, give_chips: List[str], receive_chips: List[str]) -> float:
        """Calculate direct utility gain from a trade"""
        if give_chips == ["Pass"]:
            return 0

        current_score, _, _ = self.game.get_max_score_and_path(self.player_id)

        # Check if we can make this trade
        my_chips = self.game.states[self.player_id].chips
        for chip in give_chips:
            if chip != "Pass" and my_chips.get(chip, 0) < give_chips.count(chip):
                return -float('inf')

        # Simulate the trade
        new_chips = dict(my_chips)
        for chip in receive_chips:
            if chip != "Pass":
                new_chips[chip] = new_chips.get(chip, 0) + 1
        for chip in give_chips:
            if chip != "Pass":
                new_chips[chip] -= 1
                if new_chips[chip] == 0:
                    del new_chips[chip]

        temp_state = self.game.states[self.player_id]
        original_chips = temp_state.chips
        temp_state.chips = Counter(new_chips)
        new_score, _, _ = self.game.get_max_score_and_path(self.player_id)
        temp_state.chips = original_chips

        return new_score - current_score

    def _generate_possible_offers(self) -> List[Tuple[List[str], List[str]]]:
        """Generate reasonable trade offers to consider"""
        offers = []

        # Pass option
        offers.append((["Pass"], ["Pass"]))

        my_chips = self.game.states[self.player_id].chips
        opp_chips = self.game.states[self.opponent_id].chips

        # Only generate offers with chips we actually have
        my_colors = [color for color in COLORS if my_chips.get(color, 0) > 0]
        opp_colors = [color for color in COLORS if opp_chips.get(color, 0) > 0]

        # Single chip trades
        for my_color in my_colors:
            for opp_color in opp_colors:
                if my_color != opp_color:
                    offers.append(([my_color], [opp_color]))

        # 2-for-1 trades
        for my_color in my_colors:
            if my_chips[my_color] >= 2:
                for opp_color in opp_colors:
                    offers.append(([my_color, my_color], [opp_color]))

        # 1-for-2 trades
        for my_color in my_colors:
            for opp_color in opp_colors:
                if opp_chips[opp_color] >= 2:
                    offers.append(([my_color], [opp_color, opp_color]))

        return offers