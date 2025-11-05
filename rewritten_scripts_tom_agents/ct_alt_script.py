# ct_run.py
import random
from typing import List, Tuple, Dict, Any

# ------------------------------
# Helpers
# ------------------------------

def convertCode(code: int, binMax: List[int]) -> List[int]:
    out = []
    for i in range(len(binMax)):
        base = binMax[i] + 1
        out.append(code % base)
        code //= base
    return out

def convertChips(chipsetArray: List[int], binMax: List[int]) -> int:
    code = chipsetArray[-1]
    for i in range(len(chipsetArray) - 2, -1, -1):
        code = code * (binMax[i] + 1) + chipsetArray[i]
    return code

def invertCode(code: int, binMax: List[int]) -> int:
    v = convertCode(code, binMax)
    for i in range(len(v)):
        v[i] = binMax[i] - v[i]
    return convertChips(v, binMax)

def getChipDifference(index1: int, index2: int, binMax: List[int]) -> List[int]:
    a = convertCode(index1, binMax)
    b = convertCode(index2, binMax)
    return [ai - bi for ai, bi in zip(a, b)]

def getNumberOfTokens(code: int, binMax: List[int]) -> int:
    return sum(convertCode(code, binMax))

# ------------------------------
# CT game model
# ------------------------------

class CTgame:
    def __init__(self):
        self.nColors = 5
        self.locations: List[int] = [0, 0]   # index 0..11 (12 geldige locaties)
        self.goals: List[int] = []
        self.chips: List[List[int]] = [[0]*self.nColors, [0]*self.nColors]
        self.chipSets: List[int] = [0, 0]
        self.flipArray: List[int] = []
        self.unusedBoardColors: List[int] = []
        self.board: List[List[int]] = [[0]*5 for _ in range(5)]
        self.binMax: List[int] = [0]*self.nColors
        self.utilityFunction: List[List[int]] = []  # [loc][offer_code]
        self.finalLocation: List[List[int]] = []

    def getRandomBoardColor(self) -> int:
        i = random.randrange(len(self.unusedBoardColors))
        return self.unusedBoardColors.pop(i)

    def init(self):
        # Bord kleuren en pool
        self.unusedBoardColors = []
        for i in range(5):
            for j in range(5):
                if i == 2 and j == 2:
                    self.board[i][j] = 0
                else:
                    self.board[i][j] = random.randrange(self.nColors)
                    self.unusedBoardColors.append(self.board[i][j])
        # Chips reset + uitdelen
        for c in range(self.nColors):
            self.chips[0][c] = 0
            self.chips[1][c] = 0
        for _ in range(4):
            self.chips[0][self.getRandomBoardColor()] += 1
            self.chips[1][self.getRandomBoardColor()] += 1
        # Setting
        self.calculateSetting()
        # Kies startlocaties (status-quo utility <= 0) en niet gelijk
        def ok(pidx, loc):
            return self.utilityFunction[loc][self.chipSets[pidx]] <= 0
        while True:
            tries = 0
            while True:
                tries += 1
                l0 = random.randrange(12)
                if ok(0, l0) or tries >= 20:
                    break
            tries = 0
            while True:
                tries += 1
                l1 = random.randrange(12)
                if ok(1, l1) or tries >= 20:
                    break
            if l0 != l1:
                self.locations = [l0, l1]
                break

    def calculateSetting(self):
        nrOffers = 1
        for i in range(self.nColors):
            self.binMax[i] = self.chips[0][i] + self.chips[1][i]
            nrOffers *= (self.binMax[i] + 1)
        self.flipArray = [invertCode(i, self.binMax) for i in range(nrOffers)]
        self.chipSets[0] = convertChips(self.chips[0], self.binMax)
        self.chipSets[1] = convertChips(self.chips[1], self.binMax)
        self.utilityFunction = []
        self.finalLocation = []
        for j in range(5):
            for k in range(5):
                if abs(j - 2) + abs(k - 2) > 2:
                    util = [0]*nrOffers
                    finl = [0]*nrOffers
                    self.getUtilityFunction(util, finl, self.binMax, j, k, nrOffers)
                    self.utilityFunction.append(util)
                    self.finalLocation.append(finl)

    def getUtilityFunction(self, utilityFnc: List[int], finalLoc: List[int],
                           binMax: List[int], x: int, y: int, nrOffers: int):
        scoreM = [[[0]*nrOffers for _ in range(5)] for __ in range(5)]
        locM   = [[[0]*nrOffers for _ in range(5)] for __ in range(5)]
        for k in range(nrOffers):
            n = getNumberOfTokens(k, binMax)
            for i in range(5):
                for j in range(5):
                    s = 5*n - 10*(abs(x-i) + abs(y-j))
                    if i == x and j == y:
                        s += 50
                    scoreM[i][j][k] = s
                    locM[i][j][k] = i*5 + j
        changed = True
        while changed:
            changed = False
            for i in range(5):
                for j in range(5):
                    if self.processLocation(scoreM, locM, binMax, i, j, nrOffers):
                        changed = True
        for i in range(nrOffers):
            utilityFnc[i] = scoreM[2][2][i]
            finalLoc[i]   = locM[2][2][i]

    def processLocation(self, scoreM, locM, binMax, x, y, nrOffers) -> bool:
        hasChanged = False
        color = self.board[x][y]
        for k in range(nrOffers):
            bins = convertCode(k, binMax)
            if bins[color] < binMax[color]:
                bins[color] += 1
                k2 = convertChips(bins, binMax)
                cur = scoreM[x][y][k]
                if x > 0 and scoreM[x-1][y][k2] < cur:
                    scoreM[x-1][y][k2] = cur; locM[x-1][y][k2] = locM[x][y][k]; hasChanged = True
                if y > 0 and scoreM[x][y-1][k2] < cur:
                    scoreM[x][y-1][k2] = cur; locM[x][y-1][k2] = locM[x][y][k]; hasChanged = True
                if x < 4 and scoreM[x+1][y][k2] < cur:
                    scoreM[x+1][y][k2] = cur; locM[x+1][y][k2] = locM[x][y][k]; hasChanged = True
                if y < 4 and scoreM[x][y+1][k2] < cur:
                    scoreM[x][y+1][k2] = cur; locM[x][y+1][k2] = locM[x][y][k]; hasChanged = True
        return hasChanged

