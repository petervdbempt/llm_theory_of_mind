In this repository you will find the code and documentation of the comparison between LLMs and Theory of mind agents. 
The goal of this comparison is to see whether big LLMs that perform state-of-the-art on all sorts of benchmarks exhibit 
reasoning behaviour about others mental states. 
We use the game of Colored Trails to test this.

The repository is split in the following way

- agents 
  - in this folder you can find the different kinds of agents. We have 4 kind of agents,
a greedy agent, a TOM agent with different orders of TOM and 3 LLM agents: Llama (3.1-8B-Instruct),
Claude (claude-sonnet-4-5) and Gemini (gemini-2.5-flash).
- game 
  - in this folder you can find the game logic which we use to visualize and evaluate games of Colored Trails. 
- scripts_tom_agents 
  - in this folder you can find the original scripts of the TOM agents, that were taken from: http://www.harmendeweerd.nl/alternating-offers-negotiation/. These scripts are an implementation of paper 1*. 
- rewritten_scripts_tom_agents 
  - in this folder you can find the scripts of paper 1*, rewritten to work with our Python implementation. 
- plots
  - Here you can find some files with visualisations of the work we have done
- utils 
  - here you can find files with useful additional functions.
- main.py
- requirements.txt  
  - in this file you can find the dependencies needed for this project
- seed.json 
  - in this file you can find a seed that allows for interesting behaviour of the agents


To run the code of the repository, you can clone it using git clone https://github.com/petervdbempt/llm_theory_of_mind.git 
CD into the llm_theory_of_mind folder and run pip install -r requirements.txt
Create an API_token_<llama/gemini/claude>.txt with an API key for the corresponding 
LLM.

In order to run a game you can use this command and specify the options as wished:
python main.py --p1-agent <LLAMA/GREEDY/CLAUDE/GEMINI/TOM> --p2-agent <LLAMA/GREEDY/CLAUDE/GEMINI/TOM> --set-global-seed  --load-scenario .\seed.json

The load scenario with the seed.json makes sure that you will run the game on our found seed that had some interesting properties. Not using a seed might give game boards or distributions that do not require
any negotiation for example. 

If chosen to use any player as TOM agent, use: --p<1/2>-tom-order <0/1/2> to specify the order of TOM for player 1 or 2

You can also add --tournament to run the tournament mode such that the agents will play more games in a row. Be aware that 
you only have limited tokens a day on a free account for the LLMs. 

![seed14gamestateplot.png](plots/seed14gamestateplot.png)

Here you can see the board of seed14


paper 1*: de Weerd, H., Verbrugge, R. & Verheij, B. Negotiating with other minds: the role of recursive theory of mind in negotiation with incomplete information. Auton Agent Multi-Agent Syst 31, 250–287 (2017). https://doi.org/10.1007/s10458-015-9317-1
