We have done a tournament between the ToM agents and the LLM agents to analyze their behaviours.
All combinations of agents play the same 6 games. Unfortunately the first agent often passes at
the start of the game. It is observed that Claude makes more proposals than Gemini. Gemini is also
quite bad at the game, it passes in almost all cases and often looses. Clause does seem to know how
to play the game but sometimes offers trades while it already has the required chips to reach the goal.

In terms of signs of theory of mind, for claude in the response it shows that it tries to think about the
wants and needs of the opponent to come up with a trade that they might take. But as discussed in meetings
those reasons in responses might not at all be faithful to the actions it took (proposals and acceptance/rejections).
If we look at the trades alone, we see that Claude offers chips that the opponent asked for earlier. But this also
limits it to never come up with a different plan after rejection. It will keep asking for one chip but does not consider
that it needs to ask for another chip, that the opponent might want to give. this sometimes leads to a stalemate like situation
where both parties keep trying to get the same chip. Trades are always accepted when it benefits themselves. But that is ofcourse
not always beneficial to win the game. It suggests that claude is trying to win the game but never really tries to
prevent its opponent from winning the game. As long as a trade proposal is beneficial to it, also when it is more beneficial
for the opponent, it will still take the trade. If we have to classify Clause in terms of ToM orders it would be 0 or 1. And it varies
over the different games. In some games it takes note of what the opponent want and acts with that information. It actively makes counter
proposals to find a way to benefit itself with the opponents needs.

Gemini tries to trade very rarely and when proposals are rejected it will pass. Again it only accepts trades when they are beneficial
for itself. If we would classify have to classify gemini in terms of ToM order, we would say 0 as it does not make decicions as if it is
playing against an opponent who is also trying to win. It does not make counter proposals.

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
