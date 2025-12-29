import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import json

# Data URLs
GAMES_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
TEAMS_URL = "https://github.com/nflverse/nfldata/raw/master/data/teams.csv"
ROSTER_URL = "https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_2024.csv" # 2024 for base headshots
STATS_URL = "https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats.csv"

def get_nfl_data():
    # 1. Load Data
    games = pd.read_csv(GAMES_URL)
    teams_meta = pd.read_csv(TEAMS_URL)[['team_abbr', 'team_logo_espn', 'team_color', 'team_conf']]
    roster = pd.read_csv(ROSTER_URL)[['team', 'full_name', 'position', 'headshot_url', 'jersey_number']]
    stats = pd.read_csv(STATS_URL)
    stats = stats[stats['season'] == 2024] # Most recent full stats

    # 2. PQ Math
    played = games[(games['season'] == 2025) & (games['game_type'] == 'REG')].dropna(subset=['home_score']).copy()
    max_week = played['week'].max()
    team_list = pd.unique(played[['home_team', 'away_team']].values.ravel())
    
    records = {}
    for t in team_list:
        tg = played[(played['home_team'] == t) | (played['away_team'] == t)]
        wins = len(tg[((tg['home_team'] == t) & (tg['home_score'] > tg['away_score'])) | ((tg['away_team'] == t) & (tg['away_score'] > tg['home_score']))])
        records[t] = {'win_pct': wins / len(tg), 'w': wins, 'l': len(tg)-wins}

    dashboard_data = []
    for t in team_list:
        tg = played[(played['home_team'] == t) | (played['away_team'] == t)]
        pq = sum((((g['home_score'] - g['away_score']) if g['home_team'] == t else (g['away_score'] - g['home_score'])) * (records[g['away_team'] if g['home_team'] == t else g['home_team']]['win_pct'] + 0.1) * (0.95 ** (max_week - g['week']))) for _, g in tg.iterrows())
        
        # Playoff Status Logic
        w = records[t]['w']
        status, s_color = ("CLINCHED", "#28a745") if w >= 10 else (("ELIMINATED", "#dc3545") if w <= 6 else ("IN THE HUNT", "#007bff"))

        # Find Key Players
        t_roster = roster[roster['team'] == t]
        qb = t_roster[t_roster['position'] == 'QB'].head(1).to_dict('records')
        wr = t_roster[t_roster['position'] == 'WR'].head(1).to_dict('records')
        
        # Sack Leader
        t_stats = stats[stats['recent_team'] == t].groupby('player_name')['sacks'].sum().reset_index()
        sack_leader_name = t_stats.sort_values('sacks', ascending=False).iloc[0]['player_name'] if not t_stats.empty else "N/A"
        sack_leader_img = t_roster[t_roster['full_name'] == sack_leader_name]['headshot_url'].values[0] if sack_leader_name in t_roster['full_name'].values else ""

        dashboard_data.append({
            'team': t, 'pq': round(pq, 2), 'record': f"{w}-{records[t]['l']}", 'status': status, 's_color': s_color,
            'qb': qb[0] if qb else {}, 'wr': wr[0] if wr else {}, 'sack_leader': {'name': sack_leader_name, 'img': sack_leader_img}
        })

    df_final = pd.DataFrame(dashboard_data).sort_values('pq', ascending=False).merge(teams_meta, left_on='team', right_on='team_abbr')
    return df_final

# Build HTML
data = get_nfl_data()
est = pytz.timezone('US/Eastern')
time_str = datetime.now(est).strftime('%I:%M %p EST')

