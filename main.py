import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
import numpy as np

from game.colored_trails import (
    ColoredTrails,
    GameState,
    PENALTY_PER_ROUND,
    BOARD_SIZE,
    START_POS,
    COLORS
)
from agents.llm_player_gemini import LLMPlayer

MAX_NEGOTIATION_ROUNDS = 5

COLOR_TO_VALUE = {"RE": 0, "BL": 1, "YE": 2, "GR": 3, "OR": 4}
HEX_COLORS = ['#DC143C', '#1E90FF', '#FFD700', '#32CD32', '#FF8C00']

COLOR_MAP = mcolors.ListedColormap(HEX_COLORS)
BOUNDS = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5]
NORM = mcolors.BoundaryNorm(BOUNDS, COLOR_MAP.N)


def plot_game_state(game: ColoredTrails):
    """Generates and displays a Matplotlib visualization of the game board and state."""

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
    plt.show()


def run_game_simulation(game: ColoredTrails, player_type: str = 'LLM'):
    """
    Runs the full simulation of the negotiation phase followed by scoring.
    Supports multi-chip trades (any redistribution).
    player_type: 'LLM' (uses LLMPlayer) or 'GREEDY' (simple heuristic agent).
    """

    print("--- Starting negotiation phase. ---")

    # Small local GreedyPlayer implementation for testing / non-LLM runs
    class GreedyPlayer:
        def __init__(self, player_id: str, game_env: ColoredTrails):
            self.player_id = player_id
            self.opponent_id = "p2" if player_id == "p1" else "p1"
            self.game = game_env
            self.history = []

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
                hypo[chip] = hypo.get(chip, 0) - 1
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
            self.history.append(f"{self.player_id} {'ACCEPTED' if accept else 'REJECTED'} offer ({opp_give} for {opp_receive})")
            return accept

    # Build agents according to the requested type
    if player_type.upper() == 'LLM':
        player_agents = {
            'p1': LLMPlayer(player_id='p1', game_env=game),
            'p2': LLMPlayer(player_id='p2', game_env=game)
        }
    else:
        player_agents = {
            'p1': GreedyPlayer(player_id='p1', game_env=game),
            'p2': GreedyPlayer(player_id='p2', game_env=game)
        }

    offers_made = {'p1': 0, 'p2': 0}
    trade_made = False

    print("\n" + "=" * 60)
    print("      COLORED TRAILS: STARTING NEGOTIATION LOG")
    print("=" * 60)
    print("\nInitial Chip Distribution (Player Hands):")
    for player_id, state in game.states.items():
        chip_str = ", ".join([f"{count}x{color}" for color, count in state.chips.items()])
        print(f" - {player_id.upper()} (Goal:{state.goal_pos}): {chip_str}")

    # Negotiation loop: up to MAX_NEGOTIATION_ROUNDS rounds; each round p1 then p2 propose
    for round_num in range(1, MAX_NEGOTIATION_ROUNDS + 1):
        print(f"\n{'=' * 60}")
        print(f"ROUND {round_num}")
        print(f"{'=' * 60}")

        for proposer_id in ['p1', 'p2']:
            responder_id = 'p2' if proposer_id == 'p1' else 'p1'
            proposer_agent = player_agents[proposer_id]
            responder_agent = player_agents[responder_id]

            print(f"\n--- {proposer_id.upper()}'s Turn to Propose ---")
            proposer_give, proposer_receive = proposer_agent.propose_trade()

            # Normalize possible string "Pass" vs list ["Pass"]
            if isinstance(proposer_give, str):
                proposer_give = [proposer_give]
            if isinstance(proposer_receive, str):
                proposer_receive = [proposer_receive]

            # If proposer passes, negotiation ends immediately (no penalty increment for a pass)
            if proposer_give == ["Pass"] or (len(proposer_give) == 1 and proposer_give[0].upper() == "PASS"):
                print(f"  -> {proposer_id.upper()} passes. Negotiation ends.")
                # record history already taken care of by agent; just break
                trade_made = False
                break

            # Count this as an offer made by proposer
            offers_made[proposer_id] += 1

            print(
                f"  -> PROPOSAL: {proposer_id.upper()} offers to GIVE: {proposer_give} "
                f"for RECEIVING: {proposer_receive} from {responder_id.upper()}"
            )

            # Responder evaluates the offer
            # Note semantics: proposer_give = chips proposer gives (so responder receives these),
            # proposer_receive = chips proposer wants (so responder must give these)
            responder_proposal = (proposer_give, proposer_receive)
            acceptance = responder_agent.evaluate_proposal(responder_proposal)

            if acceptance:
                print(f"  -> {responder_id.upper()} ACCEPTS the trade!")
                ok = game.apply_trade(
                    p1_id=proposer_id,
                    p2_id=responder_id,
                    p1_give=proposer_give,
                    p1_receive=proposer_receive
                )
                if not ok:
                    print("  -> Trade application failed due to invalid availability. Continue negotiation.")
                    # if trade failed due to validation, treat as rejection for negotiation continuation
                    continue

                # Print the immediate result of the trade
                print(f"  -> Chips after trade:")
                print(f"     - P1 Chips: {dict(game.states['p1'].chips)}")
                print(f"     - P2 Chips: {dict(game.states['p2'].chips)}")

                trade_made = True
                break
            else:
                print(f"  -> {responder_id.upper()} REJECTS the trade.")

        # end for proposer loop
        # If a trade was made or a pass ended negotiation, stop negotiating
        # (Note: pass sets proposer_give == ["Pass"] and breaks out earlier)
        if trade_made or (proposer_give == ["Pass"]):
            break

    print("\n" + "=" * 60)
    print("--- NEGOTIATION PHASE ENDED ---")

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

    print("\n--- FINAL RESULTS ---")
    print(f"P1 Offers Made: {offers_made['p1']} (Penalty: {p1_penalty} points)")
    print(f"P2 Offers Made: {offers_made['p2']} (Penalty: {p2_penalty} points)")
    print(f"\nP1 Final Score: {p1_final_score} (Max Path Score: {p1_max_score})")
    print(f"P2 Final Score: {p2_final_score} (Max Path Score: {p2_max_score})")

    if p1_final_score > p2_final_score:
        print("\nWINNER: Player 1 (p1)")
    elif p2_final_score > p1_final_score:
        print("\nWINNER: Player 2 (p2)")
    else:
        print("\nRESULT: TIE")

    print("=" * 60)

    # --- VISUALIZE FINAL STATE ---
    plot_game_state(game)


if __name__ == "__main__":
    # Set up the game
    board_map, player_states = ColoredTrails.generate_random_game()
    game = ColoredTrails(board_map, player_states)

    # Set the desired player type here. Options: 'GREEDY' or 'LLM'
    AGENT_TO_USE = 'LLM'

    # Run the simulation and plot the result
    run_game_simulation(game, player_type=AGENT_TO_USE)
