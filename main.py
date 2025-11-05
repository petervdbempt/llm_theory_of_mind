import argparse

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
import numpy as np
from pathlib import Path
from itertools import product
from utils.text_logger import TextLogger

import sys
import io
import statistics

sys.stdout.reconfigure(encoding='utf-8')

from game.colored_trails import (
    ColoredTrails,
    GameState,
    PENALTY_PER_ROUND,
    BOARD_SIZE,
    START_POS,
    COLORS, load_scenario_json, save_scenario_json
)
from agents.llm_player_llama import LlamaMPlayer
from agents.llm_player_claude import ClaudePlayer
from agents.llm_player_gemini import LLMPlayer as GeminiPlayer

from agents.tom_agent import ToMAgent  # New import

MAX_NEGOTIATION_ROUNDS = 5

COLOR_TO_VALUE = {"RE": 0, "BL": 1, "YE": 2, "GR": 3, "OR": 4}
HEX_COLORS = ['#DC143C', '#1E90FF', '#FFD700', '#32CD32', '#FF8C00']

COLOR_MAP = mcolors.ListedColormap(HEX_COLORS)
BOUNDS = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5]
NORM = mcolors.BoundaryNorm(BOUNDS, COLOR_MAP.N)


def set_global_seed(seed: int):
    # set a seed to increase reproducability
    import random
    random.seed(seed)
    np.random.seed(seed)


def print_quick_metrics(game: ColoredTrails):
    # Function just to quickly see whether seed is promising and we should try it
    p1_score, p1_steps, _ = game.get_max_score_and_path('p1')
    p2_score, p2_steps, _ = game.get_max_score_and_path('p2')
    g1 = game.states['p1'].goal_pos
    g2 = game.states['p2'].goal_pos

    hist = {c: 0 for c in COLORS}
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            hist[game.board[r][c]] += 1

    print("\n--- QUICK METRICS ---")
    print(f" P1: steps_to_goal={p1_steps}, path_score={p1_score}")
    print(f" P2: steps_to_goal={p2_steps}, path_score={p2_score}")
    print(" Board color counts:", hist)
    print(" P1 chips:", dict(game.states['p1'].chips))
    print(" P2 chips:", dict(game.states['p2'].chips))


def plot_game_state(game: ColoredTrails, save=False, save_path: Path = None):
    # Generates and displays a Matplotlib visualization of the game board and state.

    board_matrix = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            board_matrix[r, c] = COLOR_TO_VALUE[game.board[r][c]]

    fig, ax = plt.subplots(figsize=(6, 6))
    cax = ax.imshow(board_matrix, cmap=COLOR_MAP, norm=NORM)

    ax.set_xticks(np.arange(-0.5, BOARD_SIZE, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, BOARD_SIZE, 1), minor=True)
    ax.grid(which="minor", color="black", linestyle='-', linewidth=2)
    ax.tick_params(which="minor", size=0)

    ax.set_xticks(np.arange(BOARD_SIZE))
    ax.set_yticks(np.arange(BOARD_SIZE))
    ax.set_xticklabels(np.arange(BOARD_SIZE))
    ax.set_yticklabels(np.arange(BOARD_SIZE))
    ax.set_xlabel("Column (C)")
    ax.set_ylabel("Row (R)")

    s_pos = START_POS
    g1_pos = game.states['p1'].goal_pos
    g2_pos = game.states['p2'].goal_pos

    ax.text(s_pos[1], s_pos[0], 'S', ha='center', va='center', fontsize=20, color='black',
            path_effects=[pe.withStroke(linewidth=1, foreground='white')])

    ax.text(g1_pos[1], g1_pos[0], '1️', ha='center', va='center', fontsize=20, color='black',
            path_effects=[pe.withStroke(linewidth=1, foreground='white')])

    if g2_pos != g1_pos:
        ax.text(g2_pos[1], g2_pos[0], '2️', ha='center', va='center', fontsize=20, color='black',
                path_effects=[pe.withStroke(linewidth=1, foreground='white')])

    title_text = "Colored Trails Board State"
    fig.suptitle(title_text, fontsize=16, fontweight='bold')
    if not save:
        plt.show()
    else:
        plt.savefig(save_path, dpi=150)
    plt.close(fig)



