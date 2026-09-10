import os
import gamedaybot.espn.functionality as espn
import gamedaybot.utils.util as util


def get_env_vars():
    data = {}
    try:
        ff_start_date = os.environ["START_DATE"]
    except KeyError:
        ff_start_date = '2026-09-08'

    data['ff_start_date'] = ff_start_date

    try:
        ff_end_date = os.environ["END_DATE"]
    except KeyError:
        ff_end_date = '2027-01-10'

    data['ff_end_date'] = ff_end_date

    try:
        my_timezone = os.environ["TIMEZONE"]
    except KeyError:
        my_timezone = 'America/New_York'

    data['my_timezone'] = my_timezone

    try:
        daily_waiver = util.str_to_bool(os.environ["DAILY_WAIVER"])
    except KeyError:
        daily_waiver = False

    data['daily_waiver'] = daily_waiver

    try:
        monitor_report = util.str_to_bool(os.environ["MONITOR_REPORT"])
    except KeyError:
        monitor_report = True

    data['monitor_report'] = monitor_report

    try:
        close_scores_threshold = int(os.environ["CLOSE_SCORES_THRESHOLD"])
    except (KeyError, ValueError):
        # Unset, or set to something that is not a whole number. A typo in one
        # optional env var should not take down every scheduled message, so
        # fall back to the default rather than raise.
        close_scores_threshold = espn.CLOSE_SCORES_DEFAULT_THRESHOLD

    data['close_scores_threshold'] = close_scores_threshold

    str_limit = 2000  # discord char limit

    try:
        discord_webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
    except KeyError:
        discord_webhook_url = 1

    if (len(str(discord_webhook_url)) <= 1):
        # Ensure that there's info for at least one messaging platform,
        # use length of str in case of blank but non null env variable
        raise Exception("No messaging platform info provided. Be sure one of BOT_ID, SLACK_WEBHOOK_URL, or DISCORD_WEBHOOK_URL env variables are set")

    data['str_limit'] = str_limit
    data['discord_webhook_url'] = discord_webhook_url

    data['league_id'] = os.environ["LEAGUE_ID"]

    try:
        year = int(os.environ["LEAGUE_YEAR"])
    except KeyError:
        year = 2026

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
        test = util.str_to_bool(os.environ["TEST"])
    except KeyError:
        test = False

    data['test'] = test

    try:
        waiver_report = util.str_to_bool(os.environ["WAIVER_REPORT"])
    except KeyError:
        waiver_report = False

    data['waiver_report'] = waiver_report

    try:
        extra_trophies = util.str_to_bool(os.environ["EXTRA_TROPHIES"])
    except KeyError:
        extra_trophies = False

    data['extra_trophies'] = extra_trophies

    try:
        score_warn = int(os.environ["SCORE_WARNING"])
    except KeyError:
        score_warn = 3

    data['score_warn'] = score_warn

    try:
        data['init_msg'] = os.environ["INIT_MSG"]
    except KeyError:
        # do nothing here, empty init message
        pass

    return data


def split_emotes(league):
    emotes = ['']
    if not league:
        return emotes
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