# ------------------------------
# ToM Agents
# ------------------------------

DEFAULT_LEARNING_SPEED = 0.8
PRECISION = 1e-5
MODE_ONE_LOCATION = 0
MODE_ALL_LOCATION = 1

class ToM0Model:
    def __init__(self, playerID: int):
        self.playerID = playerID
        self.loc = 0
        self.learningSpeed = DEFAULT_LEARNING_SPEED
        self.savedBeliefs: List[List[float]] = []
        self.saveCount = 0
        self.cntBeliefs = [
            [5,5,5,5,5,5,5,5,5],
            [14,248,407,5,5,5,5,5,5],
            [26,316,196,129,5,5,5,5,5],
            [28,19,194,62,24,5,5,5,5],
            [26,27,18,19,10,5,5,5,5],
            [5,5,5,5,5,5,5,5,5],
            [5,5,5,5,5,5,5,5,5],
            [5,5,5,5,5,5,5,5,5],
            [5,5,5,5,5,5,5,5,5],
        ]
        self.ttlBeliefs = [
            [226,25,27,34,45,5,5,5,5],
            [14,495,912,26,34,5,5,5,5],
            [26,566,392,289,23,5,5,5,5],
            [28,19,345,122,55,5,5,5,5],
            [26,27,18,32,17,5,5,5,5],
            [5,5,5,5,5,5,5,5,5],
            [5,5,5,5,5,5,5,5,5],
            [5,5,5,5,5,5,5,5,5],
            [5,5,5,5,5,5,5,5,5],
        ]
        self.beliefOffer: List[float] = []

    def init(self, ctGame: CTgame, playerID: int):
        self.playerID = playerID
        self.beliefOffer = []
        for i in range(len(ctGame.utilityFunction[self.playerID])):
            self.beliefOffer.append(self.getAcceptanceRate(ctGame, i))
        self.saveCount = 0
        self.savedBeliefs = []

    def saveBeliefs(self):
        self.savedBeliefs.append(self.beliefOffer.copy())
        self.saveCount += 1

    def restoreBeliefs(self):
        self.saveCount -= 1
        self.beliefOffer = self.savedBeliefs[self.saveCount].copy()

    def observe(self, ctGame: CTgame, offer: int, isAccepted: bool, playerID: int):
        pos = 0; neg = 0
        diff = getChipDifference(ctGame.chipSets[self.playerID], offer, ctGame.binMax)
        for d in diff:
            if d > 0: pos += d
            else:     neg -= d
        self.ttlBeliefs[pos][neg] += 1
        if playerID != self.playerID:
            self.cntBeliefs[pos][neg] += 1
            self.increaseColorBelief(ctGame, offer)
        elif isAccepted:
            self.cntBeliefs[pos][neg] += 1
        else:
            self.decreaseColorBelief(ctGame, offer)

    def increaseColorBelief(self, ctGame: CTgame, newOwnChips: int):
        newBins = convertCode(newOwnChips, ctGame.binMax)
        for i in range(len(self.beliefOffer)):
            curOffer = convertCode(i, ctGame.binMax)
            if any(cj > nj for cj, nj in zip(curOffer, newBins)):
                self.beliefOffer[i] *= (1 - self.learningSpeed)

    def decreaseColorBelief(self, ctGame: CTgame, newOwnChips: int):
        newBins = convertCode(newOwnChips, ctGame.binMax)
        for i in range(len(self.beliefOffer)):
            curOffer = convertCode(i, ctGame.binMax)
            if all(cj >= nj for cj, nj in zip(curOffer, newBins)):
                self.beliefOffer[i] *= (1 - self.learningSpeed)

    def getAcceptanceRate(self, ctGame: CTgame, offer: int) -> float:
        pos = 0; neg = 0
        diff = getChipDifference(ctGame.chipSets[self.playerID], offer, ctGame.binMax)
        for d in diff:
            if d > 0: pos += d
            else:     neg -= d
        denom = self.ttlBeliefs[pos][neg]
        return (self.cntBeliefs[pos][neg] / denom) if denom > 0 else 0.0

    def getExpectedValue(self, ctGame: CTgame, offer: int) -> float:
        return self.beliefOffer[offer] * ctGame.utilityFunction[self.loc][offer]

    def setID(self, newPlayerID: int):
        self.playerID = newPlayerID