def run_game_simulation(game: ColoredTrails, p1_type: str = 'LLAMA', p2_type: str = 'LLAMA',
                        tom_order_p1: int = 1, tom_order_p2: int = 1, tournament=False,
                        logger: TextLogger | None = None):
    """
    Runs the full simulation of the negotiation phase followed by scoring.
    Supports multiple agent types:
    - 'LLAMA': Uses LLAMA player
    - 'GEMINI': Uses GEMINI player
    - 'CLAUDE': Uses CLAUDE player
    - 'GREEDY': Simple greedy heuristic
    - 'TOM': Theory of Mind agent with specified order

    Args:
        game: The ColoredTrails game instance
        p1_type: Agent type for player 1 ('LLAMA', 'GEMINI', 'CLAUDE', 'GREEDY', 'TOM')
        p2_type: Agent type for player 2 ('LLAMA', 'GEMINI', 'CLAUDE', 'GREEDY', 'TOM')
        tom_order_p1: ToM order for p1 if p1_type='TOM' (0, 1, 2, ...)
        tom_order_p2: ToM order for p2 if p2_type='TOM' (0, 1, 2, ...)
    """
    def log(msg):
        if logger:
            logger.log(msg)
        else:
            print(msg)

    # Small local GreedyPlayer implementation for testing / non-LLM runs
    class GreedyPlayer:
        def __init__(self, player_id: str, game_env: ColoredTrails, logger: TextLogger | None = None):
            self.player_id = player_id
            self.opponent_id = "p2" if player_id == "p1" else "p1"
            self.game = game_env
            self.history = []
            self.logger = logger
            
        def _log(self, msg: str):
            if self.logger:
                self.logger.log(f"[{self.player_id}] {msg}")
            else:
                print(f"[{self.player_id}] {msg}")

        def propose_trade(self):
            # Greedy player never proposes (always passes)
            self.history.append(f"{self.player_id} PASSED")
            return ["Pass"], ["Pass"]

        def evaluate_proposal(self, proposal):
            # Accept only if the trade strictly improves the responder's utility.
            opp_give, opp_receive = proposal
            my_state = self.game.states[self.player_id]

            if opp_give == ["Pass"]:
                self.history.append(f"{self.opponent_id} PASSED")
                return True

            # Validate availability (responder must have the chips proposer asks for)
            opp_receive_counter = {}
            for chip in opp_receive:
                opp_receive_counter[chip] = opp_receive_counter.get(chip, 0) + 1

            for chip, count in opp_receive_counter.items():
                if my_state.chips.get(chip, 0) < count:
                    self.history.append(f"{self.player_id} REJECT (missing {chip})")
                    return False

            # compute utility delta
            current_score, _, _ = self.game.get_max_score_and_path(self.player_id)

            hypo = dict(my_state.chips)
            # Responder receives opp_give
            for chip in opp_give:
                hypo[chip] = hypo.get(chip, 0) + 1
            # Responder gives opp_receive
            for chip in opp_receive:
                hypo[chip] -= 1
                if hypo[chip] == 0:
                    del hypo[chip]

            # Make a temporary state to compute utility
            temp_state = {
                self.player_id: GameState(goal_pos=self.game.states[self.player_id].goal_pos, chips=hypo),
                self.opponent_id: self.game.states[self.opponent_id]
            }
            temp_game = ColoredTrails(self.game.board, temp_state)
            new_score, _, _ = temp_game.get_max_score_and_path(self.player_id)

            accept = new_score > current_score
            self.history.append(
                f"{self.player_id} {'ACCEPTED' if accept else 'REJECTED'} offer ({opp_give} for {opp_receive})")
            return accept

    # Build agents according to the requested types
    def create_agent(player_id: str, agent_type: str, tom_order: int):
        agent_type = agent_type.upper()
        if agent_type == 'LLAMA':
            return LlamaMPlayer(player_id=player_id, game_env=game, logger=logger)
        elif agent_type == 'GREEDY':
            return GreedyPlayer(player_id=player_id, game_env=game, logger=logger)
        elif agent_type == 'TOM':
            return ToMAgent(player_id=player_id, game_env=game, order=tom_order, logger=logger)
        elif agent_type == 'CLAUDE':
            return ClaudePlayer(player_id=player_id, game_env=game, logger=logger)
        elif agent_type == 'GEMINI':
            return GeminiPlayer(player_id=player_id, game_env=game, logger=logger)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

    player_agents = {
        'p1': create_agent('p1', p1_type, tom_order_p1),
        'p2': create_agent('p2', p2_type, tom_order_p2)
    }

    offers_made = {'p1': 0, 'p2': 0}
    trade_made = False
    negotiation_ended = False

    log("\n" + "=" * 60)
    log("      COLORED TRAILS: STARTING NEGOTIATION LOG")
    log("=" * 60)
    log(f"\nAgent Configuration:")
    log(f" - P1: {p1_type}" + (f" (Order {tom_order_p1})" if p1_type.upper() == 'TOM' else ""))
    log(f" - P2: {p2_type}" + (f" (Order {tom_order_p2})" if p2_type.upper() == 'TOM' else ""))

    log("\nInitial Chip Distribution (Player Hands):")
    for player_id, state in game.states.items():
        chip_str = ", ".join([f"{count}x{color}" for color, count in state.chips.items()])
        log(f" - {player_id.upper()} (Goal:{state.goal_pos}): {chip_str}")

    # Negotiation loop: up to MAX_NEGOTIATION_ROUNDS rounds; each round p1 then p2 propose
    for round_num in range(1, MAX_NEGOTIATION_ROUNDS + 1):
        if negotiation_ended:
            break

        log(f"\n{'=' * 60}")
        log(f"ROUND {round_num}")
        log(f"{'=' * 60}")

        for proposer_id in ['p1', 'p2']:
            responder_id = 'p2' if proposer_id == 'p1' else 'p1'
            proposer_agent = player_agents[proposer_id]
            responder_agent = player_agents[responder_id]

            log(f"\n--- {proposer_id.upper()}'s Turn to Propose ---")
            proposer_give, proposer_receive = proposer_agent.propose_trade()

            # Normalize possible string "Pass" vs list ["Pass"]
            if isinstance(proposer_give, str):
                proposer_give = [proposer_give]
            if isinstance(proposer_receive, str):
                proposer_receive = [proposer_receive]

            # Check for Pass
            is_pass = proposer_give == ["Pass"] or (len(proposer_give) == 1 and proposer_give[0].upper() == "PASS")

            if is_pass:
                log(f"  -> {proposer_id.upper()} passes. Negotiation ends.")
                negotiation_ended = True
                break

            # Count this as an offer made by proposer
            offers_made[proposer_id] += 1

            log(
                f"  -> PROPOSAL: {proposer_id.upper()} offers to GIVE: {proposer_give} "
                f"for RECEIVING: {proposer_receive} from {responder_id.upper()}"
            )

            # Responder evaluates the offer
            responder_proposal = (proposer_give, proposer_receive)
            acceptance = responder_agent.evaluate_proposal(responder_proposal)

            if acceptance:
                log(f"  -> {responder_id.upper()} ACCEPTS the trade!")
                ok = game.apply_trade(
                    p1_id=proposer_id,
                    p2_id=responder_id,
                    p1_give=proposer_give,
                    p1_receive=proposer_receive
                )
                if not ok:
                    log("  -> Trade application failed due to invalid availability. Continue negotiation.")
                    continue

                # log the immediate result of the trade
                log(f"  -> Chips after trade:")
                log(f"     - P1 Chips: {dict(game.states['p1'].chips)}")
                log(f"     - P2 Chips: {dict(game.states['p2'].chips)}")

                trade_made = True
                negotiation_ended = True
                break
            else:
                log(f"  -> {responder_id.upper()} REJECTS the trade.")

        if negotiation_ended:
            break

    log("\n" + "=" * 60)
    log("--- NEGOTIATION PHASE ENDED ---")

    # --- FINAL SCORING ---
    final_scores = {}

    # Calculate final max scores (utility) based on final chip counts
    p1_max_score, _, _ = game.get_max_score_and_path('p1')
    p2_max_score, _, _ = game.get_max_score_and_path('p2')

    # Apply individual penalties based on offers made
    p1_penalty = offers_made['p1'] * PENALTY_PER_ROUND
    p2_penalty = offers_made['p2'] * PENALTY_PER_ROUND

    p1_final_score = p1_max_score - p1_penalty
    p2_final_score = p2_max_score - p2_penalty

    final_scores['p1'] = p1_final_score
    final_scores['p2'] = p2_final_score

    log("\n--- FINAL RESULTS ---")
    log(f"P1 Offers Made: {offers_made['p1']} (Penalty: {p1_penalty} points)")
    log(f"P2 Offers Made: {offers_made['p2']} (Penalty: {p2_penalty} points)")
    log(f"\nP1 Final Score: {p1_final_score} (Max Path Score: {p1_max_score})")
    log(f"P2 Final Score: {p2_final_score} (Max Path Score: {p2_max_score})")

    if p1_final_score > p2_final_score:
        log("\nWINNER: Player 1 (p1)")
    elif p2_final_score > p1_final_score:
        log("\nWINNER: Player 2 (p2)")
    else:
        log("\nRESULT: TIE")

    log("=" * 60)
    if not tournament:
        plot_game_state(game)



