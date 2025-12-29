import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# Stable Data Sources
GAMES_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
TEAMS_URL = "https://raw.githubusercontent.com/nflverse/nflfastR-data/master/teams_colors_logos.csv"

def get_nfl_data():
    games = pd.read_csv(GAMES_URL)
    teams_meta = pd.read_csv(TEAMS_URL)
    
    # Smart Detection for columns
    mapping = {'team': ['team_abbr', 'team'], 'logo': ['team_logo_espn', 'logo'], 'color': ['team_color', 'color']}
    final_mapping = {}
    for target, options in mapping.items():
        for opt in options:
            if opt in teams_meta.columns:
                final_mapping[opt] = target
                break
    teams_meta = teams_meta.rename(columns=final_mapping)

    # 2025 Logic
    played = games[(games['season'] == 2025) & (games['game_type'] == 'REG')].dropna(subset=['home_score']).copy()
    if played.empty: return pd.DataFrame()

    team_list = pd.unique(played[['home_team', 'away_team']].values.ravel())
    max_week = played['week'].max()
    
    records = {}
    for t in team_list:
        tg = played[(played['home_team'] == t) | (played['away_team'] == t)]
        wins = len(tg[((tg['home_team'] == t) & (tg['home_score'] > tg['away_score'])) | ((tg['away_team'] == t) & (tg['away_score'] > tg['home_score']))])
        records[t] = {'w': wins, 'l': len(tg)-wins, 'pct': wins/len(tg)}

    dashboard = []
    for t in team_list:
        tg = played[(played['home_team'] == t) | (played['away_team'] == t)]
        pq = sum((((g['home_score'] - g['away_score']) if g['home_team'] == t else (g['away_score'] - g['home_score'])) * (records[g['away_team'] if g['home_team'] == t else g['home_team']]['pct'] + 0.1) * (0.95 ** (max_week - g['week']))) for _, g in tg.iterrows())
        
        status, s_color = ("CLINCHED", "#28a745") if records[t]['w'] >= 10 else (("ELIMINATED", "#dc3545") if records[t]['w'] <= 6 else ("IN THE HUNT", "#007bff"))
        dashboard.append({'team': t, 'pq': round(pq, 2), 'record': f"{records[t]['w']}-{records[t]['l']}", 'status': status, 's_color': s_color})

    return pd.DataFrame(dashboard).sort_values('pq', ascending=False).merge(teams_meta[['team', 'logo', 'color']], on='team', how='left')

data = get_nfl_data()
time_str = datetime.now(pytz.timezone('US/Eastern')).strftime('%I:%M %p EST')

html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL PQ Dashboard</title>
    <style>
        :root {{ --bg: #0f172a; --card: #1e293b; --text: #f8fafc; }}
        body {{ background: var(--bg); color: var(--text); font-family: sans-serif; padding: 15px; margin: 0; }}
        .card {{ background: var(--card); border-radius: 12px; padding: 15px; margin-bottom: 10px; display: flex; align-items: center; border-left: 6px solid; }}
        .logo {{ width: 40px; height: 40px; margin-right: 15px; }}
        .pq {{ font-weight: bold; color: #38bdf8; font-size: 1.2em; }}
    </style>
</head>
<body>
    <div style="text-align: center; padding: 20px;"><h1>🏈 NFL PQ LIVE</h1><p>Updated: {time_str}</p></div>
    {"".join([f'''
    <div class="card" style="border-left-color: {r['color']}">
        <div style="width: 25px; opacity: 0.4;">{i+1}</div>
        <img src="{r['logo']}" class="logo">
        <div style="flex-grow: 1;"><b>{r['team']}</b> ({r['record']})<br><small style="color:{r['s_color']}">{r['status']}</small></div>
        <div style="text-align: right;"><small>PQ</small><br><span class="pq">{r['pq']}</span></div>
    </div>
    ''' for i, r in data.iterrows()])}
</body>
</html>
"""
with open("index.html", "w") as f: f.write(html)
