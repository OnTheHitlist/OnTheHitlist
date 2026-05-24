"""
ELO Rating Engine for FIFA World Cup Teams.

Computes dynamic ELO ratings from historical World Cup match data.
"""

import math
from collections import defaultdict
from data.historical_matches import get_matches, WC_WINNERS

# ── Constants ────────────────────────────────────────────────────────────────
BASE_ELO = 1500

# K-factors by tournament stage (higher = more impactful on ratings)
K_FACTORS = {
    "group": 30,
    "r32":   40,
    "r16":   45,
    "qf":    50,
    "sf":    55,
    "3rd":   40,
    "final": 60,
}

# Recency multipliers: post-2002 = 1.5x, post-2014 = 2x
def recency_weight(year: int) -> float:
    if year >= 2014:
        return 2.0
    elif year >= 2002:
        return 1.5
    elif year >= 1986:
        return 1.2
    return 1.0

# ── ELO Core ─────────────────────────────────────────────────────────────────

def expected_score(rating_a: float, rating_b: float) -> float:
    """Expected score for team A against team B (standard ELO formula)."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400))

def get_outcome(score1: int, score2: int):
    """Return (result1, result2) where result is 1=win, 0.5=draw, 0=loss."""
    if score1 > score2:
        return 1.0, 0.0
    elif score1 < score2:
        return 0.0, 1.0
    else:
        return 0.5, 0.5

def update_elo(rating_a, rating_b, score_a, score_b, stage, year):
    """Compute new ELO ratings after a match."""
    k = K_FACTORS.get(stage, 30) * recency_weight(year)
    exp_a = expected_score(rating_a, rating_b)
    exp_b = 1.0 - exp_a
    actual_a, actual_b = get_outcome(score_a, score_b)
    
    # Goal difference bonus (logarithmic dampening)
    gd = abs(score_a - score_b)
    gd_bonus = math.log(gd + 1) * 0.15 + 1.0
    
    new_a = rating_a + k * gd_bonus * (actual_a - exp_a)
    new_b = rating_b + k * gd_bonus * (actual_b - exp_b)
    return new_a, new_b

# ── Main ELO Computation ──────────────────────────────────────────────────────

def compute_elo_ratings(extra_boosts: dict = None) -> dict:
    """
    Compute ELO ratings for all teams from historical WC data.
    
    Args:
        extra_boosts: Optional {team: delta} to apply to current-era
                      ratings (e.g., from recent qualifying performance)
    
    Returns:
        dict mapping team name → current ELO rating
    """
    ratings = defaultdict(lambda: BASE_ELO)
    matches = get_matches()
    
    for year, stage, team1, team2, score1, score2 in matches:
        r1 = ratings[team1]
        r2 = ratings[team2]
        new_r1, new_r2 = update_elo(r1, r2, score1, score2, stage, year)
        ratings[team1] = new_r1
        ratings[team2] = new_r2
    
    # Apply any extra boosts (e.g., from 2022–2025 qualifying results)
    if extra_boosts:
        for team, delta in extra_boosts.items():
            if team in ratings:
                ratings[team] += delta
    
    return dict(ratings)


# ── Adjustments for 2026 qualified teams not in WC history ───────────────────
# Teams qualifying for 2026 that have limited/no WC history get base + boost
DEBUT_TEAM_RATINGS = {
    "Haiti":      1350,
    "Curaçao":    1320,
    "Jordan":     1330,
    "Uzbekistan": 1340,
    "Iraq":       1360,
    "Cape Verde": 1370,
    "Panama":     1380,
}

# Recent form adjustments (2022–2025 qualifying performance, relative boosts)
RECENT_FORM_BOOSTS = {
    "Argentina":  80,   # World Cup 2022 winners
    "France":     50,   # 2022 WC finalists
    "Morocco":    60,   # 2022 historic semi-final run
    "England":    40,   # Consistent recent form
    "Spain":      45,   # Nations League winners
    "Brazil":     20,   # Below expectations in 2022
    "Germany":    30,   # Rebuilding post-2022
    "Portugal":   35,   # Strong qualifying
    "Netherlands":30,   # QF 2022
    "Belgium":    -10,  # Golden generation aging
    "Colombia":   40,   # Strong CONMEBOL qualifying
    "Uruguay":    25,   # Consistent
    "Senegal":    35,   # AFCON competitive
    "Japan":      45,   # Shocking 2022 upsets
    "South Korea":20,
    "Australia":  15,
    "Ecuador":    20,
    "Croatia":    20,
    "Norway":     25,   # Haaland-era strength
    "Sweden":     10,
    "Denmark":    15,
    "Switzerland":20,
    "Austria":    25,
    "Scotland":   15,
    "Czechia":    10,
    "Turkey":     20,
    "Bosnia and Herzegovina": 10,
    "Serbia":     15,
    "Algeria":    20,
    "Tunisia":    10,
    "Egypt":      15,
    "Ghana":      5,
    "DR Congo":   15,
    "Saudi Arabia": 10,
    "Iran":       10,
    "South Africa": 15,  # 2026 hosts-adjacent
}

def get_final_ratings() -> dict:
    """
    Get final ELO ratings for all 2026 WC teams, with recent form applied.
    """
    ratings = compute_elo_ratings(extra_boosts=RECENT_FORM_BOOSTS)
    
    # Inject debut/low-history teams with sensible ratings
    for team, rating in DEBUT_TEAM_RATINGS.items():
        if team not in ratings or ratings[team] < rating:
            ratings[team] = rating
    
    return ratings

def print_top_teams(ratings: dict, n: int = 20):
    """Print top N teams by ELO rating."""
    sorted_teams = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
    print(f"\n{'Rank':<5} {'Team':<30} {'ELO':>7}")
    print("-" * 45)
    for i, (team, elo) in enumerate(sorted_teams[:n], 1):
        print(f"{i:<5} {team:<30} {elo:>7.1f}")


if __name__ == "__main__":
    ratings = get_final_ratings()
    print_top_teams(ratings, n=48)
