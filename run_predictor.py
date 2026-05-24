"""
FIFA World Cup 2026 Winner Predictor — Main Pipeline.

Run this script to compute ELO ratings, run Monte Carlo simulation,
and generate the predictions.json output for the web dashboard.
"""

import json
import os
import sys
import time

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model.elo       import get_final_ratings, print_top_teams
from model.predictor import head_to_head_analysis
from model.simulator import run_monte_carlo, WC_2026_GROUPS, ALL_TEAMS


def main(n_sims: int = 50_000):
    print("=" * 65)
    print("  FIFA WORLD CUP 2026 WINNER PREDICTOR")
    print("  ELO Ratings + Monte Carlo Simulation")
    print("=" * 65)

    # ── Step 1: Compute ELO Ratings ──────────────────────────────────────────
    print("\n[1/3] Computing ELO ratings from historical data (1930–2022)...")
    t0 = time.time()
    ratings = get_final_ratings()
    print(f"      Done in {time.time()-t0:.2f}s — {len(ratings)} teams rated")
    print_top_teams(ratings, n=15)

    # ── Step 2: Run Monte Carlo Simulation ───────────────────────────────────
    print(f"\n[2/3] Running {n_sims:,} Monte Carlo tournament simulations...")
    t0 = time.time()
    predictions = run_monte_carlo(ratings, n_sims=n_sims)
    print(f"      Done in {time.time()-t0:.1f}s")

    # ── Step 3: Generate Head-to-Head Matrix (top 10 teams) ─────────────────
    print("\n[3/3] Computing head-to-head matrix for top teams...")
    sorted_teams = sorted(predictions.values(),
                          key=lambda x: x["champion_pct"], reverse=True)
    top10 = [t["team"] for t in sorted_teams[:10]]
    
    h2h_matrix = {}
    for i, team_a in enumerate(top10):
        h2h_matrix[team_a] = {}
        for j, team_b in enumerate(top10):
            if team_a != team_b:
                result = head_to_head_analysis(team_a, team_b, ratings)
                h2h_matrix[team_a][team_b] = {
                    "win_pct":  result["p_win_a"],
                    "draw_pct": result["p_draw"],
                    "loss_pct": result["p_win_b"],
                }
    
    # ── Assemble output JSON ──────────────────────────────────────────────────
    output = {
        "meta": {
            "generated_at":   time.strftime("%Y-%m-%dT%H:%M:%S"),
            "n_simulations":  n_sims,
            "tournament":     "FIFA World Cup 2026",
            "num_teams":      len(ALL_TEAMS),
            "model":          "ELO + Monte Carlo (Dixon-Coles draw correction)",
        },
        "groups": WC_2026_GROUPS,
        "ratings": {
            team: round(elo, 1)
            for team, elo in sorted(ratings.items(), key=lambda x: x[1], reverse=True)
            if team in ALL_TEAMS
        },
        "predictions": {
            team: data
            for team, data in sorted(
                predictions.items(),
                key=lambda x: x[1]["champion_pct"],
                reverse=True
            )
        },
        "head_to_head": h2h_matrix,
        "elo_history": _build_elo_history(),
    }
    
    # ── Save to file ──────────────────────────────────────────────────────────
    os.makedirs("output", exist_ok=True)
    output_path = os.path.join(os.path.dirname(__file__), "output", "predictions.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Saved predictions to: {output_path}")
    
    # ── Print summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  TOP 15 CHAMPIONSHIP PREDICTIONS")
    print("=" * 65)
    print(f"{'Rank':<5} {'Team':<25} {'Grp':>4} {'ELO':>7} "
          f"{'Champ%':>8} {'Final%':>8} {'Semi%':>7}")
    print("-" * 65)
    for i, t in enumerate(sorted_teams[:15], 1):
        print(f"{i:<5} {t['team']:<25} {t['group']:>4} {t['elo']:>7.0f} "
              f"{t['champion_pct']:>8.2f} {t['finalist_pct']:>8.2f} "
              f"{t['semi_pct']:>7.2f}")
    
    print(f"\n  Probabilities sum to: "
          f"{sum(t['champion_pct'] for t in predictions.values()):.1f}%")
    print("\n>> Open web/index.html in your browser to view the dashboard!")
    
    return output


def _build_elo_history() -> dict:
    """Build ELO progression over tournament history for key teams."""
    from data.historical_matches import get_matches, TEAM_ALIASES
    from model.elo import BASE_ELO, K_FACTORS, recency_weight, update_elo
    from collections import defaultdict

    key_teams = [
        "Brazil", "Germany", "Argentina", "France", "Italy",
        "Spain", "England", "Netherlands", "Portugal", "Uruguay",
    ]
    
    ratings = defaultdict(lambda: BASE_ELO)
    history = {t: [] for t in key_teams}
    matches = get_matches()
    
    years_seen = set()
    year_ratings = {}
    
    for year, stage, team1, team2, score1, score2 in matches:
        r1 = ratings[team1]
        r2 = ratings[team2]
        new_r1, new_r2 = update_elo(r1, r2, score1, score2, stage, year)
        ratings[team1] = new_r1
        ratings[team2] = new_r2
        
        if year not in years_seen:
            years_seen.add(year)
            year_ratings[year] = {}
        year_ratings[year][team1] = round(new_r1, 1)
        year_ratings[year][team2] = round(new_r2, 1)
    
    # Build per-team timeline
    all_years = sorted(years_seen)
    result = {}
    running = {t: BASE_ELO for t in key_teams}
    
    for year in all_years:
        yr_data = year_ratings.get(year, {})
        for team in key_teams:
            if team in yr_data:
                running[team] = yr_data[team]
    
    for year in all_years:
        yr_data = year_ratings.get(year, {})
        for team in key_teams:
            if team not in result:
                result[team] = []
            val = yr_data.get(team, running.get(team, BASE_ELO))
            result[team].append({"year": year, "elo": val})
    
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FIFA WC 2026 Winner Predictor")
    parser.add_argument("--sims", type=int, default=50_000,
                        help="Number of Monte Carlo simulations (default: 50000)")
    args = parser.parse_args()
    main(n_sims=args.sims)