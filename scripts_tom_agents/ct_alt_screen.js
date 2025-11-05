//-------------------------------------------------------------------------------------------- VARIABLES
boardColors = new Array("white","black","purple","gray","yellow");
	// Color codes of the game colors.
revealGoals = false;
	// Reveal the goals to all players each round
showOfferHelper = false;
	// Immediately shows the effect of possible offers when changing the current offer

//-------------------------------------------------------------------------------------------- CONSTANTS
// Note: changing these variables will result in errors.

goalLocations = new Array("board0_0","board0_1","board0_3","board0_4","board1_0","board1_4","board3_0","board3_4","board4_0","board4_1","board4_3","board4_4");
goalLocationArray = new Array(0,1,3,4,5,9,15,19,20,21,23,24);
offerPanel = new Array();
agentLevels = new Array(2,2);
timerEnabled = 0;
round = -1;
currentOffer = -1;
scores = new Array(0,0);
accuracies = new Array(0,0,0,0);
totalRounds = new Array(0,0);
showMentalContent = new Array(false, false);

//-------------------------------------------------------------------------------------------- CONSTRUCTORS

function makeHistoryPanel(id) {
// Panels on the left and right that show previously made offers. Each offer has 10 slots (8 chips + 2 separator)
// To acess: history_%AGENTID%_%OFFERNR%_%CHIPNR%
  var i,j,strPanel;
  strPanel = "";
  for (i = 0; i < 21; ++i) {
    for (j = 0; j < 10; ++j) {
      strPanel += "<img id=\"history_"+id+"_"+i+"_"+j+"\" src=\"/images/chip.png\" height=10 style=\"visibility:hidden;\">";
    }
    strPanel += "<br>";
  }
  return strPanel;
}

function makeBoard(size) {
// Game board
// To access: board%ROW%_%COLUMN%
  var i,j,k,strBoard;
  strBoard = "<table border=1 cellspacing=0 cellpadding=0>";
  for (i = 0; i < size; ++i) {
    strBoard += "<tr>";
    for (j = 0; j < size; ++j) {
      if (i == Math.floor(size/2) && j == Math.floor(size/2)) {
        strBoard += "<td><div id=\"board"+i+"_"+j+"\" style=\"position:relative;top:0;left:0;width:50;height:50;background-color:white;font-size:42;\" align=center><img src=\"/images/c2c1.png\"></div></td>";
      } else {
        k = Math.floor(boardColors.length*Math.random());
        strBoard += "<td><div id=\"board"+i+"_"+j+"\" style=\"position:relative;top:0;left:0;width:50;height:50;background-color:"+boardColors[k]+";\"  align=center></div></td>";
      }
    }
    strBoard += "</tr>";
  }
  return strBoard+"</table>";
}

function makeEndowmentArea(id) {
// Initial sets of chips
// To access: endowment_%AGENTID%_%CHIPNR%
  var i, strPanel;
  strPanel = "";
  for (i = 0; i < 4; ++i) {
    strPanel += "<img id=\"endowment_"+id+"_"+i+"\" src=\"/images/chip.png\" style=\"background-color:"+boardColors[i]+";\">";
  }
  return strPanel;
}

function makeOfferPanel() {
// Panel that shows currently offered redistribution of chips with buttons to adjust
// To access: 	chip%CHIPNR%_l_c%COLORID%		for left side, chip numbers in descending order
//				chip%CHIPNR%_r_c%COLORID%		for right side, chip numbers in ascending order
  var i,j,strPanel;
  strPanel = "";
  for (i = 0; i < boardColors.length; ++i) {
    offerPanel[i] = new Array(4,4);
    for (j = 0; j < 8; ++j) {
      strPanel += "<img id=\"chip"+(7-j)+"_l_c"+i+"\" src=\"/images/chip.png\" style=\"background-color:"+boardColors[i]+";\">";
    }
    strPanel += "<input type=button value=\"<\" style=\"position:relative;top:-7;\" onClick=\"javascript:moveLeft("+i+");\">";
    strPanel += "<input type=button value=\">\" style=\"position:relative;top:-7;\" onClick=\"javascript:moveRight("+i+");\">";
    for (j = 0; j < 8; ++j) {
      strPanel += "<img id=\"chip"+j+"_r_c"+i+"\" src=\"/images/chip.png\" style=\"background-color:"+boardColors[i]+";\">";
    }
    strPanel += "<br>";
  }
  return strPanel;
}