class Agent:
    def __init__(self, order: int, playerID: int):
        self.learningSpeed = DEFAULT_LEARNING_SPEED
        self.order = order
        self.confidenceLocked = False
        self.confidence = 1.0
        self.playerID = playerID
        self.locationBeliefs: List[float] = []
        self.savedBeliefs: List[List[float]] = []
        self.saveCount = 0
        self.loc = 0
        self.lastAccuracy = 0.0
        self.mode = MODE_ALL_LOCATION
        if self.order > 0:
            self.opponentModel = Agent(order - 1, 1 - playerID)
            self.opponentModel.confidenceLocked = True
            self.selfModel = Agent(order - 1, playerID)
        else:
            self.opponentModel = ToM0Model(playerID)
            self.selfModel = None

    def init(self, ctGame: CTgame, playerID: int):
        self.playerID = playerID
        self.loc = ctGame.locations[self.playerID]
        self.savedBeliefs = []
        self.saveCount = 0
        self.opponentModel.init(ctGame, 1 - playerID)
        if self.order > 0:
            self.selfModel.init(ctGame, playerID)
            self.locationBeliefs = [1.0/len(ctGame.utilityFunction) for _ in range(len(ctGame.utilityFunction))]
        else:
            self.opponentModel.init(ctGame, playerID)

    def saveBeliefs(self):
        if self.order > 0:
            self.savedBeliefs.append(self.locationBeliefs.copy())
            self.saveCount += 1
        self.opponentModel.saveBeliefs()

    def restoreBeliefs(self):
        self.saveCount -= 1
        if self.order > 0:
            self.locationBeliefs = self.savedBeliefs[self.saveCount].copy()
        self.opponentModel.restoreBeliefs()

    def getLocationBeliefs(self, location: int) -> float:
        if self.confidenceLocked:
            return self.locationBeliefs[location]
        if self.order == 0:
            return 1.0/12.0
        return self.confidence*self.locationBeliefs[location] + (1-self.confidence)*self.selfModel.getLocationBeliefs(location)

    def informLocation(self, ctGame: CTgame):
        self.loc = ctGame.locations[self.playerID]
        if self.order > 0:
            self.locationBeliefs = [0.0 for _ in self.locationBeliefs]
            self.locationBeliefs[ctGame.locations[1 - self.playerID]] = 1.0
            self.selfModel.informLocation(ctGame)
            self.opponentModel.informLocation(ctGame)

    def getLocationValue(self, ctGame: CTgame, offerToSelf: int) -> float:
        response = self.opponentModel.selectOffer(ctGame, ctGame.flipArray[offerToSelf])
        curValue = 0.0
        if response == ctGame.flipArray[offerToSelf]:
            curValue += ctGame.utilityFunction[self.loc][offerToSelf] - ctGame.utilityFunction[self.loc][ctGame.chipSets[self.playerID]] - 1
        elif response != ctGame.chipSets[1 - self.playerID]:
            response = ctGame.flipArray[response]
            curValue += max(-1, ctGame.utilityFunction[self.loc][response] - ctGame.utilityFunction[self.loc][ctGame.chipSets[self.playerID]] - 2)
        return curValue

    def setLocation(self, newLocation: int):
        self.loc = newLocation
        if self.order > 0:
            self.selfModel.setLocation(newLocation)
        else:
            self.opponentModel.loc = newLocation

    def getValue(self, ctGame: CTgame, offerToSelf: int) -> float:
        if ctGame.utilityFunction[self.loc][offerToSelf] <= ctGame.utilityFunction[self.loc][ctGame.chipSets[self.playerID]]:
            return -1.0
        if self.order == 0:
            return self.opponentModel.getExpectedValue(ctGame, offerToSelf)
        curValue = 0.0
        if self.confidence > 0 or self.confidenceLocked:
            self.opponentModel.saveBeliefs()
            self.opponentModel.receiveOffer(ctGame, ctGame.flipArray[offerToSelf])
            if self.mode == MODE_ONE_LOCATION:
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
                curValue = 0.0
                for l in range(len(self.locationBeliefs)):
                    if self.locationBeliefs[l] > 0:
                        self.opponentModel.setLocation(l)
                        curValue += self.locationBeliefs[l]*self.getLocationValue(ctGame, offerToSelf)
            self.opponentModel.restoreBeliefs()
        if self.confidence >= 1 or self.confidenceLocked:
            return curValue
        return self.confidence*curValue + (1-self.confidence)*self.selfModel.getValue(ctGame, offerToSelf)

    def setID(self, newPlayerID: int):
        self.playerID = newPlayerID
        if self.order > 0:
            self.opponentModel.setID(1 - newPlayerID)
            self.selfModel.setID(newPlayerID)
        else:
            self.opponentModel.setID(newPlayerID)

    def observe(self, ctGame: CTgame, offer: int, isAccepted: bool, playerID: int):
        self.opponentModel.observe(ctGame, offer, isAccepted, playerID)
        if self.order > 0:
            self.selfModel.observe(ctGame, offer, isAccepted, playerID)
            if playerID != self.playerID and not self.confidenceLocked:
                denom = max(0.0, self.opponentModel.getBestValue(ctGame)) + 1.0
                num = max(0.0, self.opponentModel.getValue(ctGame, offer)) + 1.0
                target = (num/denom) if denom > 0 else 0.0
                self.confidence = (1 - self.learningSpeed)*self.confidence + self.learningSpeed*target

    def selectOffer(self, ctGame: CTgame, offerToMe: int) -> int:
        allOffers = self.getValidOffers(ctGame, offerToMe)
        return random.choice(allOffers)

    def makeOffer(self, ctGame: CTgame, offerToMe: int) -> int:
        self.receiveOffer(ctGame, offerToMe)
        choice = self.selectOffer(ctGame, offerToMe)
        self.sendOffer(ctGame, choice)
        return ctGame.flipArray[choice]

    def getBestValue(self, ctGame: CTgame) -> float:
        bestValue = 0.0
        for i in range(len(ctGame.utilityFunction[0])):
            v = self.getValue(ctGame, i)
            if v > bestValue + PRECISION:
                bestValue = v
        return max(0.0, bestValue)

    def getValidOffers(self, ctGame: CTgame, offerToMe: int) -> List[int]:
        allOffers: List[int] = []
        bestValue = 0.0
        for i in range(len(ctGame.utilityFunction[0])):
            v = self.getValue(ctGame, i)
            if v > bestValue - PRECISION:
                if v > bestValue + PRECISION:
                    allOffers = []
                    bestValue = v
                allOffers.append(i)
        if offerToMe >= 0 and ctGame.utilityFunction[self.loc][offerToMe] - ctGame.utilityFunction[self.loc][ctGame.chipSets[self.playerID]] > bestValue - PRECISION:
            allOffers = [offerToMe]
            bestValue = ctGame.utilityFunction[self.loc][offerToMe] - ctGame.utilityFunction[self.loc][ctGame.chipSets[self.playerID]]
        if bestValue < PRECISION:
            allOffers = [ctGame.chipSets[self.playerID]]
        return allOffers

    def updateLocationBeliefs(self, ctGame: CTgame, offerReceived: int):
        offerToOther = ctGame.flipArray[offerReceived]
        accuracy = 0.0
        sumB = 0.0
        for l in range(len(self.locationBeliefs)):
            self.opponentModel.setLocation(l)
            if ctGame.utilityFunction[l][offerToOther] <= ctGame.utilityFunction[l][ctGame.chipSets[1 - self.playerID]]:
                self.locationBeliefs[l] = 0.0
            else:
                denom = max(0.0, self.opponentModel.getBestValue(ctGame)) + 1.0
                num = max(0.0, self.opponentModel.getValue(ctGame, offerToOther)) + 1.0
                factor = (num/denom) if denom > 0 else 0.0
                self.locationBeliefs[l] *= max(factor, 0.0)
                accuracy += self.locationBeliefs[l]
            sumB += self.locationBeliefs[l]
        if sumB > 0:
            inv = 1.0/sumB
            for l in range(len(self.locationBeliefs)):
                self.locationBeliefs[l] *= inv
        else:
            self.locationBeliefs = [1.0/12.0 for _ in self.locationBeliefs]
        self.lastAccuracy = accuracy
        if not self.confidenceLocked:
            self.confidence = (1 - self.learningSpeed)*self.confidence + self.learningSpeed*accuracy

    def receiveOffer(self, ctGame: CTgame, offerToMe: int):
        if offerToMe >= 0:
            if self.order > 0:
                self.updateLocationBeliefs(ctGame, offerToMe)
                self.selfModel.receiveOffer(ctGame, offerToMe)
                self.opponentModel.sendOffer(ctGame, ctGame.flipArray[offerToMe])
            else:
                self.opponentModel.observe(ctGame, offerToMe, True, 1 - self.playerID)

    def sendOffer(self, ctGame: CTgame, offerToMe: int):
        if self.order > 0:
            self.selfModel.sendOffer(ctGame, offerToMe)
            self.opponentModel.receiveOffer(ctGame, ctGame.flipArray[offerToMe])
        else:
            self.opponentModel.observe(ctGame, offerToMe, True, 1 - self.playerID)

