function getChipDifference(index1, index2, binMax) {
  var bins1, bins2, i;
  bins1 = convertCode(index1, binMax);
  bins2 = convertCode(index2, binMax);
  for (i = 0; i < bins1.length; ++i) {
    bins1[i] -= bins2[i];
  }
  return bins1;
}

function invertCode(code, binMax) {
  var chipsetArray, i;
  chipsetArray = convertCode(code, binMax);
  for (i = 0; i < binMax.length; ++i) {
    chipsetArray[i] = binMax[i] - chipsetArray[i];
  }
  return convertChips(chipsetArray, binMax);
}

function getNumberOfTokens(code, binMax) {
  var chipsetArray, acc, i;
  chipsetArray = convertCode(code, binMax);
  acc = 0;
  for (i = 0; i < chipsetArray.length; ++i) {
    acc += chipsetArray[i];
  }
  return acc;
}

function convertCode(code, binMax) {
  var chipsetArray, i;
  chipsetArray = new Array();
  for (i = 0; i < binMax.length; ++i) {
    chipsetArray[i] = code % (binMax[i] + 1);
    code = Math.floor(code / (binMax[i] + 1));
  }
  return chipsetArray;
}

function convertChips(chipsetArray, binMax) {
  var code, i;
  code = chipsetArray[chipsetArray.length-1];
  for (i = chipsetArray.length-2; i >= 0; --i) {
    code = code*(binMax[i] + 1) + chipsetArray[i];
  }
  return code;
}

function getRandomBoardColor(ctGame) {
  var i, n;
  i = Math.floor(Math.random()*ctGame.unusedBoardColors.length);
  n = ctGame.unusedBoardColors.charAt(i);
  ctGame.unusedBoardColors = ctGame.unusedBoardColors.substr(0,i) + ctGame.unusedBoardColors.substr(i+1);
  return n*1;
}

function initCTgame() {
  var i,j;
  this.unusedBoardColors = "";
  for (i = 0; i < 5; ++i) {
    for (j = 0; j < 5; ++j) {
      if (i == 2 && j == 2) {
        this.board[i][j] = 0;
      } else {
        this.board[i][j] = Math.floor(Math.random()*this.nColors);
        this.unusedBoardColors += ""+this.board[i][j];
      }
    }
  }
  for (i = 0; i < this.nColors; ++i) {
    this.chips[0][i] = 0;
    this.chips[1][i] = 0;
  }
  for (i = 0; i < 4; ++i) {
    this.chips[0][getRandomBoardColor(this)]++;
    this.chips[1][getRandomBoardColor(this)]++;
  }
  this.calculateSetting();
  do {
    i = 0;
    do {
      i++;
      this.locations[0] = Math.floor(Math.random()*12);
    } while (i < 20 && this.utilityFunction[this.locations[0]][this.chipSets[0]] > 0);
    i = 0;
    do {
      i++;
      this.locations[1] =  Math.floor(Math.random()*12);
    } while (i < 20 && this.utilityFunction[this.locations[1]][this.chipSets[1]] > 0);
  } while (this.locations[0] == this.locations[1]);
}

function calculateCTsetting() {
  var i,j,k,n, nrOffers;
  nrOffers = 1;
  for (i = 0; i < this.nColors; ++i) {
    this.binMax[i] = this.chips[0][i]+this.chips[1][i];
    nrOffers *= (this.binMax[i] + 1);
  }
  this.flipArray = new Array();
  for (i = 0; i < nrOffers; ++i) {
    this.flipArray[i] = invertCode(i, this.binMax);
  }
  this.chipSets[0] = convertChips(this.chips[0], this.binMax);
  this.chipSets[1] = convertChips(this.chips[1], this.binMax);
  n = 0;
  for (j = 0; j < 5; ++j) {
    for (k = 0; k < 5; ++k) {
      if (Math.abs(j-2) + Math.abs(k-2) > 2) {
        this.utilityFunction[n] = new Array();
        this.finalLocation[n] = new Array();
        this.getUtilityFunction(this.utilityFunction[n], this.finalLocation[n], this.binMax, j, k, nrOffers);
        n++;
      }
    }
  }
}