function makeLocationBeliefGrid(gridID, size) {
// Mental content
// Te access: %FIELDID%_board%ROW%_%COLUMN%
  var strPanel, i, j;
  strPanel = "<div id=\""+gridID+"_container\" style=\"position:relative;width:"+(5*size+6)+";height:"+(5*size+6)+";background-color:black;\">";
  for (i = 0; i < 5; ++i) {
    for (j = 0; j < 5; ++j) {
      strPanel += "<div id=\""+gridID+"_board"+i+"_"+j+"\" style=\"position:absolute;top:"+(i*(size+1)+1)+";left:"+(j*(size+1)+1)+";height:"+size+";width:"+size+";background-color:black;\"></div>"
    }
  }
  return strPanel+"</div>";
}


//-------------------------------------------------------------------------------------------- CONTROLS

function toggleInitMental(newValue) {
// Shows/hides mental content initiator
  showMentalContent[0] = newValue;
  updateBeliefPanels();
}

function toggleRespMental(newValue) {
// Shows/hides mental content responder
  showMentalContent[1] = newValue;
  updateBeliefPanels();
}

function moveRight(color) {
// Moves one chip of the given color from the initiator to the responder
   if (offerPanel[color][0] > 0) {
     offerPanel[color][0]--;
     offerPanel[color][1]++;
   }
   updateOfferPanel();
}

function moveLeft(color) {
// Moves one chip of the given color from the responder to the initiator
   if (offerPanel[color][1] > 0) {
     offerPanel[color][1]--;
     offerPanel[color][0]++;
   }
   updateOfferPanel();
}

function setInitiator(newValue) {
// Set theory of mind level of the initiator
  agentLevels[0] = newValue*1;
  init();
}

function setResponder(newValue) {
// Set theory of mind level of the responder
  agentLevels[1] = newValue*1;
  init();
}

//-------------------------------------------------------------------------------------------- VISUALIZATION

function setButtons() {
// Activate/deactivate buttons according to burrent game state
  document.getElementById("turn_signal_0").style.visibility = (round%2==0&&round>=0?"visible":"hidden");
  document.getElementById("turn_signal_1").style.visibility = (round%2==1&&round>=0?"visible":"hidden");
  if (round < 0) {
    document.getElementById("button_play").value = "New game";
    document.getElementById("button_play").disabled = false;
    document.getElementById("button_accept").disabled = true;
    document.getElementById("button_withdraw").disabled = true;
    document.getElementById("button_counter").disabled = true;
    document.getElementById("button_start").disabled = (agentLevels[0] < 0 || agentLevels[1] < 0);
  } else {
    document.getElementById("button_play").value = "Play round"
    document.getElementById("button_stop").disabled = true;
    if (agentLevels[round%2] >= 0 && agentLevels[1 - round%2] < 0) {
      playRound(-1);
    } else if (agentLevels[round%2] < 0) {
      document.getElementById("button_play").disabled = true;
      document.getElementById("button_start").disabled = true;
      document.getElementById("button_accept").disabled = (round < 1);
      document.getElementById("button_withdraw").disabled = false;
      document.getElementById("button_counter").disabled = (round > 38);
    } else {
      document.getElementById("button_accept").disabled = true;
      document.getElementById("button_withdraw").disabled = true;
      document.getElementById("button_counter").disabled = true;
      document.getElementById("button_play").disabled = false;
      document.getElementById("button_start").disabled = false;
    }
    updateOfferPanel();
//    resetOffer(ct);
    showScores();
    updateBeliefPanels();
  }
}

