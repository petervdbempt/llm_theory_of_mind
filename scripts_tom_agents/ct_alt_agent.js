DEFAULT_LEARNING_SPEED = 0.8;
	// Degree to which agents adjust their behaviour to offers made by the other player. Range: [0,1]
PRECISION = 0.00001
	// Precision of "better" and "similar" offers
MODE_ONE_LOCATION = 0;
MODE_ALL_LOCATION = 1;

function ToM0model(playerID) {
// Basic agent that learns what offers tend to be accepted
  this.playerID = playerID;
  this.loc = 0;
  this.learningSpeed = DEFAULT_LEARNING_SPEED;
  this.savedBeliefs = new Array();
  this.saveCount = 0;
  this.cntBeliefs = new Array([5, 5, 5, 5, 5, 5, 5, 5, 5],
                              [14, 248, 407, 5, 5, 5, 5, 5, 5],
                              [26, 316, 196, 129, 5, 5, 5, 5, 5],
                              [28, 19, 194, 62, 24, 5, 5, 5, 5],
                              [26, 27, 18, 19, 10, 5, 5, 5, 5],
                              [5, 5, 5, 5, 5, 5, 5, 5, 5],
                              [5, 5, 5, 5, 5, 5, 5, 5, 5],
                              [5, 5, 5, 5, 5, 5, 5, 5, 5],
                              [5, 5, 5, 5, 5, 5, 5, 5, 5]);
  this.ttlBeliefs = new Array([226, 25, 27, 34, 45, 5, 5, 5, 5],
                              [14, 495, 912, 26, 34, 5, 5, 5, 5],
                              [26, 566, 392, 289, 23, 5, 5, 5, 5],
                              [28, 19, 345, 122, 55, 5, 5, 5, 5],
                              [26, 27, 18, 32, 17, 5, 5, 5, 5],
                              [5, 5, 5, 5, 5, 5, 5, 5, 5],
                              [5, 5, 5, 5, 5, 5, 5, 5, 5],
                              [5, 5, 5, 5, 5, 5, 5, 5, 5],
                              [5, 5, 5, 5, 5, 5, 5, 5, 5]);
  this.beliefOffer = new Array();
  this.init =
    function(ctGame, playerID) {
    // Initializes agent for the given game with the gives ID
      var i;
      this.playerID = playerID;
      this.beliefOffer = new Array();
      for (i = 0; i < ctGame.utilityFunction[this.playerID].length; ++i) {
        this.beliefOffer[i] = this.getAcceptanceRate(ctGame, i);
      }
      this.saveCount = 0;
      this.savedBeliefs = new Array();
      
    };
  this.saveBeliefs =
    function() {
    // Saves beliefs to be restored later. Used by theory of mind agents.
      this.savedBeliefs[this.saveCount] = this.beliefOffer.slice(0);
      this.saveCount++;
    };
  this.restoreBeliefs =
    function() {
    // Restores previously saved beliefs. Used by theory of mind agents.
      this.saveCount--;
      this.beliefOffer = this.savedBeliefs[this.saveCount].slice(0);
    };
  this.observe = 
    function (ctGame, offer, isAccepted, playerID) {
    // Observes the offer that is accepted/rejected in a given game by a given player
      var diff, pos, neg, i;
      pos = 0;
      neg = 0;
      diff = getChipDifference(ctGame.chipSets[this.playerID], offer, ctGame.binMax);
      for (i = 0; i < diff.length; ++i) {
        if (diff[i] > 0) {
          pos += diff[i];
        } else {
          neg -= diff[i];
        }
      }
      this.ttlBeliefs[pos][neg]++;
      if (playerID != this.playerID) {
        this.cntBeliefs[pos][neg]++;
        this.increaseColorBelief(ctGame,offer);
      } else if (isAccepted) {
        this.cntBeliefs[pos][neg]++;
      } else {
        this.decreaseColorBelief(ctGame,offer);
      }
    };
  this.increaseColorBelief = 
    function(ctGame, newOwnChips) {
    // Decrease belief that offers less generous than the given offer will be successful
      var i,j, newBins, curOffer;
      newBins = convertCode(newOwnChips, ctGame.binMax);
      for (i = 0; i < this.beliefOffer.length;++i) {
        curOffer = convertCode(i, ctGame.binMax);
        for (j = 0; j < curOffer.length; ++j) {
          if (curOffer[j] > newBins[j]) {
            this.beliefOffer[i] = (1 - this.learningSpeed)*this.beliefOffer[i];
          }
        }
      }
    };
  this.decreaseColorBelief = 
    function(ctGame, newOwnChips) {
    // Decrease belief that offers no more generous than the given offer will be successful
      var i,j, newBins, curOffer;
      newBins = convertCode(newOwnChips, ctGame.binMax);
      for (i = 0; i < beliefOffer.length;++i) {
        curOffer = convertCode(i, ctGame.binMax);
        for (j = 0; j < curOffer.length; ++j) {
          if (curOffer[j] >= newBins[j]) {
            this.beliefOffer[i] = (1 - this.learningSpeed)*this.beliefOffer[i];
          }
        }
      }
    };
  this.getAcceptanceRate =
    function (ctGame, offer) {
    // Returns the believed probability that a given offer will be accepted
      var diff, pos, neg, i;
      pos = 0;
      neg = 0;
      diff = getChipDifference(ctGame.chipSets[this.playerID], offer, ctGame.binMax);
      for (i = 0; i < diff.length; ++i) {
        if (diff[i] > 0) {
          pos += diff[i];
        } else {
          neg -= diff[i];
        }
      }
      return this.cntBeliefs[pos][neg] / this.ttlBeliefs[pos][neg]
    };
  this.getExpectedValue =
    function(ctGame, offer) {
    // Returns the expected change in score by making the offer
      return this.beliefOffer[offer] * ctGame.utilityFunction[this.loc][offer];
    };
  this.setID = 
    function(newPlayerID) {
    // Sets playerID for this agent
      this.playerID = newPlayerID;
    };
}

