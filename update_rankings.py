import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# 2025 Data Sources
GAMES_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
TEAMS_URL = "https://raw.githubusercontent.com/nflverse/nflfastR-data/master/teams_colors_logos.csv"
ROSTER_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"

def get_nfl_data():
    # Load data
    try:
        games = pd.read_csv(GAMES_URL)
        teams_meta = pd.read_csv(TEAMS_URL)
        rosters = pd.read_csv(ROSTER_URL)
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

    # Filter active players
    rosters = rosters[rosters['status'] == 'Active'][['team_abbr', 'display_name', 'position', 'headshot_url']]
    
    # Map team metadata
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
        
        # Build the player list for the pop-up
        team_p = rosters[rosters['team_abbr'] == t].head(4).to_dict('records')
        p_html = "".join([f"<div class='p-row'><img src='{p['headshot_url']}' class='p-img'><b>{p['display_name']}</b> <span>{p['position']}</span></div>" for p in team_p])

        status, s_color = ("CLINCHED", "#28a745") if records[t]['w'] >= 10 else (("ELIMINATED", "#dc3545") if records[t]['w'] <= 6 else ("IN THE HUNT", "#38bdf8"))
        dashboard.append({'team': t, 'pq': round(pq, 2), 'record': f"{records[t]['w']}-{records[t]['l']}", 'status': status, 's_color': s_color, 'players': p_html})

    return pd.DataFrame(dashboard).sort_values('pq', ascending=False).merge(teams_meta[['team', 'logo', 'color']], on='team', how='left')

data = get_nfl_data()
time_str = datetime.now(pytz.timezone('US/Eastern')).strftime('%I:%M %p EST')

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL PQ Dashboard</title>
    <style>
        :root {{ --bg: #0f172a; --card: #1e293b; --text: #f8fafc; --accent: #38bdf8; }}
        body {{ background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; padding: 15px; margin: 0; }}
        .card {{ background: var(--card); border-radius: 12px; padding: 15px; margin-bottom: 10px; display: flex; align-items: center; border-left: 6px solid; cursor: pointer; }}
        .logo {{ width: 42px; height: 42px; margin-right: 15px; }}
        .pq-val {{ font-weight: bold; color: var(--accent); font-size: 1.2em; margin-left: auto; }}
        #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 100; align-items: center; justify-content: center; }}
        .modal-content {{ background: #1e293b; width: 85%; max-width: 350px; border-radius: 20px; padding: 25px; text-align: center; border: 1px solid #334155; }}
        .p-row {{ display: flex; align-items: center; padding: 10px 0; border-bottom: 1px solid #334155; text-align: left; }}
        .p-img {{ width: 45px; height: 45px; border-radius: 50%; margin-right: 12px; background: #0f172a; }}
        .close-btn {{ width: 100%; background: #ef4444; border: none; color: white; padding: 12px; border-radius: 10px; margin-top: 20px; font-weight: bold; cursor: pointer; }}
    </style>
</head>
<body>
    <div style="text-align:center;"><h1>🏈 NFL PQ DASHBOARD</h1><p><b>Tap team</b> for stars | {time_str}</p></div>
    
    {"".join([f'''
    <div class="card" style="border-left-color: {r['color']}" onclick="openModal('{r['team']}', `{r['players']}`)">
        <img src="{r['logo']}" class="logo">
        <div><b>{r['team']}</b><br><small>{r['record']} • <span style="color:{r['s_color']}">{r['status']}</span></small></div>
        <div class="pq-val">{r['pq']}</div>
    </div>
    ''' for i, r in data.iterrows()])}

    <div id="modal" onclick="closeModal()">
        <div class="modal-content" onclick="event.stopPropagation()">
            <h2 id="m-title"></h2>
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
