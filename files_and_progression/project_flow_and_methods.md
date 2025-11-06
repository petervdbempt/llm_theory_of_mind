During this project we experimented with different kinds of things. 
We started with reading papers related to TOM, reasoning, the Colored Trails game and LLMs. 
We first implemented the game of Colored Trails in Python, together with a greedy baseline agent 
to ensure we have some working agent on the game.
From this we developed an LLM based agent that worked with the API from the Llama
3.1-8B-Instruct model. We started experimenting on how we should prompt the LLM to get it to 
understand the game and situation it is in, and receive a reasonable output given the situation.
You can find this progression with some more information and visual examples in Meeting 2 presentation.pdf

After the meeting we tried to further develop the prompt such that the model would better understand the game.
This was already quite challenging, since especially the Llama model seemed not capable to
understand the game states and rules and produced nonsense or irrational outputs, often being illegal moves 
or very dumb trade proposals. We therefore also tried to see if other LLMs had the same difficulties
with understanding the game and their goal, and we noticed that the bigger state-of-the-art LLM models
seemed much more capable of playing the game and made sensible and logical decisions (from a human perspective).
We therefore decided to switch to more state-of-the-art LLM models: Claude and Gemini. These models made much more sensible trade offers and therefore seemed more suitable to use 
for this task. 
You can find a more elaborate explanation of what we tried and our conclusion that we might better 
switch to bigger LLM models in Meeting 3 presentation.pdf

We then fine-tuned the prompt such that the bigger LLM models fully understand the game, without giving away too much
information of what we would like to see as a results. We focussed on this since we wanted to 
see what emergent behaviour would arise when the LLMs where just given the rules and content
of the game, without steering them to use any reaosning or TOM. We also ignore any reasoning given, for
Gemini we do this by using the JSON mode such that it only gives back a JSON response in the format
we have made and given to the LLM (which can also be seen in the prompt, which is found in the prompt.txt).
For Claude although we prompt it to only give a valid JSON back, it most of the times gives some reasoning
but for the reasons made clear above we ignore the reasoning, since we only care about the behaviour.
This is because the goal of this research is to compare the emergent behaviour of the LLM to the 
behaviour of the TOM agents, to see what TOM order the LLM mostly resembles. 

Our findings and things still left to discover can be found in findings_and_discussion.md