def run_tournament(args, games=1, use_seeds = False):
    seeds = [] 
    
    base_log_dir = Path("tournament_logs")
    base_log_dir.mkdir(exist_ok=True)

    agent_types = [ "CLAUDE", "GEMINI"]
    # agent_types = ["GREEDY", "LLAMA", "CLAUDE", "GEMINI", "TOM"]
    tom_orders = [0, 1, 2]  # ToM orders to test

    def make_agent_configs():
        configs = []
        for a_type in agent_types:
            if a_type == "TOM":
                for order in tom_orders:
                    configs.append((a_type, order))
            else:
                configs.append((a_type, None))
        return configs

    agent_configs = make_agent_configs()

    def allow_self_play(a_type):
        return a_type in ["LLAMA", "CLAUDE", "GEMINI"]

    matchups = []
    for (a1_type, a1_order), (a2_type, a2_order) in product(agent_configs, repeat=2):
        if a1_type == a2_type and a1_order == a2_order:
            if allow_self_play(a1_type):
                matchups.append(((a1_type, a1_order), (a2_type, a2_order)))
        else:
            matchups.append(((a1_type, a1_order), (a2_type, a2_order)))

    print(f"Running tournament with {len(matchups)} matchups")

    for (a1_type, a1_order), (a2_type, a2_order) in matchups:
        match_name = (
            f"{a1_type}{'' if a1_order is None else f'_O{a1_order}'}"
            f"_vs_"
            f"{a2_type}{'' if a2_order is None else f'_O{a2_order}'}"
        )

        match_dir = base_log_dir / match_name
        match_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nStarting {games} games: {match_name}")

        results = []

        for game_num in range(1, games+1):
            
            if use_seeds:
                game_seed = seeds[game_num-1]
                set_global_seed(game_seed)
            else:
                game_seed = None
            
            if game_num <= 5:
                p1_type, p1_order = a1_type, a1_order
                p2_type, p2_order = a2_type, a2_order
            else:
                p1_type, p1_order = a2_type, a2_order
                p2_type, p2_order = a1_type, a1_order

            log_path = match_dir / f"game_{game_num}.log"
            logger = TextLogger(log_path)

            logger.log(f"Starting game {game_num} with seed {game_seed}" if game_seed is not None else f"Starting game {game_num}")
            board_map, player_states = ColoredTrails.generate_random_game(seed=game_num)
            game = ColoredTrails(board_map, player_states)

            run_game_simulation(
                game,
                p1_type=p1_type,
                p2_type=p2_type,
                tom_order_p1=p1_order or 1,
                tom_order_p2=p2_order or 1,
                tournament=True,
                logger=logger
            )

            plot_game_state(game, save=True, save_path=match_dir / f"game_{game_num}.png")
            logger.close()
            
            # Write full captured log
            log_text = log_path.read_text(encoding="utf-8")
            p1_score = p2_score = None
            winner = "Tie"
            for line in log_text.splitlines():
                if "P1 Final Score:" in line:
                    p1_score = float(line.split()[3])
                elif "P2 Final Score:" in line:
                    p2_score = float(line.split()[3])
                elif "WINNER:" in line:
                    winner = line.split(":")[-1].strip()

            results.append({
                "game": game_num,
                "p1_type": p1_type,
                "p2_type": p2_type,
                "p1_score": p1_score,
                "p2_score": p2_score,
                "winner": winner,
            })

            print(f"Game {game_num} finished log saved to {log_path.name}")

        summary_path = match_dir / "summary.log"
        summary_lines = [f"SUMMARY FOR MATCHUP: {match_name}\n", "=" * 60 + "\n"]

        total_p1_wins = sum(1 for r in results if r["winner"] == "Player 1 (p1)")
        total_p2_wins = sum(1 for r in results if r["winner"] == "Player 2 (p2)")
        total_ties = len(results) - total_p1_wins - total_p2_wins

        p1_scores = [r["p1_score"] for r in results if r["p1_score"] is not None]
        p2_scores = [r["p2_score"] for r in results if r["p2_score"] is not None]

        avg_p1 = statistics.mean(p1_scores) if p1_scores else 0
        avg_p2 = statistics.mean(p2_scores) if p2_scores else 0

        summary_lines.append(f"Total games: {len(results)}\n")
        summary_lines.append(f"Player 1 wins: {total_p1_wins}\n")
        summary_lines.append(f"Player 2 wins: {total_p2_wins}\n")
        summary_lines.append(f"Ties: {total_ties}\n\n")
        summary_lines.append(f"Average P1 score: {avg_p1:.2f}\n")
        summary_lines.append(f"Average P2 score: {avg_p2:.2f}\n\n")
        summary_lines.append("Detailed results:\n")

        for r in results:
            summary_lines.append(
                f"  Game {r['game']:>2}: {r['p1_type']} (P1={r['p1_score']}) vs "
                f"{r['p2_type']} (P2={r['p2_score']}) -> Winner: {r['winner']}\n"
            )

        summary_path.write_text("".join(summary_lines), encoding="utf-8")

        print(f"Match completed summary written to {summary_path.name}")



