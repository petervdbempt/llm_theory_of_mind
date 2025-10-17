import random
from typing import List


# ------------------------------
# Helper functions (1:1 ports)
# ------------------------------

def convertCode(code: int, binMax: List[int]) -> List[int]:
    """
    Convert an integer 'code' into a per-color counts vector given binMax.
    Equivalent to mixed-radix decoding where radix_i = binMax[i] + 1.
    """
    chipsetArray = []
    for i in range(len(binMax)):
        base = binMax[i] + 1
        chipsetArray.append(code % base)
        code //= base
    return chipsetArray


def convertChips(chipsetArray: List[int], binMax: List[int]) -> int:
    """
    Convert a per-color counts vector to its integer code.
    Inverse of convertCode (mixed-radix encoding).
    """
    # JS starts from last element then goes backwards
    code = chipsetArray[-1]
    for i in range(len(chipsetArray) - 2, -1, -1):
        code = code * (binMax[i] + 1) + chipsetArray[i]
    return code


def getChipDifference(index1: int, index2: int, binMax: List[int]) -> List[int]:
    """
    Return per-color difference (index1 - index2) in chip counts.
    """
    bins1 = convertCode(index1, binMax)
    bins2 = convertCode(index2, binMax)
    for i in range(len(bins1)):
        bins1[i] -= bins2[i]
    return bins1


def invertCode(code: int, binMax: List[int]) -> int:
    """
    Given an offer code, return the flipped offer (other side of the trade).
    """
    chipsetArray = convertCode(code, binMax)
    for i in range(len(binMax)):
        chipsetArray[i] = binMax[i] - chipsetArray[i]
    return convertChips(chipsetArray, binMax)


def getNumberOfTokens(code: int, binMax: List[int]) -> int:
    """
    Count total tokens in an encoded chip vector.
    """
    chipsetArray = convertCode(code, binMax)
    return sum(chipsetArray)


# ------------------------------
# CT game scaffold (ported)
# ------------------------------