# ------------------------------
# Headless controller (CLI)
# ------------------------------

class CTRunner:
    def __init__(self, agent_orders: Tuple[int, int] = (2, 2), seed: int | None = None):
        if seed is not None:
            random.seed(seed)
        self.ct = CTgame()
        self.agents: List[List[Agent]] = [
            [Agent(0, 0), Agent(1, 0), Agent(2, 0)],
            [Agent(0, 1), Agent(1, 1), Agent(2, 1)],
        ]
        self.agentLevels: List[int] = [agent_orders[0], agent_orders[1]]  # -1 = human
        self.round: int = -1
        self.currentOffer: int = -1
        self.scores: List[int] = [0, 0]
        self.accuracies: List[float] = [0.0, 0.0, 0.0, 0.0]
        self.totalRounds: List[int] = [0, 0]

    def reset_game(self):
        self.scores = [0, 0]
        self.accuracies = [0.0, 0.0, 0.0, 0.0]
        self.totalRounds = [0, 0]
        return self.init_game()

    def init_game(self):
        self.ct.init()
        for i in range(3):
            self.agents[0][i].init(self.ct, 0)
            self.agents[0][i].setLocation(self.ct.locations[0])
            self.agents[1][i].init(self.ct, 1)
            self.agents[1][i].setLocation(self.ct.locations[1])
        self.round = 0
        self.currentOffer = -1
        return {"round": self.round, "locations": tuple(self.ct.locations), "chipSets": tuple(self.ct.chipSets)}

    def end_game(self, offer_from_initiator_view: int) -> Dict[str, Any]:
        self.scores[0] += self.ct.utilityFunction[self.ct.locations[0]][offer_from_initiator_view]
        self.scores[1] += self.ct.utilityFunction[self.ct.locations[1]][self.ct.flipArray[offer_from_initiator_view]]
        self.round = -1
        return {"scores": tuple(self.scores), "final_offer": offer_from_initiator_view, "locations": tuple(self.ct.locations)}

    def _apply_offer_observation(self, offer_to_other: int, cur: int):
        other = 1 - cur
        for i in range(3):
            self.agents[cur][i].sendOffer(self.ct, offer_to_other)
            self.agents[other][i].receiveOffer(self.ct, self.ct.flipArray[offer_to_other])
        self.accuracies[2*other+0] += self.agents[other][1].lastAccuracy
        self.accuracies[2*other+1] += self.agents[other][2].lastAccuracy
        self.totalRounds[other] += 1

    def play_round(self) -> Dict[str, Any]:
        if self.round < 0:
            return self.init_game()
        cur = self.round % 2
        lvl = self.agentLevels[cur]
        if lvl < 0:
            return {"status": "awaiting_human", "round": self.round, "player": cur}
        new_offer_to_other = self.agents[cur][lvl].selectOffer(self.ct, self.currentOffer)
        self._apply_offer_observation(new_offer_to_other, cur)
        public_view = self.ct.flipArray[new_offer_to_other]
        # accept?
        if public_view == self.ct.flipArray[self.currentOffer]:
            scoring_offer = self.currentOffer if (cur == 0) else public_view
            end = self.end_game(scoring_offer)
            return {"action": "accepted", **end}
        # withdraw/timeout?
        if public_view == self.ct.chipSets[1 - cur] or self.round > 38:
            end = self.end_game(self.ct.chipSets[0])
            return {"action": "withdraw_or_timeout", **end}
        # continue
        self.round += 1
        self.currentOffer = public_view
        return {"action": "agent_offer", "round": self.round, "offer_public": public_view}

    def human_offer_bins(self, bins_for_self: List[int]) -> Dict[str, Any]:
        if self.round < 0:
            self.init_game()
        cur = self.round % 2
        if self.agentLevels[cur] >= 0:
            return {"error": "not human turn"}
        # Validatie
        if len(bins_for_self) != self.ct.nColors:
            return {"error": f"expected {self.ct.nColors} integers"}
        for i, v in enumerate(bins_for_self):
            if v < 0 or v > self.ct.binMax[i]:
                return {"error": f"bin {i} out of range 0..{self.ct.binMax[i]}"}
        # Encode & transform naar 'offer to other'
        offer_code_self = convertChips(bins_for_self, self.ct.binMax)
        new_offer_to_other = self.ct.flipArray[offer_code_self]
        # gelijk aan vorige -> accept
        if new_offer_to_other == self.ct.flipArray[self.currentOffer]:
            scoring_offer = self.currentOffer if (cur == 0) else self.ct.flipArray[self.currentOffer]
            end = self.end_game(scoring_offer)
            return {"action": "accepted", **end}
        # withdraw?
        if new_offer_to_other == self.ct.chipSets[1 - cur]:
            end = self.end_game(self.ct.chipSets[0])
            return {"action": "withdraw", **end}
        # anders voortzetten
        self._apply_offer_observation(new_offer_to_other, cur)
        self.round += 1
        self.currentOffer = self.ct.flipArray[new_offer_to_other]
        return {"action": "human_offer", "round": self.round, "offer_public": self.currentOffer}

    def human_accept(self) -> Dict[str, Any]:
        if self.round < 0:
            return {"error": "no active game"}
        cur = self.round % 2
        scoring_offer = self.currentOffer if (cur == 0) else self.ct.flipArray[self.currentOffer]
        end = self.end_game(scoring_offer)
        return {"action": "accepted", **end}

    def human_withdraw(self) -> Dict[str, Any]:
        if self.round < 0:
            return {"error": "no active game"}
        end = self.end_game(self.ct.chipSets[0])
        return {"action": "withdraw", **end}