function updateBeliefPanels() {
// Updates mental content information
  var i, j, strInit, strResp, ag, weight;
  document.getElementById("initMentalContent").style.visibility = (showMentalContent[0]?"visible":"hidden");
  document.getElementById("respMentalContent").style.visibility = (showMentalContent[1]?"visible":"hidden");
  for (i = 1; i < agents[0].length; ++i) {
    for (j = 0; j < agents[0][i].locationBeliefs.length; ++j) {
      strInit = getColorCode(Math.floor(256*Math.pow(agents[0][i].locationBeliefs[j],0.25)));
      strResp = getColorCode(Math.floor(256*Math.pow(agents[1][i].locationBeliefs[j],0.25)));
      document.getElementById("init"+i+"_"+goalLocations[j]).style.backgroundColor = "#"+strInit+strInit+strInit;
      document.getElementById("resp"+i+"_"+goalLocations[j]).style.backgroundColor = "#"+strResp+strResp+strResp;
    }
  }
  ag = agents[0][2];
  weight = 1.0;
  for (i = 2; i > 0; --i) {
    document.getElementById("confToM"+i+"_init").innerHTML = "Weight: "+Math.floor(100*weight*ag.confidence)/100+"<br>Accuracy: "+(totalRounds[0]==0?0:Math.floor(100*accuracies[i-1]/totalRounds[0]))+"%";
    weight *= (1 - ag.confidence);
    ag = ag.selfModel;
  }
  ag = agents[1][2];
  weight = 1.0;
  for (i = 2; i > 0; --i) {
    document.getElementById("confToM"+i+"_resp").innerHTML = "Weight: "+Math.floor(100*weight*ag.confidence)/100+"<br>Accuracy: "+(totalRounds[1]==0?0:Math.floor(100*accuracies[i+1]/totalRounds[1]))+"%";
    weight *= (1 - ag.confidence);
    ag = ag.selfModel;
  }
}

function updateOfferPanel() {
// Show the contents of offerPanel onscreen
  var i,j;
  for (i = 0; i < boardColors.length; ++i) {
    for (j = 0; j < 8; ++j) {
      document.getElementById("chip"+j+"_l_c"+i).style.visibility = (offerPanel[i][0]>j ? "visible":"hidden");
      document.getElementById("chip"+j+"_r_c"+i).style.visibility = (offerPanel[i][1]>j ? "visible":"hidden");
    }
  }
  if (agentLevels[round%2] < 0) {
    showOfferBoard(getHumanOfferFromScreen(0),round%2==0,round%2==1);
  } else {
    showOfferBoard(getHumanOfferFromScreen(0),true, true);
  }
}

function loadEndowment(ctGame, number, id) {
// Show endowment onscreen
  var i,j,n;
  n = 0;
  for (i = 0; i < boardColors.length; ++i) {
    for (j = 0; j < ctGame.chips[number][i]; ++j) {
      document.getElementById("endowment_"+id+"_"+n).style.backgroundColor = boardColors[i];
      n++;
    }
  }
}

function showScores() {
// Show scores onscreen
  document.getElementById("scoreIntiator").innerHTML = scores[0];
  document.getElementById("scoreResponder").innerHTML = scores[1];
}

function resetOffer(ctGame) {
// Shows initial distribution of chips as an offer.
  var i;
  for (i = 0; i < boardColors.length; ++i) {
    offerPanel[i][0] = ctGame.chips[0][i];
    offerPanel[i][1] = ctGame.chips[1][i];
  }
  updateOfferPanel();
}


function showOffer(offer, playerID) {
// Shows the given offer from the given player onscreen
  var bins, i, j, n, itemID;
  if (playerID == 0) {
    offer = ct.flipArray[offer];
  }
  bins = convertCode(offer, ct.binMax);
  n = 0;
  itemID = Math.floor(round/2);
  for (i = 0; i < bins.length; ++i) {
    offerPanel[i][0] = bins[i];
    for (j = 0; j < bins[i]; ++j) {
      document.getElementById("history_"+(playerID % 2)+"_"+itemID+"_"+n).style.backgroundColor = boardColors[i];
      document.getElementById("history_"+(playerID % 2)+"_"+itemID+"_"+n).style.visibility = "visible";
      n++;
    }
  }
  bins = convertCode(ct.flipArray[offer], ct.binMax);
  n += 2;
  for (i = 0; i < bins.length; ++i) {
    offerPanel[i][1] = bins[i];
    for (j = 0; j < bins[i]; ++j) {
      document.getElementById("history_"+(playerID % 2)+"_"+itemID+"_"+n).style.visibility = "visible";
      document.getElementById("history_"+(playerID % 2)+"_"+itemID+"_"+n).style.backgroundColor = boardColors[i];
      n++;
    }
  }
  updateOfferPanel();
  updateBeliefPanels();
}

