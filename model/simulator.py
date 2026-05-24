"""
Monte Carlo Tournament Simulator for FIFA World Cup 2026.

Simulates the full 48-team, 12-group tournament structure 50,000 times
to produce championship probabilities for each team.
"""

import random
from collections import defaultdict
from model.predictor import simulate_match, match_probabilities, knockout_win_prob

# ── 2026 FIFA World Cup — Official Group Draw ─────────────────────────────────
WC_2026_GROUPS = {
    "A": ["Mexico",       "South Africa",           "South Korea",          "Czechia"],
    "B": ["Canada",       "Bosnia and Herzegovina", "Qatar",                "Switzerland"],
    "C": ["Brazil",       "Morocco",                "Haiti",                "Scotland"],
    "D": ["United States","Paraguay",               "Australia",            "Türkiye"],
    "E": ["Germany",      "Curaçao",                "Ivory Coast",          "Ecuador"],
    "F": ["Netherlands",  "Japan",                  "Sweden",               "Tunisia"],
    "G": ["Belgium",      "Egypt",                  "Iran",                 "New Zealand"],
    "H": ["Spain",        "Cape Verde",             "Saudi Arabia",         "Uruguay"],
    "I": ["France",       "Senegal",                "Iraq",                 "Norway"],
    "J": ["Argentina",    "Algeria",                "Austria",              "Jordan"],
    "K": ["Portugal",     "DR Congo",               "Uzbekistan",           "Colombia"],
    "L": ["England",      "Croatia",                "Ghana",                "Panama"],
}

# All 48 qualified teams in order
ALL_TEAMS = [team for group in WC_2026_GROUPS.values() for team in group]

# ── Group Stage Simulation ────────────────────────────────────────────────────

def simulate_group(teams: list, ratings: dict) -> list:
    """
    Simulate a group stage (round-robin) and return teams ranked by points.
    
    Returns list of teams sorted by: points → GD → goals scored → ELO (tiebreaker)
    """
    points = {t: 0 for t in teams}
    gd     = {t: 0 for t in teams}
    gf     = {t: 0 for t in teams}
    
    # Round-robin: every pair plays once
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            a, b = teams[i], teams[j]
            elo_a = ratings.get(a, 1500)
            elo_b = ratings.get(b, 1500)
            
            result = simulate_match(elo_a, elo_b, knockout=False)
            
            # Simulate approximate scoreline for goal difference tracking
            p_win, p_draw, p_loss = match_probabilities(elo_a, elo_b)
            avg_goals_a = 1.2 + 0.3 * (elo_a - elo_b) / 200
            avg_goals_b = 1.2 - 0.3 * (elo_a - elo_b) / 200
            avg_goals_a = max(0.3, min(4.0, avg_goals_a))
            avg_goals_b = max(0.3, min(4.0, avg_goals_b))
            
            import math
            def poisson_goal():
                pass
            
            g_a = _poisson_sample(avg_goals_a)
            g_b = _poisson_sample(avg_goals_b)
            
            # Adjust score consistency with outcome
            if result == 'A' and g_a <= g_b:
                g_a = g_b + 1
            elif result == 'B' and g_b <= g_a:
                g_b = g_a + 1
            elif result == 'D':
                g_b = g_a  # same score for draw
            
            gf[a] += g_a;  gf[b] += g_b
            gd[a] += g_a - g_b;  gd[b] += g_b - g_a
            
            if result == 'A':
                points[a] += 3
            elif result == 'B':
                points[b] += 3
            else:
                points[a] += 1;  points[b] += 1
    
    # Sort: points → GD → GF → ELO
    ranked = sorted(
        teams,
        key=lambda t: (points[t], gd[t], gf[t], ratings.get(t, 1500)),
        reverse=True,
    )
    return ranked


def _poisson_sample(lam: float) -> int:
    """Sample from Poisson distribution (Knuth algorithm)."""
    import math
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


# ── Knockout Stage Simulation ─────────────────────────────────────────────────

def simulate_knockout_match(team_a: str, team_b: str, ratings: dict) -> str:
    """Simulate a single knockout match, returning the winner."""
    elo_a = ratings.get(team_a, 1500)
    elo_b = ratings.get(team_b, 1500)
    result = simulate_match(elo_a, elo_b, knockout=True)
    return team_a if result == 'A' else team_b