class CTgame:
    """
    Port of the JS CTgame 'class' and its bound methods.
    Exposes:
      - init()
      - calculateSetting()
      - getUtilityFunction(utilityFnc, finalLoc, binMax, x, y, nrOffers)
      - processLocation(scoreMatrix, locMatrix, binMax, x, y, nrOffers)

    Attributes expected/used by the ToM agents:
      - nColors, locations, chips, chipSets, flipArray,
        binMax, utilityFunction, finalLocation, board
    """

    def __init__(self):
        self.nColors = 5

        self.locations: List[int] = []           # two players’ locations (indices 0..11)
        self.goals: List[int] = []               # not used in the snippet, kept for parity
        self.chips: List[List[int]] = [[0]*self.nColors, [0]*self.nColors]
        self.chipSets: List[int] = [0, 0]        # encoded chip sets for both players
        self.flipArray: List[int] = []           # maps offer -> flipped offer
        self.unusedBoardColors: List[int] = []   # pool used to deal starting chips
        self.board: List[List[int]] = [[0]*5 for _ in range(5)]  # 5x5 color indices

        self.binMax: List[int] = [0]*self.nColors
        self.utilityFunction: List[List[int]] = []  # utilityFunction[location][offer_code]
        self.finalLocation: List[List[int]] = []    # finalLocation[location][offer_code]

    # --- Methods ---

    def getRandomBoardColor(self) -> int:
        """
        Pop a random color from the pool of unused board colors (mirrors string slicing in JS).
        """
        i = random.randrange(len(self.unusedBoardColors))
        return self.unusedBoardColors.pop(i)

    def init(self):
        """
        JS: initCTgame
        - Fill board with random colors (center is 0)
        - Build pool of colors seen on board (except center) for dealing chips
        - Deal 4 random board colors to each player (increment chip counts)
        - Calculate setting
        - Choose distinct starting locations for both players with a simple suitability check
        """
        # Build board and color pool
        self.unusedBoardColors = []
        for i in range(5):
            for j in range(5):
                if i == 2 and j == 2:
                    self.board[i][j] = 0
                else:
                    self.board[i][j] = random.randrange(self.nColors)
                    self.unusedBoardColors.append(self.board[i][j])

        # Reset chips
        for c in range(self.nColors):
            self.chips[0][c] = 0
            self.chips[1][c] = 0

        # Deal 4 chips per player from random board colors
        for _ in range(4):
            self.chips[0][self.getRandomBoardColor()] += 1
            self.chips[1][self.getRandomBoardColor()] += 1

        # Compute derived setting (binMax, offers, utilities...)
        self.calculateSetting()

        # Choose locations with up to 20 retries each, ensuring status-quo utility <= 0
        # Locations are grid positions with Manhattan distance > 2 from center (12 possibilities)
        # We index them 0..11 in the same way as JS builds them in calculateSetting.
        def status_ok(player_idx: int, loc_idx: int) -> bool:
            return self.utilityFunction[loc_idx][self.chipSets[player_idx]] <= 0

        while True:
            tries = 0
            # pick P0
            while True:
                tries += 1
                loc0 = random.randrange(12)
                if status_ok(0, loc0) or tries >= 20:
                    break

            tries = 0
            # pick P1
            while True:
                tries += 1
                loc1 = random.randrange(12)
                if status_ok(1, loc1) or tries >= 20:
                    break

            if loc0 != loc1:
                self.locations = [loc0, loc1]
                break

    def calculateSetting(self):
        """
        JS: calculateCTsetting
        - Compute binMax and total number of possible offers
        - Build flipArray (offer <-> inverted offer)
        - Encode chip sets
        - Fill utilityFunction and finalLocation for each enumerated location
        """
        # binMax is total tokens available per color (sum of both players’ tokens)
        nrOffers = 1
        for i in range(self.nColors):
            self.binMax[i] = self.chips[0][i] + self.chips[1][i]
            nrOffers *= (self.binMax[i] + 1)

        # flipArray maps offer code to its complement (what the other receives)
        self.flipArray = [invertCode(i, self.binMax) for i in range(nrOffers)]

        # Encode current chip sets for both players
        self.chipSets[0] = convertChips(self.chips[0], self.binMax)
        self.chipSets[1] = convertChips(self.chips[1], self.binMax)

        # Build utility and final location tables for the 12 valid locations
        self.utilityFunction = []
        self.finalLocation = []

        # Enumerate grid cells with Manhattan distance > 2 from center (2,2)
        # We fill in order j (rows) then k (cols), same as JS.
        for j in range(5):
            for k in range(5):
                if abs(j - 2) + abs(k - 2) > 2:
                    utilityFnc = [0] * nrOffers
                    finalLoc = [0] * nrOffers
                    self.getUtilityFunction(utilityFnc, finalLoc, self.binMax, j, k, nrOffers)
                    self.utilityFunction.append(utilityFnc)
                    self.finalLocation.append(finalLoc)

    def getUtilityFunction(self,
                           utilityFnc: List[int],
                           finalLoc: List[int],
                           binMax: List[int],
                           x: int, y: int,
                           nrOffers: int):
        """
        JS: getCTutilityFunction
        For a target (x, y), compute per-offer utility at the board center (2,2) after
        allowing moves that spend a token of the destination tile color (propagated via processLocation).
        """
        # Allocate [5][5][nrOffers]
        scoreMatrix = [[[0] * nrOffers for _ in range(5)] for __ in range(5)]
        locMatrix = [[[0] * nrOffers for _ in range(5)] for __ in range(5)]

        # Initialize base scores and default final locations
        for k in range(nrOffers):
            n = getNumberOfTokens(k, binMax)
            for i in range(5):
                for j in range(5):
                    # base score: +5 per token, -10 per Manhattan step from (x, y)
                    score = 5 * n - 10 * (abs(x - i) + abs(y - j))
                    if i == x and j == y:
                        score += 50  # bonus for reaching the goal cell
                    scoreMatrix[i][j][k] = score
                    locMatrix[i][j][k] = i * 5 + j  # encode location as single int

        # Relaxation/propagation step until no improvement
        doContinue = True
        while doContinue:
            doContinue = False
            for i in range(5):
                for j in range(5):
                    if self.processLocation(scoreMatrix, locMatrix, binMax, i, j, nrOffers):
                        doContinue = True

        # Extract utilities/final locations for the center cell (2,2) per offer code
        for i in range(nrOffers):
            utilityFnc[i] = scoreMatrix[2][2][i]
            finalLoc[i] = locMatrix[2][2][i]

    def processLocation(self,
                        scoreMatrix: List[List[List[int]]],
                        locMatrix: List[List[List[int]]],
                        binMax: List[int],
                        x: int, y: int,
                        nrOffers: int) -> bool:
        """
        JS: processCTlocation
        For each offer k, if we can pay one token matching color at (x,y),
        try to propagate the score at (x,y,k) to neighbors at the new code k2.
        """
        hasChanged = False
        cell_color = self.board[x][y]

        for k in range(nrOffers):
            bins = convertCode(k, binMax)
            if bins[cell_color] < binMax[cell_color]:
                bins[cell_color] += 1
                k2 = convertChips(bins, binMax)

                cur = scoreMatrix[x][y][k]

                # Up
                if x > 0 and scoreMatrix[x - 1][y][k2] < cur:
                    scoreMatrix[x - 1][y][k2] = cur
                    locMatrix[x - 1][y][k2] = locMatrix[x][y][k]
                    hasChanged = True

                # Left
                if y > 0 and scoreMatrix[x][y - 1][k2] < cur:
                    scoreMatrix[x][y - 1][k2] = cur
                    locMatrix[x][y - 1][k2] = locMatrix[x][y][k]
                    hasChanged = True

                # Down
                if x < 4 and scoreMatrix[x + 1][y][k2] < cur:
                    scoreMatrix[x + 1][y][k2] = cur
                    locMatrix[x + 1][y][k2] = locMatrix[x][y][k]
                    hasChanged = True

                # Right
                if y < 4 and scoreMatrix[x][y + 1][k2] < cur:
                    scoreMatrix[x][y + 1][k2] = cur
                    locMatrix[x][y + 1][k2] = locMatrix[x][y][k]
                    hasChanged = True

        return hasChanged