function showOfferBoard(offer, doShowInit, doShowResp) {
// Show the effects of the given offer on the game situation
  var imgMatrix, i, j;
  imgMatrix = new Array();
  for (i = 0; i < 25; ++i) {
    imgMatrix[i] = "";
  }
  if (doShowResp && offer >= 0 && (showOfferHelper || round < 0)) {
    imgMatrix[ct.finalLocation[ct.locations[1]][ct.flipArray[offer]]] += "c2";
  } else {
    imgMatrix[12] += "c2";
  }
  if (doShowInit && offer >= 0 && (showOfferHelper || round < 0)) {
    imgMatrix[ct.finalLocation[ct.locations[0]][offer]] += "c1";
  } else {
    imgMatrix[12] += "c1";
  }
  if (doShowResp || revealGoals) {
    imgMatrix[goalLocationArray[ct.locations[1]]] += "g2";
  }
  if (doShowInit || revealGoals) {
    imgMatrix[goalLocationArray[ct.locations[0]]] += "g1";
  }
  for (i = 0; i < 5; ++i) {
    for (j = 0; j < 5; ++j) {
      document.getElementById("board"+i+"_"+j).innerHTML = (imgMatrix[5*i+j]==""?"":"<img src=\"/images/"+imgMatrix[5*i+j]+".png\">");
    }
  }
}

function loadGame(ctGame) {
// Shows all game information onscreen
  var i,j;
  for (i = 0; i < 5; ++i) {
    for (j = 0; j < 5; ++j) {
      document.getElementById("board"+i+"_"+j).style.backgroundColor = boardColors[ctGame.board[i][j]];
      document.getElementById("board"+i+"_"+j).innerHTML = "";
    }
  }
  loadEndowment(ctGame, 0, "i");
  loadEndowment(ctGame, 1, "r");
  if (agentLevels[0] < 0 || agentLevels[1] >= 0) {
    document.getElementById(goalLocations[ct.locations[0]]).innerHTML = "<img src=\"/images/gi.png\">";
  }
  if (agentLevels[1] < 0 || agentLevels[0] >= 0) {
    document.getElementById(goalLocations[ct.locations[1]]).innerHTML = "<img src=\"/images/gr.png\">";
  }
  document.getElementById("board2_2").innerHTML = "<img src=\"/images/crci.png\">";
  for (i = 0; i < agents[0].length; ++i) {
    agents[0][i].init(ct, 0);
    agents[0][i].setLocation([ct.locations[0]]);
    agents[1][i].init(ct, 1);
    agents[1][i].setLocation([ct.locations[1]]);
  }
}


//-------------------------------------------------------------------------------------------- GAME FUNCTIONS

function resetGame() {
// Reset all data to zero
  scores = new Array(0,0);
  accuracies = new Array(0,0,0,0);
  totalRounds = new Array(0,0);
  init();
}

function init() {
// Initialize a new game
  var i, j, tmpElements;
  tmpElements = document.getElementsByName("ToMorder1");
  for (i = 0; i < tmpElements.length; ++i) {
    if (tmpElements[i].checked) {
      agentLevels[0] = tmpElements[i].value*1;
    }
  }
  tmpElements = document.getElementsByName("ToMorder2");
  for (i = 0; i < tmpElements.length; ++i) {
    if (tmpElements[i].checked) {
      agentLevels[1] = tmpElements[i].value*1;
    }
  }
  for (i = 0; i < 20; ++i) {
    for (j = 0; j < 10; ++j) {
      document.getElementById("history_0_"+i+"_"+j).style.visibility = "hidden";
      document.getElementById("history_1_"+i+"_"+j).style.visibility = "hidden";
    }
  }
  showMentalContent[0] = document.getElementById("showInitMental").checked;
  showMentalContent[1] = document.getElementById("showRespMental").checked;
  ct.init();
  loadGame(ct);
  resetOffer(ct);
  round = 0;
  currentOffer = -1;
  setButtons();

}

function startTimer() {
// Sets the timer to a new value and initiates automatic play
  timerEnabled++;
  playRound(timerEnabled);
}

function stopTimer() {
// Sets the timer to a new value, disabling any active timer
  timerEnabled++;
}

function getColorCode(nr) {
// Simple function to get a hex value from a number
  var strOut, alphabet;
  alphabet = "0123456789ABCDEF";
  strOut = "";
  while (nr > 0) {
    strOut = alphabet.charAt(nr%16) + strOut;
    nr = Math.floor(nr/16);
  }
  while (strOut.length < 2) {
    strOut = "0"+strOut;
  }
  return strOut;
}

function processHumanOffer(newOffer) {
// Process the given offer as a human offer
  for (i = 0; i < agents[round%2].length; ++i) {
    agents[round%2][i].sendOffer(ct, ct.flipArray[newOffer]);
    agents[1-(round%2)][i].receiveOffer(ct, newOffer);
  }
  accuracies[2*(1-(round%2))] += agents[1-(round%2)][1].lastAccuracy;
  accuracies[2*(1-(round%2))+1] += agents[1-(round%2)][2].lastAccuracy;
  totalRounds[1-(round%2)]++;
  showOffer(newOffer, round%2);
}