def simulate_tournament(ratings: dict) -> dict:
    """
    Simulate one complete 2026 FIFA World Cup tournament.
    
    2026 Format:
    - 12 groups of 4 teams, top 2 + 8 best 3rd-place teams advance (32 total)
    - Round of 32 → R16 → QF → SF → Final
    
    Returns dict: team → {stage reached}
    """
    results = {team: {"group": False, "r32": False, "r16": False,
                      "qf": False, "sf": False, "final": False, "winner": False}
               for team in ALL_TEAMS}
    
    # ── Group Stage ──────────────────────────────────────────────────────────
    group_winners   = []  # 1st in each group
    group_runners   = []  # 2nd in each group
    group_thirds    = []  # 3rd in each group (8 best advance)
    
    group_standings = {}
    for group_name, teams in WC_2026_GROUPS.items():
        ranked = simulate_group(teams, ratings)
        group_standings[group_name] = ranked
        group_winners.append(ranked[0])
        group_runners.append(ranked[1])
        group_thirds.append(ranked[2])
        # 4th place goes home
        for t in ranked:
            results[t]["group"] = True
    
    # Best 8 third-place teams advance (ranked by ELO as proxy for points)
    best_thirds = sorted(group_thirds,
                         key=lambda t: ratings.get(t, 1500), reverse=True)[:8]
    
    # ── Round of 32 (R32): 32 teams ─────────────────────────────────────────
    # Pairing: Group winner vs best 3rd / runner-up vs runner-up
    # Simplified bracket: pair group winners vs runners/thirds
    r32_pool = group_winners + group_runners + best_thirds
    random.shuffle(r32_pool)  # simplified bracket (real bracket TBD by FIFA)
    
    # Official 2026 bracket structure (simplified as sequential pairs)
    r32_winners = []
    for i in range(0, len(r32_pool), 2):
        if i + 1 < len(r32_pool):
            w = simulate_knockout_match(r32_pool[i], r32_pool[i+1], ratings)
            r32_winners.append(w)
            results[w]["r32"] = True
    
    # ── Round of 16 ─────────────────────────────────────────────────────────
    r16_winners = []
    for i in range(0, len(r32_winners), 2):
        if i + 1 < len(r32_winners):
            w = simulate_knockout_match(r32_winners[i], r32_winners[i+1], ratings)
            r16_winners.append(w)
            results[w]["r16"] = True
    
    # ── Quarter-Finals ───────────────────────────────────────────────────────
    qf_winners = []
    for i in range(0, len(r16_winners), 2):
        if i + 1 < len(r16_winners):
            w = simulate_knockout_match(r16_winners[i], r16_winners[i+1], ratings)
            qf_winners.append(w)
            results[w]["qf"] = True
    
    # ── Semi-Finals ──────────────────────────────────────────────────────────
    sf_winners = []
    sf_losers  = []
    for i in range(0, len(qf_winners), 2):
        if i + 1 < len(qf_winners):
            a, b = qf_winners[i], qf_winners[i+1]
            w = simulate_knockout_match(a, b, ratings)
            loser = b if w == a else a
            sf_winners.append(w)
            sf_losers.append(loser)
            results[w]["sf"] = True
            results[loser]["sf"] = True  # Both SF participants reached semi-finals
    
    # ── Final ────────────────────────────────────────────────────────────────
    if len(sf_winners) >= 2:
        finalist_a, finalist_b = sf_winners[0], sf_winners[1]
        results[finalist_a]["final"] = True
        results[finalist_b]["final"] = True
        
        champion = simulate_knockout_match(finalist_a, finalist_b, ratings)
        results[champion]["winner"] = True
    
    return results


# ── Monte Carlo Runner ────────────────────────────────────────────────────────

def run_monte_carlo(ratings: dict, n_sims: int = 50_000) -> dict:
    """
    Run n_sims tournament simulations and aggregate probabilities.
    
    Returns:
        dict: team → {
            "champion_pct", "finalist_pct", "semi_pct",
            "qf_pct", "r16_pct", "r32_pct", "elo", "group"
        }
    """
    counts = {
        team: defaultdict(int) for team in ALL_TEAMS
    }
    
    print(f"Running {n_sims:,} Monte Carlo simulations...")
    for sim in range(n_sims):
        if sim % 10_000 == 0 and sim > 0:
            print(f"  {sim:,} / {n_sims:,} complete...")
        
        result = simulate_tournament(ratings)
        for team, stages in result.items():
            if stages["winner"]:  counts[team]["winner"]   += 1
            if stages["final"]:   counts[team]["final"]    += 1
            if stages["sf"]:      counts[team]["sf"]       += 1
            if stages["qf"]:      counts[team]["qf"]       += 1
            if stages["r16"]:     counts[team]["r16"]      += 1
            if stages["r32"]:     counts[team]["r32"]      += 1
            if stages["group"]:   counts[team]["group"]    += 1
    
    # Convert counts to percentages
    output = {}
    for team in ALL_TEAMS:
        c = counts[team]
        # Find which group this team is in
        group_label = next(
            g for g, teams in WC_2026_GROUPS.items() if team in teams
        )
        output[team] = {
            "team":           team,
            "group":          group_label,
            "elo":            round(ratings.get(team, 1500), 1),
            "champion_pct":   round(c["winner"] / n_sims * 100, 2),
            "finalist_pct":   round(c["final"]  / n_sims * 100, 2),
            "semi_pct":       round(c["sf"]     / n_sims * 100, 2),
            "qf_pct":         round(c["qf"]     / n_sims * 100, 2),
            "r16_pct":        round(c["r16"]    / n_sims * 100, 2),
            "r32_pct":        round(c["r32"]    / n_sims * 100, 2),
        }
    
    return output


if __name__ == "__main__":
    from model.elo import get_final_ratings
    ratings = get_final_ratings()
    results = run_monte_carlo(ratings, n_sims=10_000)
    
    sorted_teams = sorted(results.values(),
                          key=lambda x: x["champion_pct"], reverse=True)
    print(f"\n{'Team':<25} {'Grp':>4} {'ELO':>7} {'Champ%':>8} {'Final%':>8} {'Semi%':>7}")
    print("-" * 65)
    for r in sorted_teams[:20]:
        print(f"{r['team']:<25} {r['group']:>4} {r['elo']:>7.0f} "
              f"{r['champion_pct']:>8.2f} {r['finalist_pct']:>8.2f} "
              f"{r['semi_pct']:>7.2f}")
