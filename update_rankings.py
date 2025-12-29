import pandas as pd
import numpy as np
from datetime import datetime
import pytz

DATA_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"

def run_2025_rankings():
    df = pd.read_csv(DATA_URL)
    # Filter for played regular season games
    played = df[(df['season'] == 2025) & (df['game_type'] == 'REG')].dropna(subset=['home_score']).copy()
    
    if played.empty:
        return pd.DataFrame(columns=['Team', 'PQ_Score', 'Record'])

    max_week = played['week'].max()
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
            is_home = (g['home_team'] == team)
            diff = (g['home_score'] - g['away_score']) if is_home else (g['away_score'] - g['home_score'])
            opponent = g['away_team'] if is_home else g['home_team']
            opp_strength = records.get(opponent, 0.5) + 0.1
            
            # Recency Weighting
            weeks_ago = max_week - g['week']
            recency_weight = 0.95 ** weeks_ago 
            weighted_pd += (diff * opp_strength * recency_weight)
        
        wins = int(records[team] * len(team_games))
        losses = len(team_games) - wins
        pq_results.append({'Team': team, 'PQ_Score': round(weighted_pd, 2), 'Record': f"{wins}-{losses}"})

    return pd.DataFrame(pq_results).sort_values(by='PQ_Score', ascending=False).reset_index(drop=True)

# --- THE SAVING BLOCK (MUST BE AT THE BOTTOM) ---
final_rankings = run_2025_rankings()
est = pytz.timezone('US/Eastern')
update_time = datetime.now(est).strftime('%Y-%m-%d %I:%M %p EST')

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>NFL PQ Rankings</title>
    <style>
        body {{ font-family: sans-serif; background: #f4f4f9; padding: 20px; }}
        .container {{ max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; border-bottom: 1px solid #ddd; text-align: left; }}
        th {{ background: #013369; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏈 2025 NFL PQ Rankings</h1>
        <p><em>Last Updated: {update_time}</em></p>
        <p>I weight recent games more heavily to reflect current team momentum.</p>
        {final_rankings.to_html(index=True, classes='table')}
    </div>
</body>
</html>
"""

with open("index.html", "w") as f:
    f.write(html_content)
