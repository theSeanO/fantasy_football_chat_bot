import os
# For local use
import sys
sys.path.insert(1, os.path.abspath('.'))
import gamedaybot.utils.util as util
from gamedaybot.chat.discord import Discord
from gamedaybot.espn.env_vars import get_env_vars
import gamedaybot.espn.functionality as espn
import gamedaybot.espn.season_recap as recap

from espn_api.football import League
import json
import logging

logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)


def espn_bot(function):
    """
    This function is used to send messages to a messaging platform (e.g. Slack, Discord, or GroupMe) with information
    about a fantasy football league.

    Parameters
    ----------
    function: str
        A string that specifies which type of information to send (e.g. "get_matchups", "get_power_rankings").

    Returns
    -------
    None

    Notes
    -----
    The function uses the following information from the data dictionary:

    str_limit: the character limit for messages on slack.
    discord_webhook_url: the webhook url for the discord bot.
        If not provided, defaults to 1.
    league_id: the id of the fantasy football league.
    year: the year of the league.
        If not provided, defaults to current year.
    swid: the swid of the league.
        If not provided, defaults to '{1}'.
    espn_s2: the espn s2 of the league.
        If not provided, defaults to '1'.
    top_half_scoring: a boolean that indicates whether to include only the top half of the league in the standings.
        If not provided, defaults to False.
    random_phrase: a boolean that indicates whether to include a random phrase in the message.
        If not provided, defaults to False.

    The function creates GroupMe, Slack, and Discord objects, and a League object using the provided information.
    It then uses the specified function to generate a message and sends it through the appropriate messaging platform.

    Possible function values:

    get_matchups: sends the current week's matchups and the projected scores for the remaining games.
    get_monitor: sends a message with a summary of the current week's scores.
    get_scoreboard_short: sends a short version of the current week's scores.
    get_projected_scoreboard: sends the projected scores for the remaining games.
    get_close_scores: sends a message with the scores of games that have a difference of less than 7 points.
    get_power_rankings: sends a message with the power rankings for the league.
    get_trophies: sends a message with the trophies for the league.
    get_standings: sends a message with the standings for the league.
    get_final: sends the final scores and trophies for the previous week.
    get_waiver_report: sends a message with the waiver report for the league.
    init: sends a message to confirm that the bot has been set up.
    """
    
    data = get_env_vars()
    str_limit = data['str_limit']

    try:
        discord_webhook_url = data['discord_webhook_url']
    except KeyError:
        discord_webhook_url = 1

    if (len(str(discord_webhook_url)) <= 1):
        # Ensure that there's info for at least one messaging platform,
        # use length of str in case of blank but non null env variable
        raise Exception("No messaging platform info provided. Be sure DISCORD_WEBHOOK_URL env variable is set")
    
    league_id = data['league_id']

    try:
        year = int(data['year'])
    except KeyError:
        year = 2024

    try:
        swid = data['swid']
    except KeyError:
        swid = '{1}'

    if swid.find("{", 0) == -1:
        swid = "{" + swid
    if swid.find("}", -1) == -1:
        swid = swid + "}"

    try:
        espn_s2 = data['espn_s2']
    except KeyError:
        espn_s2 = '1'

    try:
        top_half_scoring = data['top_half_scoring']
    except KeyError:
        top_half_scoring = False

    try:
        warning = int(data['score_warn'])
    except KeyError:
        warning = 0

    try:
        extra_trophies = data['extra_trophies']
    except KeyError:
        extra_trophies = False

    try:
        test = data['test']
    except KeyError:
        test = False

    discord_bot = Discord(discord_webhook_url)

    if swid == '{1}' or espn_s2 == '1':
        league = League(league_id=league_id, year=year)
    else:
        league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

    try:
        broadcast_message = data['broadcast_message']
    except KeyError:
        broadcast_message = None

    # always let init and broadcast run
    if function not in ["init", "broadcast", "win_matrix", "season_trophies"] and league.scoringPeriodId > len(league.settings.matchup_periods):
        logger.info("Not in active season")
        return

    text = ''
    logger.info("Function: " + function)

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
    elif function == "win_matrix":
        text = recap.win_matrix(league)
    elif function == "season_trophies":
        text = recap.season_trophies(league, extra_trophies)  
    elif function == "get_standings":
        text = espn.get_standings(league, top_half_scoring) + '\n'
    elif function == "get_optimal_scores":
        text = espn.optimal_team_scores(league) + '\n'
    elif function == "get_final":
        # on Tuesday we need to get the scores of last week
        week = league.current_week - 1
        text = espn.get_scoreboard_short(league, week=week)
        text = text + "\n\n" + espn.get_trophies(league, extra_trophies, week=week)
    elif function == "get_waiver_report" and swid != '{1}' and espn_s2 != '1':
        faab = league.settings.faab
        text = espn.get_waiver_report(league, faab)
    elif function == "broadcast":
        try:
            text = broadcast_message
        except KeyError:
            # do nothing here, empty broadcast message
            pass
    elif function == "init":
        try:
            text = data["init_msg"]
        except KeyError:
            # do nothing here, empty init message
            pass
    else:
        text = "Something bad happened. HALP"

    logger.debug(data)
    if text != '' and not test:
        logger.debug(text)
        messages = util.str_limit_check(text, str_limit)
        for message in messages:
            discord_bot.send_message(message)  


if __name__ == '__main__':
    from gamedaybot.espn.scheduler import scheduler

    espn_bot("init")
    scheduler()
