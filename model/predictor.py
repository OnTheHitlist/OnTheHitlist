"""
Match Outcome Predictor using ELO ratings.

Converts ELO rating differences into win/draw/loss probabilities
using a Dixon-Coles inspired draw adjustment.
"""

import math
from model.elo import expected_score

# ── Draw probability model ───────────────────────────────────────────────────
# Football is a low-scoring sport — draw probability is non-trivial.
# We model draw probability as a Gaussian-like function of ELO difference:
# higher ELO gap → less likely draw, closer ratings → more likely draw.

BASE_DRAW_PROB = 0.24      # Average WC draw rate ~24%
DRAW_DECAY     = 0.0012    # How fast draw prob falls off with ELO gap


def draw_probability(elo_diff: float) -> float:
    """
    Estimate draw probability based on absolute ELO difference.
    Uses a Gaussian decay: larger mismatches → lower draw chance.
    """
    return BASE_DRAW_PROB * math.exp(-DRAW_DECAY * elo_diff ** 2)


def match_probabilities(elo_a: float, elo_b: float) -> tuple:
    """
    Compute (P_win_A, P_draw, P_win_B) from ELO ratings.
    
    Args:
        elo_a: ELO rating of team A
        elo_b: ELO rating of team B
    
    Returns:
        (p_win, p_draw, p_loss) for team A
    """
    elo_diff = abs(elo_a - elo_b)
    p_draw = draw_probability(elo_diff)
    
    # Base win prob from ELO
    raw_win_a = expected_score(elo_a, elo_b)
    
    # Redistribute draw probability symmetrically
    p_win_a = raw_win_a * (1 - p_draw)
    p_win_b = (1 - raw_win_a) * (1 - p_draw)
    
    # Normalize to ensure they sum to 1
    total = p_win_a + p_draw + p_win_b
    return p_win_a / total, p_draw / total, p_win_b / total


def knockout_win_prob(elo_a: float, elo_b: float) -> float:
    """
    Win probability for a knockout match (no draws allowed).
    Draws resolved by penalty shootout; we model 50/50 on penalties
    but weight it by extra time likelihood.
    """
    p_win, p_draw, p_loss = match_probabilities(elo_a, elo_b)
    # Penalty shootout: ~50/50 but slight edge to favorite
    elo_diff = elo_a - elo_b
    penalty_edge = 0.5 + 0.001 * elo_diff   # tiny edge, capped
    penalty_edge = max(0.35, min(0.65, penalty_edge))
    
    # P(team A wins) = P(win in 90min) + P(draw) * P(win pens)
    return p_win + p_draw * penalty_edge


def simulate_match(elo_a: float, elo_b: float, knockout: bool = False):
    """
    Simulate a single match result.
    
    Returns:
        'A' if team A wins, 'B' if team B wins, 'D' if draw (group stage)
    """
    import random
    
    if knockout:
        p_a_wins = knockout_win_prob(elo_a, elo_b)
        return 'A' if random.random() < p_a_wins else 'B'
    else:
        p_win, p_draw, p_loss = match_probabilities(elo_a, elo_b)
        r = random.random()
        if r < p_win:
            return 'A'
        elif r < p_win + p_draw:
            return 'D'
        else:
            return 'B'


def head_to_head_analysis(team_a: str, team_b: str, ratings: dict) -> dict:
    """
    Full head-to-head analysis between two teams.
    
    Returns a dict with win/draw/loss probabilities and interpretations.
    """
    elo_a = ratings.get(team_a, 1500)
    elo_b = ratings.get(team_b, 1500)
    
    p_win, p_draw, p_loss = match_probabilities(elo_a, elo_b)
    ko_win = knockout_win_prob(elo_a, elo_b)
    
    return {
        "team_a": team_a,
        "team_b": team_b,
        "elo_a": round(elo_a, 1),
        "elo_b": round(elo_b, 1),
        "elo_diff": round(elo_a - elo_b, 1),
        "p_win_a": round(p_win * 100, 1),
        "p_draw": round(p_draw * 100, 1),
        "p_win_b": round(p_loss * 100, 1),
        "ko_win_a": round(ko_win * 100, 1),
        "ko_win_b": round((1 - ko_win) * 100, 1),
        "favorite": team_a if elo_a > elo_b else team_b,
    }


if __name__ == "__main__":
    from model.elo import get_final_ratings
    ratings = get_final_ratings()
    
    matchups = [
        ("Brazil", "Argentina"),
        ("France", "England"),
        ("Germany", "Spain"),
        ("Morocco", "Portugal"),
    ]
    
    print(f"\n{'Matchup':<35} {'Win %':>7} {'Draw %':>7} {'Loss %':>7}")
    print("-" * 60)
    for a, b in matchups:
        result = head_to_head_analysis(a, b, ratings)
        print(f"{a} vs {b:<20} {result['p_win_a']:>7.1f} {result['p_draw']:>7.1f} {result['p_win_b']:>7.1f}")