def parse_args():
    p = argparse.ArgumentParser(description="Colored Trails runner with multiple agent types.")
    p.add_argument("--seed", type=int, default=None, help="Deterministic seed for board/chips/goals.")
    p.add_argument("--save-scenario", type=str, default=None, help="Path to save current scenario JSON.")
    p.add_argument("--load-scenario", type=str, default=None, help="Path to load an existing scenario JSON.")
    p.add_argument("--tournament", action="store_true", help="Run in tournament mode.")

    p.add_argument("--p1-agent", type=str, default="LLAMA",
                   choices=["LLAMA", "GREEDY", "CLAUDE", "GEMINI", "TOM"],
                   help="Agent type for Player 1")
    p.add_argument("--p2-agent", type=str, default="LLAMA",
                   choices=["LLAMA", "GREEDY", "TOM"],
                   help="Agent type for Player 2")

    p.add_argument("--p1-tom-order", type=int, default=1,
                   help="Theory of Mind order for P1 (if --p1-agent=TOM). 0=basic, 1+=recursive")
    p.add_argument("--p2-tom-order", type=int, default=1,
                   help="Theory of Mind order for P2 (if --p2-agent=TOM). 0=basic, 1+=recursive")

    p.add_argument("--set-global-seed", action="store_true",
                   help="Also set global seeds (numpy, python random) for full determinism.")
    return p.parse_args()


