import sys
import os
sys.path.insert(1, os.path.abspath('.'))

from espn_api.football import League
import gamedaybot.espn.season_recap as recap
import gamedaybot.espn.functionality as espn
from gamedaybot.chat.discord import Discord
from gamedaybot.chat.discord import replace_formatting
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

try:
    test_week = int(os.environ["TEST_WEEK"])
except KeyError: 
    test_week = None

league = League(league_id, year)
faab = league.settings.faab
# discord_bot = Discord(data['discord_webhook_url'])
# discord_bot.send_message('test')

def printr(text):
    print(replace_formatting(text))

printr(espn.get_matchups(league, test_week) + '\n')
printr(espn.get_scoreboard_short(league, test_week) + '\n')
printr(espn.get_projected_scoreboard(league, test_week) + '\n')
printr(espn.get_close_scores(league, test_week) + '\n')
printr(espn.get_standings(league, False, test_week) + '\n')
printr(espn.optimal_team_scores(league, test_week) + '\n')
printr(espn.combined_power_rankings(league, test_week) + '\n')
printr(espn.get_monitor(league, warning) + '\n')
printr(espn.get_inactives(league, test_week) + '\n')
printr(espn.get_trophies(league, True, test_week) + '\n')
printr(espn.get_ai_recap(league, test_week) + '\n')
printr(espn.get_waiver_report(league, faab))
# print(recap.win_matrix(league) + '\n')
# print(recap.season_trophies(league, True) + '\n')


