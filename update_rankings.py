import pandas as pd

# Link to the official 2025 Live Data
DATA_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"

def run_2025_rankings():
    df = pd.read_csv(DATA_URL)
    played = df[(df['season'] == 2025) & (df['game_type'] == 'REG')].dropna(subset=['home_score'])
    
    if played.empty:
        return pd.DataFrame(columns=['Team', 'PQ_Score', 'Record'])

    teams = pd.unique(played[['home_team', 'away_team']].values.ravel())
    records = {t: (len(played[((played['home_team'] == t) & (played['home_score'] > played['away_score'])) | 
                               ((played['away_team'] == t) & (played['away_score'] > played['home_score']))]) / 
                  len(played[(played['home_team'] == t) | (played['away_team'] == t)])) for t in teams}

    pq_results = []
    for team in teams:
        team_games = played[(played['home_team'] == team) | (played['away_team'] == team)]
        weighted_pd = sum(((g['home_score'] - g['away_score'] if g['home_team'] == team else g['away_score'] - g['home_score']) 
                           * (records.get(g['away_team'] if g['home_team'] == team else g['home_team'], 0.5) + 0.1)) 
                          for _, g in team_games.iterrows())
        
        pq_results.append({'Team': team, 'PQ_Score': round(weighted_pd, 2), 
                        'Record': f"{int(records[team]*len(team_games))}-{len(team_games)-int(records[team]*len(team_games))}"})

    final_df = pd.DataFrame(pq_results).sort_values(by='PQ_Score', ascending=False).reset_index(drop=True)
    final_df.index += 1
    return final_df

# Generate the website
final_rankings = run_2025_rankings()
update_time = pd.Timestamp.now().strftime('%B %d, %Y at %I:%M %p')

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>NFL PQ Rankings</title>
    <style>
        body {{ font-family: sans-serif; background: #f4f7f6; padding: 20px; }}
        .card {{ background: white; max-width: 800px; margin: auto; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        h1 {{ color: #013369; text-align: center; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #013369; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #eee; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>🏈 2025 PQ Power Rankings</h1>
        <p style="text-align:center;">Last Updated: {update_time}</p>
        {final_rankings.to_html()}
    </div>
</body>
</html>
"""

with open("index.html", "w") as f:
    f.write(html_content)