def main(args):
    if args.set_global_seed and args.seed is not None:
        set_global_seed(args.seed)

    # Build or load game based on a seed
    if args.load_scenario:
        board_map, player_states = load_scenario_json(args.load_scenario)
        seed_used = None
        print(f"Loaded scenario from {args.load_scenario}")
    else:
        board_map, player_states = ColoredTrails.generate_random_game(seed=args.seed)
        seed_used = args.seed
        if seed_used is not None:
            print(f"Generated new scenario with seed={seed_used}")

    game = ColoredTrails(board_map, player_states)

    # for seeing if seed is promising enough to waste time on
    print_quick_metrics(game)

    # save the seed for quick load
    if args.save_scenario:
        save_scenario_json(args.save_scenario, board_map, player_states, seed=seed_used)
        print(f"Scenario saved to {args.save_scenario}")

    run_game_simulation(game,
                        p1_type=args.p1_agent,
                        p2_type=args.p2_agent,
                        tom_order_p1=args.p1_tom_order,
                        tom_order_p2=args.p2_tom_order)



if __name__ == "__main__":
    args = parse_args()
    if args.tournament:
        run_tournament(args)
    else:   
        main(args)


    # examples
    # python main.py --p1-agent LLAMA --p2-agent LLAMA --seed 42
    # python main.py --p1-agent TOM --p2-agent TOM --p1-tom-order 1 --p2-tom-order 1 --seed 42
