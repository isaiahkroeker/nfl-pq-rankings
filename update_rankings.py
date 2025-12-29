import pandas as pd
import numpy as np
from datetime import datetime
import pytz

DATA_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"

def run_2025_rankings():
    df = pd.read_csv(DATA_URL)
    # Only use 2025 Regular Season games that have a score
    played = df[(df['season'] == 2025) & (df['game_type'] == 'REG')].dropna(subset=['home_score']).copy()
    
    if played.empty:
        return pd.DataFrame(columns=['Team', 'PQ_Score', 'Record'])

    max_week = played['week'].max()
    teams = pd.unique(played[['home_team', 'away_team']].values.ravel())
    
    # Calculate Win % for Strength of Schedule (SOS)
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
            is_home = (g['home_team'] == team)
            diff = (g['home_score'] - g['away_score']) if is_home else (g['away_score'] - g['home_score'])
            
            # SOS Factor
            opponent = g['away_team'] if is_home else g['home_team']
            opp_strength = records.get(opponent, 0.5) + 0.1
            
            # Recency Weight: Every week earlier than 'now' reduces game value by 5%
            weeks_ago = max_week - g['week']
            recency_weight = 0.95 ** weeks_ago 
            
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

# Generate the website
rankings_df = run_2025_rankings()
est = pytz.timezone('US/Eastern')
update_time = datetime.now(est).strftime('%Y-%m-%d %I:%M %p EST')

html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NFL PQ Rankings</title>
    <style>
        body {{ font-family: 'Arial', sans-serif; background-color: #f0f2f5; padding: 40px; }}
        .card {{ background: white; max-width: 900px; margin: auto; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
        h1 {{ color: #013369; margin-top: 0; }}
        .update-tag {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
        .method-box {{ background: #eef2f7; padding: 15px; border-radius: 8px; margin-bottom: 25px; border-left: 5px solid #013369; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #013369; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f9f9f9; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>📊 2025 NFL PQ Rankings</h1>
        <div class="update-tag">Last Updated: {update_time}</div>
        
        <div class="method-box">
            <strong>The Logic:</strong> I weight every team's point differential by their opponent's strength. 
            <em>Recent games (like this week) are weighted heavier than early-season games to capture momentum.</em>
        </div>

        {rankings_df.to_html(classes='table')}
    </div>
</body>
</html>
"""

with open("index.html", "w") as f:
    f.write(html_content)
