"""
Belief Visualization for ToM Agents (mostly a debugging tool)
Shows how beliefs evolve during negotiation
"""

from game.colored_trails import ColoredTrails
from agents.tom_agent import ToMAgent
import json


def display_belief_changes(agent: ToMAgent, round_num: int):
    """Display how an agent's beliefs have changed"""
    print(f"\n{'=' * 50}")
    print(f"BELIEF STATE - {agent.player_id} (Order-{agent.order}) - Round {round_num}")
    print(f"{'=' * 50}")

    summary = agent.get_belief_summary()

    if agent.order == 0:
        print("\nACCEPTANCE RATE BELIEFS:")
        print(f"   Top acceptance rates:")
        for offer, rate in summary.get('top_acceptance_rates', []):
            give, receive = offer
            print(f"   • Give {list(give)} for {list(receive)}: {rate:.3f}")

        print("\n   Belief matrix sample (pos\\neg):")
        matrix = summary.get('belief_matrix_sample', [])
        print("     ", "  0    1    2")
        for i, row in enumerate(matrix):
            print(f"   {i}: {' '.join(row)}")

    else:
        print(f"\nLOCATION BELIEFS (Confidence: {summary.get('confidence', 0):.3f}):")
        for belief in summary.get('top_goal_beliefs', []):
            loc = belief['location']
            prob = belief['probability']
            print(f"   • Goal at {loc}: {prob}")

        if hasattr(agent, 'confidence_history') and agent.confidence_history:
            print(f"\n   Confidence trend: ", end="")
            for conf in agent.confidence_history[-5:]:
                print(f"{conf:.2f} ", end="")
            print()

    # Show belief history for ToM0Model
    if agent.order == 0 and hasattr(agent.opponent_model, 'belief_history'):
        history = agent.opponent_model.belief_history
        if history and len(history) > 1:
            print("\nLEARNING PROGRESSION:")
            print(f"   Observations made: {len(history)}")

            # Show how a specific offer's acceptance rate changed
            sample_offer = (["RE"], ["BL"])
            sample_key = str(sample_offer)

            rates = []
            for snapshot in history:
                if sample_key in snapshot.get('acceptance_rates', {}):
                    rates.append(snapshot['acceptance_rates'][sample_key])

            if rates:
                print(f"   Acceptance rate for {sample_offer} over time:")
                print(f"   Start: {rates[0]:.3f} → Now: {rates[-1]:.3f}")


def run_game_with_belief_tracking():
    """Run a simple game showing belief evolution"""
    print("\n" + "=" * 60)
    print("COLORED TRAILS WITH BELIEF TRACKING")
    print("=" * 60)

    # Create game
    board_map, player_states = ColoredTrails.generate_random_game(seed=42)
    game = ColoredTrails(board_map, player_states)

    # Create agents
    agent_p1 = ToMAgent('p1', game, order=0)  # Order-0 agent
    agent_p2 = ToMAgent('p2', game, order=1)  # Order-1 agent

    print(f"\nInitial Setup:")
    print(f"P1 (Order-0): {dict(game.states['p1'].chips)} → Goal: {game.states['p1'].goal_pos}")
    print(f"P2 (Order-1): {dict(game.states['p2'].chips)} → Goal: {game.states['p2'].goal_pos}")

    # Initial belief states
    display_belief_changes(agent_p1, 0)
    display_belief_changes(agent_p2, 0)

    # Simulate negotiation rounds
    for round_num in range(1, 4):
        print(f"\n{'=' * 60}")
        print(f"ROUND {round_num}")
        print(f"{'=' * 60}")

        # P1 proposes
        print("\n→ P1 proposes:")
        give1, receive1 = agent_p1.propose_trade()
        print(f"  Offer: Give {give1} for {receive1}")

        # P2 evaluates
        accept = agent_p2.evaluate_proposal((give1, receive1))
        print(f"  P2 response: {'ACCEPT' if accept else 'REJECT'}")

        if accept and give1 != ["Pass"]:
            # Apply trade
            game.apply_trade('p1', 'p2', give1, receive1)
            print(f"  Trade completed!")
            break
        elif give1 == ["Pass"]:
            print(f"  P1 passed, negotiation ends")
            break

        # P2 proposes
        print("\n→ P2 proposes:")
        give2, receive2 = agent_p2.propose_trade()
        print(f"  Offer: Give {give2} for {receive2}")

        # P1 evaluates
        accept = agent_p1.evaluate_proposal((give2, receive2))
        print(f"  P1 response: {'ACCEPT' if accept else 'REJECT'}")

        if accept and give2 != ["Pass"]:
            # Apply trade
            game.apply_trade('p2', 'p1', give2, receive2)
            print(f"  Trade completed!")
            break
        elif give2 == ["Pass"]:
            print(f"  P2 passed, negotiation ends")
            break

        # Show belief evolution
        display_belief_changes(agent_p1, round_num)
        display_belief_changes(agent_p2, round_num)

    # Final scores
    print(f"\n{'=' * 60}")
    print("FINAL RESULTS")
    print(f"{'=' * 60}")

    p1_score, _, _ = game.get_max_score_and_path('p1')
    p2_score, _, _ = game.get_max_score_and_path('p2')

    print(f"P1 Final Score: {p1_score}")
    print(f"P2 Final Score: {p2_score}")

    # Final belief states
    display_belief_changes(agent_p1, 99)
    display_belief_changes(agent_p2, 99)


if __name__ == "__main__":
    run_game_with_belief_tracking()