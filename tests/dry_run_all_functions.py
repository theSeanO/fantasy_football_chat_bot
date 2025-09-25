import sys
import os
sys.path.insert(1, os.path.abspath('.'))

from espn_api.football import League
import gamedaybot.espn.season_recap as recap
import gamedaybot.espn.functionality as espn

league_id = os.environ['LEAGUE_ID']

try:
    year = int(os.environ['LEAGUE_YEAR'])
except KeyError:
    year = 2025

try:
    warning = int(os.environ['SCORE_WARNING'])
except KeyError:
    warning = 0

try:
    extra_trophies = bool(os.environ["EXTRA_TROPHIES"])
except KeyError: 
    extra_trophies = True

try:
    test_week = int(os.environ["TEST_WEEK"])
except KeyError: 
    test_week = None

league = League(league_id, year)
faab = league.settings.faab

print(espn.get_scoreboard_short(league, week=test_week))
print(espn.get_projected_scoreboard(league, week=test_week))
print(espn.get_standings(league, week=test_week))
print(espn.get_close_scores(league, week=test_week))
print(espn.get_monitor(league, warning=warning))
print(espn.get_matchups(league, week=test_week))
print(espn.combined_power_rankings(league, week=test_week))
print(espn.get_trophies(league, week=test_week))
print(espn.optimal_team_scores(league, week=test_week))
print(espn.get_waiver_report(league, faab=faab))

print(recap.win_matrix(league))
print(recap.season_trophies(league))
