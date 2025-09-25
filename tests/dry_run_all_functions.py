import sys
import os
sys.path.insert(1, os.path.abspath('.'))

from espn_api.football import League
import gamedaybot.espn.season_recap as recap
import gamedaybot.espn.functionality as espn
from gamedaybot.espn.env_vars import get_env_vars

data = get_env_vars()

league_id = data['league_id']

try:
    year = int(data['year'])
except KeyError:
    year = 2025

try:
    warning = int(data['score_warn'])
except KeyError:
    warning = 0

league = League(league_id, year)
faab = league.settings.faab

print(espn.get_scoreboard_short(league))
print(espn.get_projected_scoreboard(league))
print(espn.get_standings(league))
print(espn.get_close_scores(league))
print(espn.get_monitor(league))
print(espn.get_matchups(league))
print(espn.combined_power_rankings(league))
print(espn.get_trophies(league))
print(espn.optimal_team_scores(league, full_report=True))
print(espn.get_waiver_report(league, True))

print(recap.win_matrix(league))
print(recap.season_trophies(league))
