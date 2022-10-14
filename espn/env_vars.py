import os
import espn.functionality as espn
import ff_bot.utils as utils

def get_env_vars():
    data = {}
    try:
        ff_start_date = os.environ["START_DATE"]
    except KeyError:
        ff_start_date = '2022-09-08'

    data['ff_start_date'] = ff_start_date

    try:
        ff_end_date = os.environ["END_DATE"]
    except KeyError:
        ff_end_date = '2023-01-04'

    data['ff_end_date'] = ff_end_date

    try:
        my_timezone = os.environ["TIMEZONE"]
    except KeyError:
        my_timezone = 'America/New_York'

    data['my_timezone'] = my_timezone

    try:
        daily_waiver = utils.str_to_bool(os.environ["DAILY_WAIVER"])
    except KeyError:
        daily_waiver = False

    data['daily_waiver'] = daily_waiver

    try:
        monitor_report = utils.str_to_bool(os.environ["MONITOR_REPORT"])
    except KeyError:
        monitor_report = True

    data['monitor_report'] = monitor_report

    str_limit = 40000 #slack char limit

    try:
        discord_webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
        str_limit = 3000
    except KeyError:
        discord_webhook_url = 1

    if len(str(discord_webhook_url)) <= 1:
        # Ensure that there's info for at least one messaging platform,
        # use length of str in case of blank but non null env variable
        raise Exception("No messaging platform info provided. Be sure one of BOT_ID,\
                        SLACK_WEBHOOK_URL, or DISCORD_WEBHOOK_URL env variables are set")

    data['str_limit'] = str_limit
    data['discord_webhook_url'] = discord_webhook_url

    data['league_id'] = os.environ["LEAGUE_ID"]

    try:
        year = int(os.environ["LEAGUE_YEAR"])
    except KeyError:
        year = 2022

    data['year'] = year

    try:
        swid = os.environ["SWID"]
    except KeyError:
        swid = '{1}'

    if swid.find("{", 0) == -1:
        swid = "{" + swid
    if swid.find("}", -1) == -1:
        swid = swid + "}"

    data['swid'] = swid

    try:
        espn_s2 = os.environ["ESPN_S2"]
    except KeyError:
        espn_s2 = '1'

    data['espn_s2'] = espn_s2

    try:
        test = utils.str_to_bool(os.environ["TEST"])
    except KeyError:
        test = False

    data['test'] = test

    try:
        top_half_scoring = utils.str_to_bool(os.environ["TOP_HALF_SCORING"])
    except KeyError:
        top_half_scoring = False

    data['top_half_scoring'] = top_half_scoring

    data['random_phrase'] = get_random_phrase()

    try:
        waiver_report = utils.str_to_bool(os.environ["WAIVER_REPORT"])
    except KeyError:
        waiver_report = False

    data['waiver_report'] = waiver_report

    try:
        score_warn = int(os.environ["SCORE_WARNING"])
    except KeyError:
        score_warn = 0

    data['score_warning'] = score_warn

    try:
        extra_trophies = utils.str_to_bool(os.environ["EXTRA_TROPHIES"])
    except KeyError:
        extra_trophies = False

    data['extra_trophies'] = extra_trophies

    try:
        users += os.environ["USERS"].split(',') 
    except KeyError:
        users += [''] * 10

    data['users'] = users

    try:
        emotes += os.environ["EMOTES"].split(',')
    except KeyError:
        emotes += [''] * 10

    data['emotes'] = emotes

    try:
        data['init_msg'] = os.environ["INIT_MSG"]
    except KeyError:
        # do nothing here, empty init message
        pass

    return data

def get_random_phrase():
    random_phrase = False
    try:
        random_phrase = utils.str_to_bool(os.environ["RANDOM_PHRASE"])
    except KeyError:
        random_phrase = False
    
    return random_phrase

def split_emotes(league):
    emotes = ['']
    try:
        emotes += os.environ["EMOTES"].split(',')
    except KeyError:
        emotes += [''] * league.teams[-1].team_id

    return emotes

def split_users(league):
    users = ['']
    try:
        users += os.environ["USERS"].split(',') 
    except KeyError:
        users += [''] * league.teams[-1].team_id

    return users