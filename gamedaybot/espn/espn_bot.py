import os
import sys
sys.path.insert(1, os.path.abspath('.'))
import json
from espn_api.football import League
import gamedaybot.espn.functionality as espn
import gamedaybot.utils as utils
from gamedaybot.chat.discord import Discord
from gamedaybot.espn.env_vars import get_env_vars


def espn_bot(function):
    data = get_env_vars()
    discord_bot = Discord(data['discord_webhook_url'])
    swid = data['swid']
    espn_s2 = data['espn_s2']
    league_id = data['league_id']
    year = data['year']
    test = data['test']
    top_half_scoring = data['top_half_scoring']
    waiver_report = data['waiver_report']
    extra_trophies = data['extra_trophies']
    warning = data['score_warn']

    if swid == '{1}' or espn_s2 == '1':
        league = League(league_id=league_id, year=year)
    else:
        league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

    if league.scoringPeriodId > len(league.settings.matchup_periods) and not test:
        print("Not in active season")
        return

    faab = league.settings.faab

    if test:
        print(espn.get_matchups(league) + '\n')
        print(espn.get_scoreboard_short(league) + '\n')
        print(espn.get_projected_scoreboard(league) + '\n')
        print(espn.get_close_scores(league) + '\n')
        print(espn.get_standings(league, top_half_scoring) + '\n')
        print(espn.optimal_team_scores(league) + '\n')
        print(espn.combined_power_rankings(league) + '\n')
        print(espn.get_monitor(league, warning) + '\n')
        print(espn.get_inactives(league) + '\n')
        if waiver_report and swid != '{1}' and espn_s2 != '1':
            print(espn.get_waiver_report(league, faab) + '\n')
        # print(espn.season_trophies(league, extra_trophies) + '\n')
        function = "get_final"
        # discord_bot.send_message("Testing")

    text = ''
    if function == "get_matchups":
        text = espn.get_matchups(league)
        # text = text + "\n\n" + espn.get_projected_scoreboard(league)
    elif function == "get_monitor":
        text = espn.get_monitor(league, warning)
    elif function == "get_inactives":
        text = espn.get_inactives(league)
    elif function == "get_scoreboard_short":
        text = espn.get_scoreboard_short(league)
        text = text + "\n\n" + espn.get_projected_scoreboard(league)
    elif function == "get_projected_scoreboard":
        text = espn.get_projected_scoreboard(league)
    elif function == "get_close_scores":
        text = espn.get_close_scores(league)
    elif function == "get_power_rankings":
        text = espn.combined_power_rankings(league)
    elif function == "get_trophies":
        text = espn.get_trophies(league)
    elif function == "season_trophies":
        text = espn.season_trophies(league, extra_trophies)  
    elif function == "get_standings":
        text = espn.get_standings(league, top_half_scoring)
    elif function == "get_optimal_scores":
        text = espn.optimal_team_scores(league)
    elif function == "get_final":
        # on Tuesday we need to get the scores of last week
        week = league.current_week - 1
        text = espn.get_scoreboard_short(league, week=week)
        text = text + "\n\n" + espn.get_trophies(league, extra_trophies, week=week)
    elif function == "get_waiver_report" and swid != '{1}' and espn_s2 != '1':
        faab = league.settings.faab
        text = espn.get_waiver_report(league, faab)
    elif function == "init":
        try:
            text = data["init_msg"]
        except KeyError:
            # do nothing here, empty init message
            pass
    else:
        text = "Something happened. HALP"

    if text != '' and not test:
        messages = utils.str_limit_check(text, data['str_limit'])
        for message in messages:
            discord_bot.send_message(message)

    if test:
        #print "get_final" function
        print(text)


if __name__ == '__main__':
    from gamedaybot.espn.scheduler import scheduler
    espn_bot("init")
    scheduler()
