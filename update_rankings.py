import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# Reliable NFL Data Sources
GAMES_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
TEAMS_URL = "https://raw.githubusercontent.com/nflverse/nflfastR-data/master/teams_colors_logos.csv"

def get_nfl_data():
    # 1. Load Data
    games = pd.read_csv(GAMES_URL)
    teams_meta = pd.read_csv(TEAMS_URL)
    
    # 2. Smart Column Detection (Prevents KeyError)
    mapping = {
        'team': ['team_abbr', 'team', 'team_id'],
        'logo': ['team_logo_espn', 'logo_url', 'logo'],
        'color': ['team_color', 'color', 'primary_color']
    }
    
    final_mapping = {}
    for target, options in mapping.items():
        for opt in options:
            if opt in teams_meta.columns:
                final_mapping[opt] = target
                break
                
    teams_meta = teams_meta.rename(columns=final_mapping)

    # 3. Calculate Rankings (2025 Week 17)
    played = games[(games['season'] == 2025) & (games['game_type'] == 'REG')].dropna(subset=['home_score']).copy()
    if played.empty: return pd.DataFrame()

    max_week = played['week'].max()
    team_list = pd.unique(played[['home_team', 'away_team']].values.ravel())
    
    records = {t: {'w': 0, 'l': 0, 'pct': 0} for t in team_list}
    for t in team_list:
        tg = played[(played['home_team'] == t) | (played['away_team'] == t)]
        wins = len(tg[((tg['home_team'] == t) & (tg['home_score'] > tg['away_score'])) | ((tg['away_team'] == t) & (tg['away_score'] > tg['home_score']))])
        records[t] = {'w': wins, 'l': len(tg)-wins, 'pct': wins/len(tg)}

    dashboard_data = []
    for t in team_list:
        tg = played[(played['home_team'] == t) | (played['away_team'] == t)]
        pq = sum((((g['home_score'] - g['away_score']) if g['home_team'] == t else (g['away_score'] - g['home_score'])) * (records[g['away_team'] if g['home_team'] == t else g['home_team']]['pct'] + 0.1) * (0.95 ** (max_week - g['week']))) for _, g in tg.iterrows())
        
        status, s_color = ("CLINCHED", "#28a745") if records[t]['w'] >= 10 else (("ELIMINATED", "#dc3545") if records[t]['w'] <= 6 else ("IN THE HUNT", "#007bff"))

        dashboard_data.append({
            'team': t, 'pq': round(pq, 2), 'record': f"{records[t]['w']}-{records[t]['l']}", 
            'status': status, 's_color': s_color
        })

    df_final = pd.DataFrame(dashboard_data).sort_values('pq', ascending=False)
    df_final = df_final.merge(teams_meta[['team', 'logo', 'color']], on='team', how='left')
    return df_final

# 4. Generate Site
data = get_nfl_data()
est = pytz.timezone('US/Eastern')
time_str = datetime.now(est).strftime('%I:%M %p EST')

html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL PQ Dashboard</title>
    <style>
        :root {{ --bg: #0f172a; --card: #1e293b; --text: #f8fafc; }}
        body {{ background: var(--bg); color: var(--text); font-family: sans-serif; margin: 0; padding: 15px; }}
        .header {{ text-align: center; padding: 20px; }}
        .card {{ background: var(--card); padding: 15px; border-radius: 12px; margin-bottom: 10px; display: flex; align-items: center; border-left: 5px solid; }}
        .logo {{ width: 45px; height: 45px; margin-right: 15px; }}
        .pq {{ font-weight: bold; color: #38bdf8; font-size: 1.2em; }}
        .badge {{ font-size: 0.7em; padding: 4px 8px; border-radius: 6px; margin-top: 5px; display: inline-block; }}
    </style>
</head>
<body>
    <div class="header"><h1>🏈 NFL PQ DASHBOARD</h1><p>Updated: {time_str}</p></div>
    <div id="list">
        {"".join([f'''
        <div class="card" style="border-left-color: {r['color']}">
            <div style="width: 25px; opacity: 0.5;">{i+1}</div>
            <img src="{r['logo']}" class="logo">
            <div style="flex-grow: 1;"><b>{r['team']}</b> ({r['record']})<br><div class="badge" style="background: {r['s_color']}">{r['status']}</div></div>
            <div style="text-align: right;"><small>PQ</small><br><span class="pq">{r['pq']}</span></div>
        </div>
        ''' for i, r in data.iterrows()])}
    </div>
</body>
</html>
"""
with open("index.html", "w") as f: f.write(html)
