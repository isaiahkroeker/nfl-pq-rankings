import pandas as pd
import numpy as np

DATA_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"

def run_2025_rankings():
    df = pd.read_csv(DATA_URL)
    # Filter for played regular season games
    played = df[(df['season'] == 2025) & (df['game_type'] == 'REG')].dropna(subset=['home_score']).copy()
    
    if played.empty:
        return pd.DataFrame(columns=['Team', 'PQ_Score', 'Record'])

    # Determine the most recent week played to calculate "distance" in time
    max_week = played['week'].max()
    
    # Calculate Team Records
    teams = pd.unique(played[['home_team', 'away_team']].values.ravel())
    records = {}
    for t in teams:
        team_games = played[(played['home_team'] == t) | (played['away_team'] == t)]
        wins = len(team_games[((team_games['home_team'] == t) & (team_games['home_score'] > team_games['away_score'])) | 
                             ((team_games['away_team'] == t) & (team_games['away_score'] > team_games['home_score']))])
        records[t] = wins / len(team_games)

    pq_results = []
    for team in teams:
        team_games = played[(played['home_team'] == team) | (played['away_team'] == team)]
        weighted_pd = 0
        
        for _, g in team_games.iterrows():
            # 1. Calculate basic point differential for this game
            is_home = (g['home_team'] == team)
            diff = (g['home_score'] - g['away_score']) if is_home else (g['away_score'] - g['home_score'])
            
            # 2. Strength of Opponent (Opponent's win %)
            opponent = g['away_team'] if is_home else g['home_team']
            opp_strength = records.get(opponent, 0.5) + 0.1
            
            # 3. RECENCY WEIGHTING (The new part!)
            # Games from the current week have a weight of 1.0. 
            # Older games lose ~5% value per week.
            weeks_ago = max_week - g['week']
            recency_weight = 0.95 ** weeks_ago 
            
            # Combine everything
            weighted_pd += (diff * opp_strength * recency_weight)
        
        wins = int(records[team] * len(team_games))
        losses = len(team_games) - wins
        pq_results.append({
            'Team': team, 
            'PQ_Score': round(weighted_pd, 2), 
            'Record': f"{wins}-{losses}"
        })

    final_df = pd.DataFrame(pq_results).sort_values(by='PQ_Score', ascending=False).reset_index(drop=True)
    final_df.index += 1
    return final_df

# ... (rest of your HTML generation code remains the same)
