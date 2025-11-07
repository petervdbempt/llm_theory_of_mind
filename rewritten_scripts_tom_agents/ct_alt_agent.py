import random
from typing import List

# --- Constants (ported directly) ---
DEFAULT_LEARNING_SPEED = 0.8  # Degree to which agents adjust their behaviour
PRECISION = 1e-5              # Precision of "better" and "similar" offers

MODE_ONE_LOCATION = 0
MODE_ALL_LOCATION = 1


# --- Helper placeholders (must be provided elsewhere, as in the JS version) ---
def getChipDifference(own_chips_code: int, offer_code: int, bin_max: List[int]) -> List[int]:
    """
    Should return per-color chip differences given the agent's chipset and an offer.
    Placeholder to match the JS dependency. Implement to suit your environment.
    """
    raise NotImplementedError


def convertCode(code: int, bin_max: List[int]) -> List[int]:
    """
    Should convert an integer-coded chip vector to a per-color 'bins' vector.
    Placeholder to match the JS dependency. Implement to suit your environment.
    """
    raise NotImplementedError


# --- ToM0 model (order-0) ---
class ToM0Model:
    """
    Basic agent that learns what offers tend to be accepted.
    Port of `ToM0model` from JS.
    """

    def __init__(self, playerID: int):
        self.playerID = playerID
        self.loc = 0
        self.learningSpeed = DEFAULT_LEARNING_SPEED
        self.savedBeliefs: List[List[float]] = []
        self.saveCount = 0

        # Copied directly from the JS arrays (9x9 tables)
        self.cntBeliefs = [
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [14, 248, 407, 5, 5, 5, 5, 5, 5],
            [26, 316, 196, 129, 5, 5, 5, 5, 5],
            [28, 19, 194, 62, 24, 5, 5, 5, 5],
            [26, 27, 18, 19, 10, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
        ]
        self.ttlBeliefs = [
            [226, 25, 27, 34, 45, 5, 5, 5, 5],
            [14, 495, 912, 26, 34, 5, 5, 5, 5],
            [26, 566, 392, 289, 23, 5, 5, 5, 5],
            [28, 19, 345, 122, 55, 5, 5, 5, 5],
            [26, 27, 18, 32, 17, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
            [5, 5, 5, 5, 5, 5, 5, 5, 5],
        ]

        self.beliefOffer: List[float] = []

    # JS: this.init = function(ctGame, playerID) { ... }
    def init(self, ctGame, playerID: int):
        """
        Initializes agent for the given game with the given ID.
        Expects ctGame.utilityFunction[playerID] to be indexable (number of offer codes).
        """
        self.playerID = playerID
        self.beliefOffer = []
        for i in range(len(ctGame.utilityFunction[self.playerID])):
            self.beliefOffer.append(self.getAcceptanceRate(ctGame, i))
        self.saveCount = 0
        self.savedBeliefs = []

    def saveBeliefs(self):
        """Saves beliefs to be restored later. Used by theory-of-mind agents."""
        self.savedBeliefs.append(self.beliefOffer.copy())
        self.saveCount += 1

    def restoreBeliefs(self):
        """Restores previously saved beliefs. Used by theory-of-mind agents."""
        self.saveCount -= 1
        self.beliefOffer = self.savedBeliefs[self.saveCount].copy()

    def observe(self, ctGame, offer: int, isAccepted: bool, playerID: int):
        """
        Observes the offer that is accepted/rejected in a given game by a given player.
        """
        pos = 0
        neg = 0
        diff = getChipDifference(ctGame.chipSets[self.playerID], offer, ctGame.binMax)
        for d in diff:
            if d > 0:
                pos += d
            else:
                neg -= d
        self.ttlBeliefs[pos][neg] += 1
        if playerID != self.playerID:
            self.cntBeliefs[pos][neg] += 1
            self.increaseColorBelief(ctGame, offer)
        elif isAccepted:
            self.cntBeliefs[pos][neg] += 1
        else:
            self.decreaseColorBelief(ctGame, offer)

    def increaseColorBelief(self, ctGame, newOwnChips: int):
        """
        Decrease belief that offers less generous than the given offer will be successful.
        (Note: Name matches JS; logic unchanged.)
        """
        newBins = convertCode(newOwnChips, ctGame.binMax)
        for i in range(len(self.beliefOffer)):
            curOffer = convertCode(i, ctGame.binMax)
            for j in range(len(curOffer)):
                if curOffer[j] > newBins[j]:
                    self.beliefOffer[i] = (1 - self.learningSpeed) * self.beliefOffer[i]
                    break  # mirrors the same multiplicative reduction once per offending color

    def decreaseColorBelief(self, ctGame, newOwnChips: int):
        """
        Decrease belief that offers no more generous than the given offer will be successful.
        BUGFIX from JS: used `beliefOffer` instead of `this.beliefOffer`. Fixed here.
        """
        newBins = convertCode(newOwnChips, ctGame.binMax)
        for i in range(len(self.beliefOffer)):
            curOffer = convertCode(i, ctGame.binMax)
            for j in range(len(curOffer)):
                if curOffer[j] >= newBins[j]:
                    self.beliefOffer[i] = (1 - self.learningSpeed) * self.beliefOffer[i]
                    break

    def getAcceptanceRate(self, ctGame, offer: int) -> float:
        """
        Returns the believed probability that a given offer will be accepted.
        """
        pos = 0
        neg = 0
        diff = getChipDifference(ctGame.chipSets[self.playerID], offer, ctGame.binMax)
        for d in diff:
            if d > 0:
                pos += d
            else:
                neg -= d
        # Avoid division by zero; JS tables ensure >0 but we guard anyway.
        denom = self.ttlBeliefs[pos][neg]
        if denom <= 0:
            return 0.0
        return self.cntBeliefs[pos][neg] / denom

    def getExpectedValue(self, ctGame, offer: int) -> float:
        """
        Returns the expected change in score by making the offer.
        """
        return self.beliefOffer[offer] * ctGame.utilityFunction[self.loc][offer]

    def setID(self, newPlayerID: int):
        """Sets playerID for this agent."""
        self.playerID = newPlayerID


# --- Theory-of-Mind Agent (order >= 0) ---
class Agent:
    """
    Theory-of-mind agent. Mirrors the original JS structure closely.
    """

    def __init__(self, order: int, playerID: int):
        self.learningSpeed = DEFAULT_LEARNING_SPEED
        self.order = order
        self.confidenceLocked = False  # If true, confidence cannot be changed
        self.confidence = 1.0          # Degree to which current order determines behaviour
        self.playerID = playerID
        self.locationBeliefs: List[float] = []
        self.savedBeliefs: List[List[float]] = []
        self.saveCount = 0
        self.loc = 0
        self.lastAccuracy = 0.0
        self.mode = MODE_ALL_LOCATION  # MODE_ALL_LOCATION or MODE_ONE_LOCATION

        if self.order > 0:
            self.opponentModel = Agent(order - 1, 1 - playerID)
            self.opponentModel.confidenceLocked = True
            self.selfModel = Agent(order - 1, playerID)
        else:
            self.opponentModel = ToM0Model(playerID)
            self.selfModel = None

    def init(self, ctGame, playerID: int):
        """
        Initializes agent for a new game.
        Expects ctGame to provide: locations, utilityFunction, etc.
        """
        self.playerID = playerID
        self.loc = ctGame.locations[self.playerID]
        self.savedBeliefs = []
        self.saveCount = 0

        # Opponent model sees the opponent id
        self.opponentModel.init(ctGame, 1 - playerID)

        if self.order > 0:
            self.selfModel.init(ctGame, playerID)
            self.locationBeliefs = [1.0 / len(ctGame.utilityFunction) for _ in range(len(ctGame.utilityFunction))]
        else:
            # JS else-branch re-inits ToM0 with this player's ID
            self.opponentModel.init(ctGame, playerID)

    def saveBeliefs(self):
        """
        Saves beliefs to be restored later. Used by higher order agents to
        determine effect of certain offer on lower order partners.
        """
        if self.order > 0:
            self.savedBeliefs.append(self.locationBeliefs.copy())
            self.saveCount += 1
        self.opponentModel.saveBeliefs()

    def restoreBeliefs(self):
        """Restores previously saved beliefs."""
        self.saveCount -= 1
        if self.order > 0:
            self.locationBeliefs = self.savedBeliefs[self.saveCount].copy()
        self.opponentModel.restoreBeliefs()

    def getLocationBeliefs(self, location: int) -> float:
        """
        Returns the believed likelihood that the partner is in the given location.
        """
        if self.confidenceLocked:
            return self.locationBeliefs[location]
        if self.order == 0:
            return 1.0 / 12.0
        return (
            self.confidence * self.locationBeliefs[location]
            + (1 - self.confidence) * self.selfModel.getLocationBeliefs(location)
        )

    def informLocation(self, ctGame):
        """Informs the agent of the actual locations of the players."""
        self.loc = ctGame.locations[self.playerID]
        if self.order > 0:
            # Reset and set certainty on the observed opponent location
            self.locationBeliefs = [0.0 for _ in self.locationBeliefs]
            self.locationBeliefs[ctGame.locations[1 - self.playerID]] = 1.0
            self.selfModel.informLocation(ctGame)
            self.opponentModel.informLocation(ctGame)

    def getLocationValue(self, ctGame, offerToSelf: int) -> float:
        """
        Returns the value of making the given offer given the current setting of locations.
        """
        response = self.opponentModel.selectOffer(ctGame, ctGame.flipArray[offerToSelf])
        curValue = 0.0
        if response == ctGame.flipArray[offerToSelf]:
            # Partner accepts offer
            curValue += (
                ctGame.utilityFunction[self.loc][offerToSelf]
                - ctGame.utilityFunction[self.loc][ctGame.chipSets[self.playerID]]
                - 1
            )
        elif response != ctGame.chipSets[1 - self.playerID]:
            # Partner does not withdraw from negotiation
            response = ctGame.flipArray[response]
            curValue += max(
                -1,
                ctGame.utilityFunction[self.loc][response]
                - ctGame.utilityFunction[self.loc][ctGame.chipSets[self.playerID]]
                - 2,
            )
        return curValue

    def setLocation(self, newLocation: int):
        """Sets location of the other player."""
        self.loc = newLocation
        if self.order > 0:
            self.selfModel.setLocation(newLocation)
        else:
            self.opponentModel.loc = newLocation

    def getValue(self, ctGame, offerToSelf: int) -> float:
        """Returns value of making given offer."""
        # If not better than status quo, return -1
        if (
            ctGame.utilityFunction[self.loc][offerToSelf]
            <= ctGame.utilityFunction[self.loc][ctGame.chipSets[self.playerID]]
        ):
            return -1.0

        if self.order == 0:
            return self.opponentModel.getExpectedValue(ctGame, offerToSelf)

        curValue = 0.0
        if self.confidence > 0 or self.confidenceLocked:
            self.opponentModel.saveBeliefs()
            self.opponentModel.receiveOffer(ctGame, ctGame.flipArray[offerToSelf])

            if self.mode == MODE_ONE_LOCATION:
                # Choose among the max-probability locations
                bestLocs = [0]
                for l in range(1, len(self.locationBeliefs)):
                    if self.locationBeliefs[l] > self.locationBeliefs[bestLocs[0]] - PRECISION:
                        if self.locationBeliefs[l] > self.locationBeliefs[bestLocs[0]] + PRECISION:
                            bestLocs = []
                        bestLocs.append(l)
                l = random.choice(bestLocs)
                if self.locationBeliefs[l] > self.locationBeliefs[self.opponentModel.loc] + PRECISION:
                    self.opponentModel.setLocation(l)
                curValue = self.getLocationValue(ctGame, offerToSelf)
            else:
                # Expectation over all locations
                curValue = 0.0
                for l in range(len(self.locationBeliefs)):
                    if self.locationBeliefs[l] > 0:
                        self.opponentModel.setLocation(l)
                        curValue += self.locationBeliefs[l] * self.getLocationValue(ctGame, offerToSelf)

            self.opponentModel.restoreBeliefs()

        if self.confidence >= 1 or self.confidenceLocked:
            return curValue

        # Blend with self-model’s evaluation
        return self.confidence * curValue + (1 - self.confidence) * self.selfModel.getValue(ctGame, offerToSelf)

    def setID(self, newPlayerID: int):
        """Sets ID of this agent."""
        self.playerID = newPlayerID
        if self.order > 0:
            self.opponentModel.setID(1 - newPlayerID)
            self.selfModel.setID(newPlayerID)
        else:
            self.opponentModel.setID(newPlayerID)

    def observe(self, ctGame, offer: int, isAccepted: bool, playerID: int):
        """
        Observes given offer made by given player being accepted/rejected.
        """
        self.opponentModel.observe(ctGame, offer, isAccepted, playerID)
        if self.order > 0:
            self.selfModel.observe(ctGame, offer, isAccepted, playerID)
            if playerID != self.playerID and not self.confidenceLocked:
                denom = max(0.0, self.opponentModel.getBestValue(ctGame)) + 1.0
                num = max(0.0, self.opponentModel.getValue(ctGame, offer)) + 1.0
                target = (num / denom) if denom > 0 else 0.0
                self.confidence = (1 - self.learningSpeed) * self.confidence + self.learningSpeed * target

    def selectOffer(self, ctGame, offerToMe: int) -> int:
        """
        Select an offer to make, given the offer received.
        """
        allOffers = self.getValidOffers(ctGame, offerToMe)
        return random.choice(allOffers)

    def makeOffer(self, ctGame, offerToMe: int) -> int:
        """
        Observes the offer being made to this agent, selects an offer,
        and observes the choice for this offer being made.
        Returns the flipped code (as in the JS version).
        """
        self.receiveOffer(ctGame, offerToMe)
        choice = self.selectOffer(ctGame, offerToMe)
        self.sendOffer(ctGame, choice)
        return ctGame.flipArray[choice]

    def getBestValue(self, ctGame) -> float:
        """Returns the highest attainable score, according to this agent."""
        bestValue = 0.0
        for i in range(len(ctGame.utilityFunction[0])):
            value = self.getValue(ctGame, i)
            if value > bestValue + PRECISION:
                bestValue = value
        return max(0.0, bestValue)

    def getValidOffers(self, ctGame, offerToMe: int) -> List[int]:
        """
        Returns all offers that maximize expected utility.
        Mirrors the JS selection (including withdrawal logic and preferring partner's better offer).
        """
        allOffers: List[int] = []
        bestValue = 0.0

        for i in range(len(ctGame.utilityFunction[0])):
            value = self.getValue(ctGame, i)
            if value > bestValue - PRECISION:
                if value > bestValue + PRECISION:
                    allOffers = []
                    bestValue = value
                allOffers.append(i)

        # If partner's offer dominates, accept it
        if (
            offerToMe >= 0
            and ctGame.utilityFunction[self.loc][offerToMe]
            - ctGame.utilityFunction[self.loc][ctGame.chipSets[self.playerID]]
            > bestValue - PRECISION
        ):
            allOffers = [offerToMe]
            bestValue = (
                ctGame.utilityFunction[self.loc][offerToMe]
                - ctGame.utilityFunction[self.loc][ctGame.chipSets[self.playerID]]
            )

        # If nothing is good, withdraw (choose current chip set)
        if bestValue < PRECISION:
            allOffers = [ctGame.chipSets[self.playerID]]

        return allOffers

    def updateLocationBeliefs(self, ctGame, offerReceived: int):
        """
        Update beliefs concerning the location of the other player when observing the given offer being made.
        """
        offerToOther = ctGame.flipArray[offerReceived]
        accuracy = 0.0
        sumBeliefs = 0.0

        for l in range(len(self.locationBeliefs)):
            self.opponentModel.setLocation(l)

            # If offer is not better than opponent's status quo at l, discard
            if (
                ctGame.utilityFunction[l][offerToOther]
                <= ctGame.utilityFunction[l][ctGame.chipSets[1 - self.playerID]]
            ):
                self.locationBeliefs[l] = 0.0
            else:
                denom = max(0.0, self.opponentModel.getBestValue(ctGame)) + 1.0
                num = max(0.0, self.opponentModel.getValue(ctGame, offerToOther)) + 1.0
                factor = (num / denom) if denom > 0 else 0.0
                self.locationBeliefs[l] *= max(factor, 0.0)
                accuracy += self.locationBeliefs[l]

            sumBeliefs += self.locationBeliefs[l]

        # Normalize or reset to uniform (1/12) if degenerates
        if sumBeliefs > 0:
            inv = 1.0 / sumBeliefs
            for l in range(len(self.locationBeliefs)):
                self.locationBeliefs[l] *= inv
        else:
            self.locationBeliefs = [1.0 / 12.0 for _ in self.locationBeliefs]

        self.lastAccuracy = accuracy
        if not self.confidenceLocked:
            self.confidence = (1 - self.learningSpeed) * self.confidence + self.learningSpeed * accuracy

    def receiveOffer(self, ctGame, offerToMe: int):
        """Observe offer being made by other player."""
        if offerToMe >= 0:
            if self.order > 0:
                self.updateLocationBeliefs(ctGame, offerToMe)
                self.selfModel.receiveOffer(ctGame, offerToMe)
                self.opponentModel.sendOffer(ctGame, ctGame.flipArray[offerToMe])
            else:
                # Order-0: just record observation in ToM0
                self.opponentModel.observe(ctGame, offerToMe, True, 1 - self.playerID)

    def sendOffer(self, ctGame, offerToMe: int):
        """Observe offer being made by this agent."""
        if self.order > 0:
            self.selfModel.sendOffer(ctGame, offerToMe)
            self.opponentModel.receiveOffer(ctGame, ctGame.flipArray[offerToMe])
        else:
            # Order-0: record observation
            self.opponentModel.observe(ctGame, offerToMe, True, 1 - self.playerID)
