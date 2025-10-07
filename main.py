import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
import numpy as np

# Import the core components, including the necessary module-level constants
from game.colored_trails import (
    ColoredTrails,
    GameState,
    PENALTY_PER_ROUND,
    BOARD_SIZE,
    START_POS,
    COLORS
)
from agents.greedy_player import GreedyPlayer

MAX_NEGOTIATION_ROUNDS = 5  # Set a limit for the negotiation phase

# Matplotlib color mapping configuration (Hot Desert color scheme)
# 1. Define value mapping for the board strings
COLOR_TO_VALUE = {"BROWN": 0, "DARK ORANGE": 1, "LIGHT ORANGE": 2, "YELLOW": 3, "BEIGE": 4}
# 2. Define the actual colors for the colormap
HEX_COLORS = ['#912C0C', '#F37031', '#F7A741', '#EFDE63', '#C59960']

COLOR_MAP = mcolors.ListedColormap(HEX_COLORS)
# 3. Define boundary positions for the colormap
BOUNDS = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5]
NORM = mcolors.BoundaryNorm(BOUNDS, COLOR_MAP.N)


def plot_game_state(game: ColoredTrails):
    """Generates and displays a Matplotlib visualization of the game board and state."""

    # 1. Prepare Data Matrix
    # Convert the string board (BLACK, GRAY, WHITE) into a numerical matrix (0, 1, 2)
    board_matrix = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            board_matrix[r, c] = COLOR_TO_VALUE[game.board[r][c]]

    # 2. Setup Plot
    fig, ax = plt.subplots(figsize=(6, 6))

    # Draw the colored board
    cax = ax.imshow(board_matrix, cmap=COLOR_MAP, norm=NORM)

    # Add grid lines
    ax.set_xticks(np.arange(-0.5, BOARD_SIZE, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, BOARD_SIZE, 1), minor=True)
    ax.grid(which="minor", color="black", linestyle='-', linewidth=2)
    ax.tick_params(which="minor", size=0)

    # Set tick labels (coordinates)
    ax.set_xticks(np.arange(BOARD_SIZE))
    ax.set_yticks(np.arange(BOARD_SIZE))
    ax.set_xticklabels(np.arange(BOARD_SIZE))
    ax.set_yticklabels(np.arange(BOARD_SIZE))
    ax.set_xlabel("Column (C)")
    ax.set_ylabel("Row (R)")

    # 3. Add Markers (Start and Goals)
    s_pos = START_POS
    g1_pos = game.states['p1'].goal_pos
    g2_pos = game.states['p2'].goal_pos

    # Start Position (S)
    ax.text(s_pos[1], s_pos[0], 'S', ha='center', va='center', fontsize=20, color='black',
            path_effects=[
                pe.withStroke(linewidth=1, foreground='white')
            ])

    # P1 Goal (1)
    ax.text(g1_pos[1], g1_pos[0], '1️', ha='center', va='center', fontsize=20, color='black',
            path_effects=[
                pe.withStroke(linewidth=1, foreground='white')
            ])

    # P2 Goal (2)
    # Use a different visual style if goals overlap, but for simplicity, just stack/overlay
    if g2_pos != g1_pos:
        ax.text(g2_pos[1], g2_pos[0], '2️', ha='center', va='center', fontsize=20, color='black',
                path_effects=[
                    pe.withStroke(linewidth=1, foreground='white')
                ])

    # 5. Add Title
    title_text = "Colored Trails Board State"

    # Use fig.suptitle for the main title
    fig.suptitle(title_text, fontsize=16, fontweight='bold')
    plt.show()  # Display the plot


def run_game_simulation(game: ColoredTrails):
    """
    Runs the full simulation of the negotiation phase followed by scoring.
    Each round now consists of both players making proposals (if they choose to).
    """
    # Initialize the two dummy LLM players
    player_agents = {
        'p1': GreedyPlayer(player_id='p1', game_env=game),
        'p2': GreedyPlayer(player_id='p2', game_env=game)
    }

    # Track how many offers each player made (for penalty calculation)
    offers_made = {'p1': 0, 'p2': 0}

    trade_made = False

    print("\n" + "=" * 60)
    print("      COLORED TRAILS: STARTING NEGOTIATION LOG")
    print("=" * 60)
    print("\nInitial Chip Distribution (Player Hands):")
    for player_id, state in game.states.items():
        chip_str = ", ".join([f"{count}x{color}" for color, count in state.chips.items()])
        print(f" - {player_id.upper()} (Goal:{state.goal_pos}): {chip_str}")

    # We use offers_made to track the negotiation penalty per player
    for round_num in range(1, MAX_NEGOTIATION_ROUNDS + 1):
        print(f"\n{'=' * 60}")
        print(f"ROUND {round_num}")
        print(f"{'=' * 60}")

        # Each round, both players get a chance to propose
        for proposer_id in ['p1', 'p2']:
            responder_id = 'p2' if proposer_id == 'p1' else 'p1'
            proposer_agent = player_agents[proposer_id]
            responder_agent = player_agents[responder_id]

            # Proposer makes an offer (Give_Chip, Receive_Chip)
            proposer_give, proposer_receive = proposer_agent.propose_trade()

            print(f"\n--- {proposer_id.upper()}'s Turn ---")

            if proposer_give == "Pass":
                print(f"  -> {proposer_id.upper()} passes. Negotiation ends.")
                trade_made = True  # Use this flag to break out of both loops
                break  # Break out of player loop

            # Count this as an offer made
            offers_made[proposer_id] += 1

            print(
                f"  -> PROPOSAL: {proposer_id.upper()} offers to GIVE: {proposer_give} "
                f"for RECEIVING: {proposer_receive} from {responder_id.upper()}")

            # Responder evaluates the offer
            # The offer is: Responder gives `proposer_receive` and receives `proposer_give`
            responder_proposal = (proposer_give, proposer_receive)
            acceptance = responder_agent.evaluate_proposal(responder_proposal)

            if acceptance:
                print(f"  -> {responder_id.upper()} ACCEPTS the trade!")
                # Apply the trade to the central game state
                game.apply_trade(
                    p1_id=proposer_id,
                    p2_id=responder_id,
                    p1_give=proposer_give,
                    p1_receive=proposer_receive
                )
                trade_made = True

                # Print the immediate result of the trade
                print(f"  -> Chips after trade:")
                print(f"     - P1 Chips: {dict(game.states['p1'].chips)}")
                print(f"     - P2 Chips: {dict(game.states['p2'].chips)}")

                # NEW: End negotiation immediately after a successful trade
                break
            else:
                print(f"  -> {responder_id.upper()} REJECTS the trade.")

        # If a trade was made, break out of the round loop
        if trade_made:
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

    # Run the simulation and plot the result
    run_game_simulation(game)