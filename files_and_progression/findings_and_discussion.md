Our findings ......






For our Discussion we would like to add suggestions of how to fix the TOM order of an LLM. 
In this project we did not have enough time to experiment with this, but we think that LLMs 
are hard to guide on which order TOM behaviour to exhibit. However, we think that if you prompt the LLM
with what intermediate reasoning steps to take, that it would be most aligned with the goal of 
fixing the TOM order. For example, if you want to exhibit zero order TOM, you can prompt: 
Try to think about what are the possible paths to your goal, which chips you need for these paths and thus
which chips might be necessary outside of your current chip distribution and propose a trade for that. 
You do not need to reason about the opponents goal or intentions.
In this way you guide the LLM into thinking only as a zero order TOM agent and not use any information of higher orders. 

For the first order TOM agent it would for example look like this: 
Try to think about what are the possible paths to your goal, which chips you need for these paths and thus
which chips might be necessary outside of your current chip distribution and propose a trade for that. 
However, do also try to reason about what the other players goal location might be based on the trades that it proposes,
if it want to receive blue in a trade, blue might be an important chip to reach their goal location. 
Use this information to make a trade taking into account that you want your opponent to accept the trade if it 
is a good trade for you. 

Also we would have liked to inlcude a user study if there would have been time to 
learn how a human person would play against the LLM. In the paper from de Weerd et al. we saw the results
of a human player against the TOM agents, and the LLM player against a human would add interesting results 
to their findings. 