html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL PQ Live</title>
    <style>
        :root {{ --bg: #0f172a; --card: #1e293b; --text: #f8fafc; }}
        body {{ background: var(--bg); color: var(--text); font-family: sans-serif; margin: 0; padding: 15px; }}
        .header {{ text-align: center; padding: 20px; }}
        .search-bar {{ width: 100%; padding: 12px; border-radius: 8px; border: none; margin-bottom: 20px; background: var(--card); color: white; }}
        .team-card {{ background: var(--card); padding: 15px; border-radius: 12px; margin-bottom: 10px; display: flex; align-items: center; cursor: pointer; transition: 0.2s; }}
        .team-card:hover {{ transform: scale(1.02); }}
        .logo {{ width: 45px; height: 45px; margin-right: 15px; }}
        .name-box {{ flex-grow: 1; }}
        .pq-val {{ font-weight: bold; color: #38bdf8; }}
        .status-badge {{ font-size: 0.7em; padding: 4px 8px; border-radius: 10px; margin-top: 5px; display: inline-block; }}
        
        /* Modal Style */
        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); align-items: center; justify-content: center; z-index: 100; }}
        .modal-content {{ background: var(--card); width: 90%; max-width: 500px; padding: 25px; border-radius: 20px; text-align: center; position: relative; }}
        .close-btn {{ position: absolute; top: 15px; right: 20px; font-size: 24px; cursor: pointer; }}
        .player-row {{ display: flex; justify-content: space-around; margin-top: 20px; }}
        .player-img {{ width: 80px; height: 80px; border-radius: 50%; border: 3px solid #38bdf8; background: #eee; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏈 NFL PQ DASHBOARD</h1>
        <p>Live Week 17 | {time_str}</p>
        <input type="text" class="search-bar" id="search" placeholder="Search team or conference..." onkeyup="filterTeams()">
    </div>

    <div id="team-list">
        {"".join([f'''
        <div class="team-card" style="border-left: 5px solid {r['team_color']}" onclick='showDetails({json.dumps(r.to_dict())})'>
            <div style="width: 30px; font-weight: bold; color: #64748b;">{i+1}</div>
            <img src="{r['team_logo_espn']}" class="logo">
            <div class="name-box">
                <div style="font-weight: bold;">{r['team']} <span style="font-weight: normal; color: #94a3b8; font-size: 0.8em;">{r['record']}</span></div>
                <div class="status-badge" style="background: {r['s_color']}">{r['status']}</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.7em; color: #94a3b8;">PQ SCORE</div>
                <div class="pq-val">{r['pq']}</div>
            </div>
        </div>
        ''' for i, r in data.iterrows()])}
    </div>

    <div class="modal" id="modal">
        <div class="modal-content" id="modal-content"></div>
    </div>

    <script>
        function filterTeams() {{
            let val = document.getElementById('search').value.toUpperCase();
            document.querySelectorAll('.team-card').forEach(card => {{
                card.style.display = card.innerText.toUpperCase().includes(val) ? "flex" : "none";
            }});
        }}

        function showDetails(data) {{
            const modal = document.getElementById('modal');
            const content = document.getElementById('modal-content');
            content.innerHTML = `
                <span class="close-btn" onclick="document.getElementById('modal').style.display='none'">&times;</span>
                <img src="${{data.team_logo_espn}}" style="width: 80px;">
                <h2>${{data.team}} Profile</h2>
                <div class="player-row">
                    <div><img class="player-img" src="${{data.qb.headshot_url || ''}}"><p>QB<br>${{data.qb.full_name || 'N/A'}}</p></div>
                    <div><img class="player-img" src="${{data.wr.headshot_url || ''}}"><p>WR1<br>${{data.wr.full_name || 'N/A'}}</p></div>
                </div>
                <hr style="border: 0.5px solid #334155; margin: 20px 0;">
                <h3 style="color: #f43f5e;">SACK LEADER</h3>
                <img class="player-img" style="border-color: #f43f5e;" src="${{data.sack_leader.img || ''}}">
                <p>${{data.sack_leader.name}}</p>
                <button onclick="document.getElementById('modal').style.display='none'" style="margin-top:20px; padding: 10px 20px; border-radius: 10px; border: none; background: #38bdf8; color: white; font-weight: bold;">CLOSE</button>
            `;
            modal.style.display = 'flex';
        }}
    </script>
</body>
</html>
"""

with open("index.html", "w") as f:
    f.write(html_template)
