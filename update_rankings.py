import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# Data Sources
GAMES_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
TEAMS_URL = "https://raw.githubusercontent.com/nflverse/nflfastR-data/master/teams_colors_logos.csv"
# Updated Roster Source for 2025
ROSTER_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"

def get_nfl_data():
    games = pd.read_csv(GAMES_URL)
    teams_meta = pd.read_csv(TEAMS_URL)
    # Get active players for rosters
    rosters = pd.read_csv(ROSTER_URL)
    rosters = rosters[rosters['status'] == 'Active'][['team_abbr', 'display_name', 'position', 'headshot_url']]
    
    mapping = {'team': ['team_abbr', 'team'], 'logo': ['team_logo_espn', 'logo'], 'color': ['team_color', 'color']}
    final_mapping = {opt: target for target, options in mapping.items() for opt in options if opt in teams_meta.columns}
    teams_meta = teams_meta.rename(columns=final_mapping)

    played = games[(games['season'] == 2025) & (games['game_type'] == 'REG')].dropna(subset=['home_score']).copy()
    if played.empty: return pd.DataFrame()

    team_list = pd.unique(played[['home_team', 'away_team']].values.ravel())
    max_week = played['week'].max()
    
    records = {t: {'w': 0, 'l': 0, 'pct': 0} for t in team_list}
    for t in team_list:
        tg = played[(played['home_team'] == t) | (played['away_team'] == t)]
        wins = len(tg[((tg['home_team'] == t) & (tg['home_score'] > tg['away_score'])) | ((tg['away_team'] == t) & (tg['away_score'] > tg['home_score']))])
        records[t] = {'w': wins, 'l': len(tg)-wins, 'pct': wins/len(tg)}

    dashboard = []
    for t in team_list:
        tg = played[(played['home_team'] == t) | (played['away_team'] == t)]
        pq = sum((((g['home_score'] - g['away_score']) if g['home_team'] == t else (g['away_score'] - g['home_score'])) * (records[g['away_team'] if g['home_team'] == t else g['home_team']]['pct'] + 0.1) * (0.95 ** (max_week - g['week']))) for _, g in tg.iterrows())
        
        # Prepare Player List HTML (Hidden until clicked)
        team_p = rosters[rosters['team_abbr'] == t].head(4).to_dict('records')
        p_html = "".join([f"<div class='p-row'><img src='{p['headshot_url']}' class='p-img'><b>{p['display_name']}</b> <span>{p['position']}</span></div>" for p in team_p])

        status, s_color = ("CLINCHED", "#28a745") if records[t]['w'] >= 10 else (("ELIMINATED", "#dc3545") if records[t]['w'] <= 6 else ("IN THE HUNT", "#007bff"))
        dashboard.append({'team': t, 'pq': round(pq, 2), 'record': f"{records[t]['w']}-{records[t]['l']}", 'status': status, 's_color': s_color, 'players': p_html})

    return pd.DataFrame(dashboard).sort_values('pq', ascending=False).merge(teams_meta[['team', 'logo', 'color']], on='team', how='left')

data = get_nfl_data()
time_str = datetime.now(pytz.timezone('US/Eastern')).strftime('%I:%M %p EST')

html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL PQ Dashboard</title>
    <style>
        :root {{ --bg: #0f172a; --card: #1e293b; --text: #f8fafc; --accent: #38bdf8; }}
        body {{ background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif; padding: 15px; margin: 0; }}
        .card {{ background: var(--card); border-radius: 12px; padding: 15px; margin-bottom: 10px; display: flex; align-items: center; border-left: 6px solid; cursor: pointer; transition: transform 0.1s; }}
        .card:active {{ transform: scale(0.98); }}
        .logo {{ width: 42px; height: 42px; margin-right: 15px; }}
        .pq-box {{ text-align: right; margin-left: auto; }}
        .pq-val {{ font-weight: bold; color: var(--accent); font-size: 1.2em; }}
        
        /* Modal - Hidden by default */
        #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 100; align-items: center; justify-content: center; backdrop-filter: blur(4px); }}
        .modal-content {{ background: #1e293b; width: 85%; max-width: 350px; border-radius: 20px; padding: 25px; border: 1px solid #334155; position: relative; }}
        .p-row {{ display: flex; align-items: center; padding: 10px 0; border-bottom: 1px solid #334155; }}
        .p-img {{ width: 45px; height: 45px; border-radius: 50%; background: #0f172a; margin-right: 12px; border: 1px solid #475569; }}
        .close-btn {{ width: 100%; background: #ef4444; border: none; color: white; padding: 12px; border-radius: 10px; margin-top: 20px; font-weight: bold; cursor: pointer; }}
    </style>
</head>
<body>
    <div style="text-align:center; padding: 10px 0;"><h1>🏈 PQ RANKINGS</h1><small>Tap team for key players | {time_str}</small></div>
    
    {"".join([f'''
    <div class="card" style="border-left-color: {r['color']}" onclick="openModal('{r['team']}', `{r['players']}`)">
        <div style="width: 20px; opacity: 0.3; font-size: 0.8em;">{i+1}</div>
        <img src="{r['logo']}" class="logo">
        <div>
            <div style="font-weight:bold;">{r['team']}</div>
            <div style="font-size:0.8em; opacity:0.8;">{r['record']} • <span style="color:{r['s_color']}">{r['status']}</span></div>
        </div>
        <div class="pq-box"><small>PQ</small><br><span class="pq-val">{r['pq']}</span></div>
    </div>
    ''' for i, r in data.iterrows()])}

    <div id="modal" onclick="closeModal()">
        <div class="modal-content" onclick="event.stopPropagation()">
            <h2 id="m-title" style="margin-top:0;"></h2>
            <div id="m-body"></div>
            <button class="close-btn" onclick="closeModal()">CLOSE</button>
        </div>
    </div>

    <script>
        function openModal(name, players) {{
            document.getElementById('m-title').innerText = name + " Stars";
            document.getElementById('m-body').innerHTML = players;
            document.getElementById('modal').style.display = 'flex';
        }}
        function closeModal() {{ document.getElementById('modal').style.display = 'none'; }}
    </script>
</body>
</html>
"""
with open("index.html", "w") as f: f.write(html_content)