function Agent(order, playerID) {
// Theory of mind agent
  this.learningSpeed = DEFAULT_LEARNING_SPEED;
  this.order = order;
  this.confidenceLocked = false;
  	// If true, confidence cannot be changed
  this.confidence = 1.0;
  	// Degree to which current order determines behaviour of the agent
  this.playerID = playerID;
  this.locationBeliefs = new Array();
  this.savedBeliefs = new Array();
  this.saveCount = 0;
  this.loc;
  this.lastAccuracy;
  this.mode = MODE_ALL_LOCATION;
  	// Agent considers all locations (MODE_ALL_LOCATION) or only the location with the highest likelihood (MODE_ONE_LOCATION)
  if (this.order > 0) {
    this.opponentModel = new Agent(order-1, 1 - playerID);
    this.opponentModel.confidenceLocked = true;
    this.selfModel = new Agent(order-1, playerID);
  } else {
    this.opponentModel = new ToM0model(playerID);
    this.selfModel = null;
  }
  this.init =
    function(ctGame, playerID) {
    // Initializes agent for a new game
      var i;
      this.playerID = playerID;
      this.loc = ctGame.locations[this.playerID];
      this.savedBeliefs = new Array();
      this.saveCount = 0;
      this.opponentModel.init(ctGame, 1 - playerID);
      if (this.order > 0) {
        this.selfModel.init(ctGame, playerID);
        for (i = 0; i < ctGame.utilityFunction.length; ++i) {
          this.locationBeliefs[i] = 1 / ctGame.utilityFunction.length;
        }
      } else {
        this.opponentModel.init(ctGame,playerID);
      }
    };
  this.saveBeliefs =
    function() {
    // Saves beliefs to be restored later. Used by higher order agents to determine effect of certain offer on lower order partners
      if (order > 0) {
        this.savedBeliefs[this.saveCount] = this.locationBeliefs.slice(0);
        this.saveCount++;
      }
      this.opponentModel.saveBeliefs();
    };
  this.restoreBeliefs =
    function() {
    // Restores previously saved beliefs.
      this.saveCount--;
      if (order > 0) {
        this.locationBeliefs = this.savedBeliefs[this.saveCount].slice(0);
      }
      this.opponentModel.restoreBeliefs();
    };
  this.getLocationBeliefs =
    function(location) {
    // Returns the believed likelihood that the partner is in the give location
      if (confidenceLocked) {
        return this.locationBeliefs[location];
      }
      if (this.order == 0) {
        return 1/12;
      }
      return this.confidence*this.locationBeliefs[location] + (1 - this.confidence)*this.selfModel.getLocationBeliefs(location);
    };
  this.informLocation = 
    function(ctGame) {
    // Informs the agent of the actual locations of the players
      var i;
      this.loc = ctGame.locations[this.playerID];
      if (this.order > 0) {
        for (i = 0; i < this.locationBeliefs.length; ++i) {
          this.locationBeliefs[i] = 0;
        }
        this.locationBeliefs[ctGame.locations[1-this.playerID]] = 1;
        this.selfModel.informLocation(ctGame);
        this.opponentModel.informLocation(ctGame);
      }
    };
  this.getLocationValue =
    function(ctGame, offerToSelf) {
    // Returns the value of making the given offer given the current setting of locations
      var response, curValue;
      response = this.opponentModel.selectOffer(ctGame, ctGame.flipArray[offerToSelf]);
      curValue = 0;
      if (response == ctGame.flipArray[offerToSelf]) {
        // Partner accepts offer
        curValue += ctGame.utilityFunction[this.loc][offerToSelf] - ctGame.utilityFunction[this.loc][ctGame.chipSets[this.playerID]] - 1;
      } else if (response != ctGame.chipSets[1-this.playerID]) {
        // Partner does not withdraw from negotiation
        response = ctGame.flipArray[response];
        curValue += Math.max(-1,ctGame.utilityFunction[this.loc][response] - ctGame.utilityFunction[this.loc][ctGame.chipSets[this.playerID]] - 2);
      }
      return curValue;
    };
  this.setLocation = 
    function(newLocation) {
    // Sets location of the other player
      this.loc = newLocation;
      if (order > 0) {
        this.selfModel.setLocation(newLocation);
      } else {
        this.opponentModel.loc = newLocation;
      }
    };
  this.getValue =
    function(ctGame, offerToSelf) {
    // Returns value of making given offer
      var l, curValue, bestLocs;
      if (ctGame.utilityFunction[this.loc][offerToSelf] <= ctGame.utilityFunction[this.loc][ctGame.chipSets[this.playerID]]) {
        return -1;
      }
      if (order == 0) {
        return this.opponentModel.getExpectedValue(ctGame, offerToSelf);
      }
      if (this.confidence > 0 || this.confidenceLocked) {
        this.opponentModel.saveBeliefs();
        this.opponentModel.receiveOffer(ctGame, ctGame.flipArray[offerToSelf]);
        if (this.mode == MODE_ONE_LOCATION) {
          bestLocs = new Array();
          bestLocs[0] = 0;
          for (l = 1; l < this.locationBeliefs.length; ++l) {
            if (this.locationBeliefs[l] > this.locationBeliefs[bestLocs[0]] - PRECISION) {
              if (this.locationBeliefs[l] > this.locationBeliefs[bestLocs[0]] + PRECISION) {
                bestLocs.length = 0;
              }
              bestLocs[bestLocs.length] = l;
            }
          }
          l = bestLocs[Math.floor(Math.random()*bestLocs.length)];
          if (this.locationBeliefs[l] > this.locationBeliefs[this.opponentModel.loc] + PRECISION) {
            this.opponentModel.setLocation(l);
          }
          curValue = this.getLocationValue(ctGame, offerToSelf);
        } else {
          curValue = 0;
          for (l = 0; l < this.locationBeliefs.length; ++l) {
            if (this.locationBeliefs[l] > 0) {
              this.opponentModel.setLocation(l);
              curValue += this.locationBeliefs[l]*this.getLocationValue(ctGame, offerToSelf);
            }
          }
        }
        this.opponentModel.restoreBeliefs();
      }
      if (this.confidence >= 1 || this.confidenceLocked) {
        return curValue;
      }
      return this.confidence*curValue + (1 - this.confidence) * this.selfModel.getValue(ctGame, offerToSelf);
    };
  this.setID = 
    function(newPlayerID) {
    // Sets ID of this agent
      this.playerID = newPlayerID;
      if (this.order > 0) {
        this.opponentModel.setID(1 - newPlayerID);
        this.selfModel.setID(newPlayerID);
      } else {
        this.opponentModel.setID(newPlayerID);
      }
    };
  this.observe = 
    function (ctGame, offer, isAccepted, playerID) {
    // Observes given offer made by given player being accepted/rejected
      this.opponentModel.observe(ctGame, offer, isAccepted, playerID);
      if (this.order > 0) {
        this.selfModel.observe(ctGame, offer, isAccepted, playerID);
        if (playerID != this.playerID && !this.confidenceLocked) {
          this.confidence = (1 - this.learningSpeed)*this.confidence + this.learningSpeed*((Math.max(0,this.opponentModel.getValue(ctGame,offer))+1) / (Math.max(0,this.opponentModel.getBestValue(ctGame))+1));
        }
      }
    };
  this.selectOffer =
    function (ctGame, offerToMe) {
    // Select an offer to make, given the given alternative
      var allOffers;
      allOffers = this.getValidOffers(ctGame, offerToMe);
      return allOffers[Math.floor(allOffers.length*Math.random())];
    };
  this.makeOffer =
    function(ctGame, offerToMe) {
    // Observes the offer being made to this agent, selects an offer, and observes the choice for this offer being made
      var choice;
      this.receiveOffer(ctGame, offerToMe);
      choice = this.selectOffer(ctGame, offerToMe);
      this.sendOffer(ctGame, choice);
      return ctGame.flipArray[choice];
    };
  this.getBestValue =
    function(ctGame) {
    // Returns the highest attainable score, according to this agent
      var i, allOffers, value, bestValue;
      bestValue = 0;
      for (i = 0; i < ctGame.utilityFunction[0].length; ++i) {
        value = this.getValue(ctGame,i);
        if (value > bestValue + PRECISION) {
          bestValue = value;
        }
      }
      return Math.max(0,bestValue);
    };
  this.getValidOffers =
    function(ctGame, offerToMe) {
    // Returns all offers that maximize expected utility
      var i, allOffers, value, bestValue;
      allOffers = new Array();
      allOffers[0] = this.chips;
      bestValue = 0;
      for (i = 0; i < ctGame.utilityFunction[0].length; ++i) {
        value = this.getValue(ctGame,i);
        if (value > bestValue - PRECISION) {
          if (value > bestValue + PRECISION) {
            allOffers.length = 0;
            bestValue = value;
          }
          allOffers[allOffers.length] = i;
        }
      }
      if (offerToMe >= 0 && ctGame.utilityFunction[this.loc][offerToMe] - ctGame.utilityFunction[this.loc][ctGame.chipSets[this.playerID]] > bestValue - PRECISION) {
      // Partner's offer is better than expected from any counteroffer
        allOffers.length = 1;
        allOffers[0] = offerToMe;
        bestValue = ctGame.utilityFunction[this.loc][offerToMe] - ctGame.utilityFunction[this.loc][ctGame.chipSets[this.playerID]];
      }
      if (bestValue < PRECISION) {
      // Withdrawing is better than any alternative
        allOffers.length = 1;
        allOffers[0] = ctGame.chipSets[this.playerID];
      }
      return allOffers;
    };
  this.updateLocationBeliefs =
    function(ctGame, offerReceived) {
    // Update beliefs concerning the location of the other player when observing the given offer being made.
      var offerToOther, l, accuracy, sumBeliefs, tmpVal;
      offerToOther = ctGame.flipArray[offerReceived];
      accuracy = 0;
      sumBeliefs = 0;
      for (l = 0; l < this.locationBeliefs.length; ++l) {
        this.opponentModel.setLocation(l);
        
        if (ctGame.utilityFunction[l][offerToOther] <= ctGame.utilityFunction[l][ctGame.chipSets[1-this.playerID]]) {
          this.locationBeliefs[l] = 0;
        } else {
          this.locationBeliefs[l] *= Math.max((this.opponentModel.getValue(ctGame,offerToOther)+1) / (this.opponentModel.getBestValue(ctGame)+1), 0);
          accuracy += this.locationBeliefs[l];
        }
        sumBeliefs += this.locationBeliefs[l];
      }
      if (sumBeliefs > 0) {
        sumBeliefs = 1/sumBeliefs;
        for (l = 0; l < this.locationBeliefs.length; ++l) {
          this.locationBeliefs[l] *= sumBeliefs;
        }
      } else {
        for (l = 0; l < this.locationBeliefs.length; ++l) {
          this.locationBeliefs[l] = 1/12;
        }
      }
      this.lastAccuracy = accuracy;
      if (!this.confidenceLocked) {
        this.confidence = (1 - this.learningSpeed) * this.confidence + this.learningSpeed * accuracy;
      }
    };
  this.receiveOffer =
    function(ctGame, offerToMe) {
    // Observe offer being made by other player
      if (offerToMe >= 0) {
        if (order > 0) {
          this.updateLocationBeliefs(ctGame, offerToMe);
          this.selfModel.receiveOffer(ctGame, offerToMe);
          this.opponentModel.sendOffer(ctGame, ctGame.flipArray[offerToMe])
        } else {
          this.opponentModel.observe(ctGame, offerToMe, true, 1 - this.playerID);
        }
      }
    };
  this.sendOffer =
    function(ctGame, offerToMe) {
    // Observe offer being made by this agent
      if (order > 0) {
        this.selfModel.sendOffer(ctGame, offerToMe);
        this.opponentModel.receiveOffer(ctGame, ctGame.flipArray[offerToMe])
      } else {
        this.opponentModel.observe(ctGame, offerToMe, true, 1 - this.playerID);
      }
    };
}