# ------------------------------
# Simple CLI
# ------------------------------

def pretty_vec(v: List[int]) -> str:
    names = ["W", "B", "P", "Gry", "Y"]
    return "[" + ", ".join(f"{n}:{x}" for n, x in zip(names, v)) + "]"

def main():
    print("=== Colored Trails (CLI) ===")
    try:
        a0 = int(input("Initiator ToM level (0/1/2 or -1 for Human) [2]: ") or "2")
        a1 = int(input("Responder ToM level (0/1/2 or -1 for Human) [2]: ") or "2")
    except Exception:
        a0, a1 = 2, 2

    runner = CTRunner(agent_orders=(a0, a1), seed=None)
    st = runner.init_game()
    print(f"New game. Locations (I,R): {runner.ct.locations}")
    print(f"binMax per color: {runner.ct.binMax}")
    print(f"Initiator chips: {pretty_vec(convertCode(runner.ct.chipSets[0], runner.ct.binMax))}")
    print(f"Responder chips: {pretty_vec(convertCode(runner.ct.chipSets[1], runner.ct.binMax))}")
    print("Type 'help' tijdens je beurt voor opties.\n")

    while True:
        if runner.round < 0:
            print(f"Game over. Scores (I,R): {runner.scores}.")
            again = input("Play again? [y/N]: ").strip().lower()
            if again == "y":
                runner.reset_game()
                print(f"\nNew game. Locations (I,R): {runner.ct.locations}")
                print(f"binMax: {runner.ct.binMax}")
                print(f"Initiator chips: {pretty_vec(convertCode(runner.ct.chipSets[0], runner.ct.binMax))}")
                print(f"Responder chips: {pretty_vec(convertCode(runner.ct.chipSets[1], runner.ct.binMax))}")
                continue
            break

        cur = runner.round % 2
        who = "Initiator" if cur == 0 else "Responder"
        print(f"\n--- Round {runner.round} | Turn: {who} ---")

        if runner.agentLevels[cur] >= 0:
            res = runner.play_round()
            if "action" in res:
                if res["action"] == "agent_offer":
                    offer_bins = convertCode(res["offer_public"], runner.ct.binMax)
                    print(f"Agent offers -> public view bins: {pretty_vec(offer_bins)}")
                elif res["action"] in ("accepted", "withdraw_or_timeout"):
                    print(f"End: {res['action']}. Final scores (I,R): {runner.scores}")
            else:
                # awaiting_human (shouldn't happen here)
                pass
        else:
            # Human turn
            print("Your options:")
            print(" - Type 5 ints (e.g. '1 0 2 1 0') = your chips after the trade (must respect binMax)")
            print(" - 'accept'  to accept the last opponent offer")
            print(" - 'withdraw' to withdraw (end with status quo)")
            print(" - 'show' to show current info")
            cmd = input("> ").strip().lower()
            if cmd == "help":
                continue
            if cmd == "show":
                print(f"binMax: {runner.ct.binMax}")
                print(f"Your current chips: {pretty_vec(convertCode(runner.ct.chipSets[cur], runner.ct.binMax))}")
                print(f"Opp. current chips: {pretty_vec(convertCode(runner.ct.chipSets[1-cur], runner.ct.binMax))}")
                if runner.currentOffer >= 0:
                    print(f"Last public offer bins: {pretty_vec(convertCode(runner.currentOffer, runner.ct.binMax))}")
                continue
            if cmd == "accept":
                res = runner.human_accept()
                print(f"Accepted. Scores (I,R): {runner.scores}")
                continue
            if cmd == "withdraw":
                res = runner.human_withdraw()
                print(f"Withdrawn. Scores (I,R): {runner.scores}")
                continue
            try:
                bins = [int(x) for x in cmd.split()]
                res = runner.human_offer_bins(bins)
                if "error" in res:
                    print("Error:", res["error"])
                else:
                    if res["action"] == "human_offer":
                        print(f"Offer registered. Public view bins: {pretty_vec(convertCode(res['offer_public'], runner.ct.binMax))}")
                    else:
                        print(f"End: {res['action']}. Scores (I,R): {runner.scores}")
            except Exception as e:
                print("Could not parse. Type 'help' for options.")

if __name__ == "__main__":
    main()
