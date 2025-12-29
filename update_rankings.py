import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import json

# Data Links
GAMES_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
TEAMS_URL = "https://raw.githubusercontent.com/nflverse/nflfastR-data/master/teams_colors_logos.csv"

def get_nfl_data():
    # 1. Load Data
    games = pd.read_csv(GAMES_URL)
    teams_meta = pd.read_csv(TEAMS_URL)
    
    # --- SMART COLUMN DETECTION ---
    # We look for the best match for each required piece of data
    potential_cols = {
        'team': ['team_abbr', 'team', 'team_id', 'abbr'],
        'logo': ['team_logo_espn', 'logo_url', 'logo', 'team_logo_wikipedia'],
        'color': ['team_color', 'color', 'primary_color'],
        'conf': ['team_conf', 'conf', 'conference']
    }
    
    final_mapping = {}
    for target, options in potential_cols.items():
        for opt in options:
            if opt in teams_meta.columns:
                final_mapping[opt] = target
                break # Stop at the first match found
                
    teams_meta = teams_meta.rename(columns=final_mapping)
    # Ensure we only keep the columns we found
    teams_meta = teams_meta[[col for col in ['team', 'logo', 'color', 'conf'] if col in teams_meta.columns]]
    # ------------------------------

    # 2. PQ Math Logic
    played = games[(games['season'] == 2025) & (games['game_type'] == 'REG')].dropna(subset=['home_score']).copy()
    if played.empty: return pd.DataFrame()

    max_week = played['week'].max()
    team_list = pd.unique(played[['home_team', 'away_team']].values.ravel())
    
    records = {}
    for t in team_list:
        tg = played[(played['home_team'] == t) | (played['away_team'] == t)]
        wins = len(tg[((tg['home_team'] == t) & (tg['home_score'] > tg['away_score'])) | 
                     ((tg['away_team'] == t) & (tg['away_score'] > tg['home_score']))])
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
    df_final = df_final.merge(teams_meta, on='team', how='left')
    return df_final

# 3. Create the HTML File
data = get_nfl_data()
est = pytz.timezone('US/Eastern')
time_str = datetime.now(est).strftime('%I:%M %p EST')

html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL PQ Dashboard</title>
    <style>
        :root {{ --bg: #0f172a; --card: #1e293b; --text: #f8fafc; }}
        body {{ background: var(--bg); color: var(--text); font-family: sans-serif; margin: 0; padding: 15px; }}
        .header {{ text-align: center; padding: 10px; }}
        .search-bar {{ width: 100%; padding: 12px; border-radius: 8px; border: none; margin-bottom: 20px; background: var(--card); color: white; }}
        .team-card {{ background: var(--card); padding: 15px; border-radius: 12px; margin-bottom: 10px; display: flex; align-items: center; border-left: 5px solid; }}
        .logo {{ width: 40px; height: 40px; margin-right: 15px; }}
        .pq-val {{ font-weight: bold; color: #38bdf8; }}
        .status-badge {{ font-size: 0.7em; padding: 3px 8px; border-radius: 8px; margin-top: 5px; display: inline-block; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>NFL PQ Rankings</h1>
        <p>Last Update: {time_str}</p>
        <input type="text" class="search-bar" id="search" placeholder="Search teams..." onkeyup="filter()">
    </div>
    <div id="list">
        {"".join([f'''
        <div class="team-card" style="border-left-color: {r.get('color', '#334155')}">
            <div style="width: 25px; font-weight: bold;">{i+1}</div>
            <img src="{r.get('logo', '')}" class="logo">
            <div style="flex-grow:1">
                <b>{r['team']}</b> ({r['record']})<br>
                <div class="status-badge" style="background: {r['s_color']}">{r['status']}</div>
            </div>
            <div style="text-align: right;"><small>PQ</small><br><span class="pq-val">{r['pq']}</span></div>
        </div>
        ''' for i, r in data.iterrows()])}
    </div>
    <script>
        function filter() {{
            let val = document.getElementById('search').value.toUpperCase();
            document.querySelectorAll('.team-card').forEach(c => c.style.display = c.innerText.toUpperCase().includes(val) ? "flex" : "none");
        }}
    </script>
</body>
</html>
"""

with open("index.html", "w") as f:
    f.write(html_template)