function acceptOffer() {
// Accept button has been clicked
  processHumanOffer(ct.flipArray[currentOffer]);
  endGame(round%2==0?currentOffer:ct.flipArray[currentOffer]);
}
	
function withdrawOffer() {
// Withdraw button has been clicked
  processHumanOffer(ct.chipSets[1 - round%2]);
  endGame(ct.chipSets[0]);
}

function getHumanOfferFromScreen(id) {
// Converts the offer onscreen to an offer ID
  var bins, i;
  bins = new Array();
  for (i = 0; i < boardColors.length; ++i) {
    bins[i] = offerPanel[i][id];
  }
  return convertChips(bins, ct.binMax);
}

function makeHumanOffer() {
// New offer button has been clicked
  var newOffer;
  newOffer = ct.flipArray[getHumanOfferFromScreen(round%2)];
  if (newOffer == ct.flipArray[currentOffer]) {
    acceptOffer();
  } else if (newOffer == ct.chipSets[1 - round%2]) {
    withdrawOffer();
  } else {
    processHumanOffer(newOffer);
    round++;
    currentOffer = newOffer;
  }
  setButtons();
}

function endGame(offer) {
// Ends the game and processes the necessary changes
  var imgMatrix, i, j;
  scores[0] += ct.utilityFunction[ct.locations[0]][offer];
  scores[1] += ct.utilityFunction[ct.locations[1]][ct.flipArray[offer]];
  round = -1;
  showOfferBoard(offer,true,true);
  showScores();
  setButtons();
}

function playRound(timerID) {
// Plays one round of the game, and sets a timer for the next round if needed
  var newOffer, i;
  if (timerID == timerEnabled || timerID < 0) {
    if (round < 0) {
      init();
    } else {
      newOffer = agents[round%2][agentLevels[round%2]].selectOffer(ct, currentOffer);
      for (i = 0; i < agents[round%2].length; ++i) {
        agents[round%2][i].sendOffer(ct, newOffer);
        agents[1-(round%2)][i].receiveOffer(ct, ct.flipArray[newOffer]);
        if (revealGoals) {
          agents[0][i].informLocation(ct);
          agents[1][i].informLocation(ct);
        }
      }
      accuracies[2*(1-(round%2))] += agents[1-(round%2)][1].lastAccuracy;
      accuracies[2*(1-(round%2))+1] += agents[1-(round%2)][2].lastAccuracy;
      totalRounds[1-(round%2)]++;
      newOffer = ct.flipArray[newOffer];
      showOffer(newOffer, round%2);
      if (newOffer == ct.flipArray[currentOffer]) {
        endGame(round%2==0?currentOffer:newOffer);
      } else if (newOffer == ct.chipSets[1 - (round%2)] || round > 38) {
        endGame(ct.chipSets[0]);
      } else {
        round++;
        document.getElementById("turn_signal_0").style.visibility = (round%2==0?"visible":"hidden");
        document.getElementById("turn_signal_1").style.visibility = (round%2==0?"hidden":"visible");
        if (agentLevels[round%2] < 0) {
          showOfferBoard(getHumanOfferFromScreen(0),agentLevels[0]<0 || agentLevels[1]>=0,agentLevels[1]<0 || agentLevels[0]>=0)
        } else {
          showOfferBoard(-1,agentLevels[0]<0 || agentLevels[1]>=0,agentLevels[1]<0 || agentLevels[0]>=0)
        }
      }
      setButtons();
      currentOffer = newOffer;
    }
  }
  if (timerID == timerEnabled) {
    document.getElementById("button_start").disabled = true;
    document.getElementById("button_stop").disabled = false;
    document.getElementById("button_play").disabled = true;
    setTimeout("playRound("+timerID+");",round<0?1000:500);
  } else {
    document.getElementById("button_start").disabled = false;
    document.getElementById("button_stop").disabled = true;
    document.getElementById("button_play").disabled = false;
  }
}

ct = new CTgame();
agents = new Array(new Array(new Agent(0,0), new Agent(1,0), new Agent(2,0)),
                   new Array(new Agent(0,1), new Agent(1,1), new Agent(2,1)));

