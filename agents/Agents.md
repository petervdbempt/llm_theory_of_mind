We have 4 different types of agents in our setup: a greedy agent, a TOM agent (where you can 
specify the order of TOM), and the three different LLM agents: Llama, Gemini and Claude. 

The greedy agent is an agent for the game of Colored Trails that will calculate the utility 
of every trade that it can possibly make and will always propose the deal that yields the biggest 
utility increase. The utility is calculated using the game rules, where the scoring follows these rules:
SCORING:
- +100 points per step closer to your goal
- +500 points for reaching your goal
- +50 points for each unused chip
- -1 point per negotiation round

For more information on the game rules please read the Game.md in the game folder. 

The agent calculates the utility of a trade based on the costs and possible increase if the trade 
would be accepted by the opponent. 

The Theory of Mind (TOM) agent can have three orders of TOM. 
The zero-order TOM agent only uses the information it has on its own goal location and chip distribution 
and proposes a trade that seems beneficial knowing this information. It will reason only 
whether the trade would be beneficial and does not reason about what the opponent would think of the offer.
It is therefore close to the greedy agent, but does not necessarily always makes the trade with the highest utility but
uses statistics to estimate what would be the best possible move. 

The first order TOM agent works similar to the zero-order TOM agent, however it now also incorporates beliefs
about the opponent. The first order TOM agent tries to figure out what the goal location of the opponent is 
based on the trades that the opponent proposes and rejects. It will place itself in the shoes of the opponent 
and thinks in what situation would I act like the opponent, which helps in figuring out the goal of the opponent.
This can be beneficial if you can estimate the private information of the opponent, as it will give you a benefit in the 
negotiation fase. 

The second order TOM agent goes one step further. It does not only reasons about what the opponents goal might be, 
but it also reasons about what the opponent might think that our goal location is. This is one step abstracter thinking and
again give an advantage in negotiation since you reason possibly with more information than your opponent. 

Note that most often second order and higher order TOM are referring to the same agent. This is because second order is seen as 
higher order TOM and going to third or further often does not improve results and thus are all categorized
as higher order TOM. 

Lastly, the LLM agents are constructed of prompting one of the three LLM models with a prompt
that explains the game, the scoring and gives the goal location of the agent alongside the board and 
the chip distribution of both the players. The prompt asks the LLM to propose a trade (or pass) if he is to act, 
or ask whether to accept or reject an offer made by the other player. 

What we are curious to see in this project is whether the LLM agents will incorporate some level of theory of mind
in their behaviour in the game. We will compare the behaviour of all the agents to each other and 
see what type of agents most closely resembles the outputs given by the LLM. 