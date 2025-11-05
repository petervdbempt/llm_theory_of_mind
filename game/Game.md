The game played in our project is the game of Colored Trails. 
The idea of the game is that 2 players are placed on a grid and get assigned a private
goal location. They must try to reach or get as close to the goal location as possible. 
For them to travel to an adjacent tile they must pay a chip of that color. They each start 
with 5 chips of random color which they can use, but they can also try and trade chips
with the other player. The idea is that agents learn to cooperate in order to reach a favourable
location. However, in our setup the players do not know their opponents goal location, they only know
their own goal location and the chip distribution of both themsemselves and the opponent.
We have different types of agents that take the role of players, please read the Agents.md in the
agents folder for more information about the agents. 

The rules of the game are the following:

GAME RULES:
- Your objective is to move as close as possible to your goal location.
- You can only move to adjacent tiles, not diagonally.
- Each move costs one chip of the same color as the tile you move onto.
- You do not need to pay for the start location, but you do need to pay for the goal location.
- Before moving, a negotiation phase takes place, where the two players may propose any redistribution of chips (e.g., 1-for-1, 3-for-1, 1-for-2, etc.).
- If the proposal is rejected, it becomes the other player's turn to propose. If the proposal is accepted or if a player passes, 
the redistribution becomes final and the negotiation immediately ends.
- Negotiation can continue for up to 5 rounds, alternating turns after each rejection.
- After a trade or a pass, both players immediately try to move as close as possible to their goal location.

The scoring in the game is as follows: 
SCORING:
- +100 points per step closer to your goal
- +500 points for reaching your goal
- +50 points for each unused chip
- -1 point per negotiation round

The winner of the game is the player that at the end of the game has the highest scoring.