function getCTutilityFunction(utilityFnc, finalLoc, binMax, x, y, nrOffers) {
  var scoreMatrix, locMatrix, i, j, k, n, doContinue;
  scoreMatrix = new Array();
  locMatrix = new Array();
  for (i = 0; i < 5; ++i) {
    scoreMatrix[i] = new Array();
    locMatrix[i] = new Array();
    for (j = 0; j < 5; ++j) {
      scoreMatrix[i][j] = new Array();
      locMatrix[i][j] = new Array();
    }
  }
  for (k = 0; k < nrOffers; ++k) {
    n = getNumberOfTokens(k, binMax);
    for (i = 0; i < 5; ++i) {
      for (j = 0; j < 5; ++j) {
        scoreMatrix[i][j][k] = 5*n - 10*(Math.abs(x-i) + Math.abs(y-j));
        locMatrix[i][j][k] = i*5+j;
        if (i == x && j == y) {
          scoreMatrix[i][j][k] += 50;
        }
      }
    }
  }
  doContinue = true;
  while (doContinue) {
    doContinue = false;
    for (i = 0; i < 5; ++i) {
      for (j = 0; j < 5; ++j) {
        doContinue = doContinue || this.processLocation(scoreMatrix, locMatrix, binMax, i, j, nrOffers);
      }
    }
  }
  for (i = 0; i < nrOffers; ++i) {
    utilityFnc[i] = scoreMatrix[2][2][i];
    finalLoc[i] = locMatrix[2][2][i];
  }
}


function processCTlocation(scoreMatrix, locMatrix, binMax, x, y, nrOffers) {
  var k, k2, bins, hasChanged;
  hasChanged = false;
  for (k = 0; k < nrOffers; ++k) {
    bins = convertCode(k, binMax);
    if (bins[this.board[x][y]] < binMax[this.board[x][y]]) {
      bins[this.board[x][y]]++;
      k2 = convertChips(bins, binMax);
      if (x > 0 && scoreMatrix[x-1][y][k2] < scoreMatrix[x][y][k]) {
        // Moving from (x-1,y) to (x,y) by handing in a token is beneficial
        scoreMatrix[x-1][y][k2] = scoreMatrix[x][y][k];
        locMatrix[x-1][y][k2] = locMatrix[x][y][k];
        hasChanged = true;
      }
      if (y > 0 && scoreMatrix[x][y-1][k2] < scoreMatrix[x][y][k]) {
        scoreMatrix[x][y-1][k2] = scoreMatrix[x][y][k];
        locMatrix[x][y-1][k2] = locMatrix[x][y][k];
        hasChanged = true;
      }
      if (x < 4 && scoreMatrix[x+1][y][k2] < scoreMatrix[x][y][k]) {
        scoreMatrix[x+1][y][k2] = scoreMatrix[x][y][k];
        locMatrix[x+1][y][k2] = locMatrix[x][y][k];
        hasChanged = true;
      }
      if (y < 4 && scoreMatrix[x][y+1][k2] < scoreMatrix[x][y][k]) {
        scoreMatrix[x][y+1][k2] = scoreMatrix[x][y][k];
        locMatrix[x][y+1][k2] = locMatrix[x][y][k];
        hasChanged = true;
      }
    }
  }
  return hasChanged;
}


function CTgame() {
  var i;
  this.nColors = 5;

  this.locations = new Array();
  this.goals = new Array();
  this.chips = new Array(new Array(),new Array());
  this.chipSets = new Array();
  this.flipArray = new Array();
  this.unusedBoardColors;
  this.board = new Array();
  for (i = 0; i < 5; ++i) {
    this.board[i] = new Array();
  }

  this.init = initCTgame;
  this.calculateSetting = calculateCTsetting;
  this.getUtilityFunction = getCTutilityFunction;
  this.processLocation = processCTlocation;

  this.binMax = new Array();
  this.utilityFunction = new Array();
  this.finalLocation = new Array();
}

