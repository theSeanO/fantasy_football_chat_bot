import logging
import os
from datetime import date, datetime
import sys
sys.path.insert(1, os.path.abspath('.'))
import gamedaybot.utils.util as util
import gamedaybot.espn.env_vars as env_vars

logger = logging.getLogger(__name__)

# Largest projected point difference that still counts as a close matchup.
# Overridable per deployment with the CLOSE_SCORES_THRESHOLD env var, which
# env_vars.get_env_vars() reads; this is the fallback when it is unset.
CLOSE_SCORES_DEFAULT_THRESHOLD = 15

# Transaction status and item types, as ESPN spells them.
TXN_STATUS_EXECUTED = 'EXECUTED'
TXN_ITEM_ADD = 'ADD'
TXN_ITEM_DROP = 'DROP'

# Player ids per player-card request. espn_api sends the id filter in a request
# header and ESPN rejects very large ones, so batches stay well inside that.
PLAYER_CARD_BATCH = 50


def season_started(league):
    """
    Check whether the league has reached a scoring period yet.

    ESPN reports scoringPeriodId == 0 for a league whose season has not begun:
    one that has not drafted, one abandoned mid-season, and every league before
    week 1 is scored. In that state league.box_scores() raises
    KeyError('rosterForCurrentScoringPeriod'), because the team payload has no
    roster for a period that does not exist.

    Only an explicit 0 counts. A scoring period we cannot read is not evidence
    of anything, so it proceeds exactly as before.

    Parameters
    ----------
    league : espn_api.football.League
        The league to check.

    Returns
    -------
    bool
        True when box scores can safely be fetched.
    """
    period = getattr(league, 'scoringPeriodId', None)
    return not (isinstance(period, int) and period == 0)


def fetch_box_scores(league, week=None):
    """
    Fetch box scores, or return an empty list when the season has not started.

    Every box-score read goes through here so the guard cannot be forgotten at
    one call site. Callers must treat an empty list as "nothing to report"
    rather than rendering an empty report.

    Parameters
    ----------
    league : espn_api.football.League
        The league to fetch for.
    week : int, optional
        The week to fetch. Defaults to the league's current week.

    Returns
    -------
    list
        The box scores, or an empty list when the season has not started.
    """
    if not season_started(league):
        logger.info('Season has not started (scoringPeriodId=0); skipping box scores')
        return []
    return league.box_scores(week=week)


def get_scoreboard_short(league, week=None, box_scores=None):
    """
    Retrieve the scoreboard for a given week of the fantasy football season.

    Parameters
    ----------
    league: espn_api.football.League
        The league for which to retrieve the scoreboard.
    week: int
        The week of the season for which to retrieve the scoreboard.
    box_scores: list, optional
        Pre-fetched box scores for the same week, to avoid a duplicate API call.

    Returns
    -------
    list of dict
        A list of dictionaries representing the games on the scoreboard for the given week. Each dictionary contains
        information about a single game, including the teams and their scores.
    """

    emotes = env_vars.split_emotes(league)
    if box_scores is None:
        box_scores = fetch_box_scores(league, week=week)
    score = ['%s#c#%4s %6.2f - %6.2f %4s#c# %s' % (emotes[i.home_team.team_id], i.home_team.team_abbrev, i.home_score,
                                    i.away_score, i.away_team.team_abbrev, emotes[i.away_team.team_id]) for i in box_scores
             if i.away_team]

    if not score:
        return util.NO_MATCHUP_DATA

    if week == league.current_week - 1:
        text = ['#q##u##b#Final Score Update#b##u# ']
    else:
        text = ['#q##u##b#Score Update#b##u#']
    
    text += score
    return '\n'.join(text)


def get_projected_scoreboard(league, week=None, box_scores=None):
    """
    Retrieve the projected scoreboard for a given week of the fantasy football season.

    Parameters
    ----------
    league: espn_api.football.League
        The league for which to retrieve the projected scoreboard.
    week: int
        The week of the season for which to retrieve the projected scoreboard.
    box_scores: list, optional
        Pre-fetched box scores for the same week, to avoid a duplicate API call.

    Returns
    -------
    list of dict
        A list of dictionaries representing the projected games on the scoreboard for the given week. Each dictionary
        contains information about a single game, including the teams and their projected scores.
    """
    emotes = env_vars.split_emotes(league)
    if box_scores is None:
        box_scores = fetch_box_scores(league, week=week)

    score = ['%s#c#%4s %6.2f - %6.2f %4s#c# %s' % (emotes[i.home_team.team_id], i.home_team.team_abbrev, get_projected_total(i.home_lineup),
                                    get_projected_total(i.away_lineup), i.away_team.team_abbrev, emotes[i.away_team.team_id]) for i in box_scores
             if i.away_team]

    if not score:
        return util.NO_MATCHUP_DATA

    text = ['#q##u##b#Approximate Projected Scores#b##u#'] + score
    return '\n'.join(text)


def get_standings(league):
    """
    Retrieve the current standings for a fantasy football league.

    Parameters
    ----------
    league: object
        The league object for which to retrieve the standings.

    Returns
    -------
    str
        A string containing the current standings, formatted as a list of teams with their records and positions.
    """

    emotes = env_vars.split_emotes(league)    
    standings = league.standings()

    records = util.align_records([f"{team.wins}-{team.losses} | {team.points_for:.2f}" for team in standings])
    standings_txt = [f"{pos + 1:2}: {emotes[team.team_id]} {team.team_name} #c#[{record}]#c#" for
                     pos, (team, record) in enumerate(zip(standings, records))]
        
    title = ['#q##u##b#Current Standings#b##u# [Record | Points for]']

    text = title + standings_txt + ['\u200e']
    return "\n".join(text)


def get_projected_total(lineup):
    """
    Retrieve the projected total points for a given lineup in a fantasy football league.

    Parameters
    ----------
    lineup : list
        A list of player objects that represents the lineup

    Returns
    -------
    float
        The projected total points for the given lineup.
    """

    total_projected = 0
    for i in lineup:
        # exclude player on bench and injured reserve
        if i.slot_position != 'BE' and i.slot_position != 'IR':
            # Check if the player has already played or not
            if i.points != 0 or i.game_played > 0:
                total_projected += i.points
            else:
                total_projected += i.projected_points
    return total_projected


def all_played(lineup):
    """
    Check if all the players in a given lineup have played their game.

    Parameters
    ----------
    lineup : list
        A list of player objects that represents the lineup

    Returns
    -------
    bool
        True if all the players in the lineup have played their game, False otherwise.
    """

    for i in lineup:
        # exclude player on bench and injured reserve
        if i.slot_position != 'BE' and i.slot_position != 'IR' and i.game_played < 100:
            return False
    return True


def get_monitor(league, warning, box_scores=None):
    """
    Retrieve a list of players from a given fantasy football league that should be monitored during a game.

    Parameters
    ----------
    league: object
        The league object for which to retrieve the monitor players.
    box_scores: list, optional
        Pre-fetched box scores for the current week, to avoid a duplicate API call.

    Returns
    -------
    str
        A string containing the list of players to monitor, formatted as a list of player names and status.
    """

    emotes = env_vars.split_emotes(league)
    if box_scores is None:
        box_scores = fetch_box_scores(league)
    monitor = []
    text = ''

    for i in box_scores:
        monitor += scan_roster(i.home_lineup, i.home_team, warning, emotes)
        monitor += scan_roster(i.away_lineup, i.away_team, warning, emotes)
    
    if not monitor:
        return ('')
    
    text = ['#q##u##b#Players to Monitor#b##u# '] + monitor
    
    return '\n'.join(text)


def get_inactives(league, box_scores=None):
    """
    Retrieve a list of players from a given fantasy football league that are likely inactive and need to be replaced.

    Parameters
    ----------
    league: object
        The league object for which to retrieve the inactive players.

    Returns
    -------
    str
        A string containing the list of inactive players, formatted as a list of player names and status.
    """
    
    users = env_vars.split_users(league)
    emotes = env_vars.split_emotes(league)
    if box_scores is None:
        box_scores = fetch_box_scores(league)
    inactives = []
    text = ''

    for i in box_scores:
        inactives += scan_inactives(i.home_lineup, i.home_team, users, emotes)
        inactives += scan_inactives(i.away_lineup, i.away_team, users, emotes)

    if not inactives:
        return ('')

    text = ['#q##u##b#Inactive Players#b##u# '] + inactives

    return '\n'.join(text)


def scan_roster(lineup, team, warning, emotes):
    """
    Retrieve a list of players from a given fantasy football league that have a status.

    Parameters
    ----------
    lineup : list
        A list of player objects that represents the lineup
    team : object
        The team object for which to retrieve the monitor players
    warning : int
        The threshold at which to warn an owner to replace a player
    emotes : list
        A list of the server's team emotes

    Returns
    -------
    list
        A list of strings containing the list of players to monitor, formatted as a list of player names and statuses.
    """

    count = 0
    players = []
    for i in lineup:
        # exclude bench and injured players and active or normal players
        if i.slot_position != 'BE' and i.slot_position != 'IR' \
            and i.position not in ['D/ST', 'P']:
            
            if i.injuryStatus != 'ACTIVE' and i.injuryStatus != 'NORMAL' \
                and i.game_played == 0:

                count += 1
                player = i.position + ' ' + i.name + ' - ' + '#b#' + i.injuryStatus.title().replace('_', ' ') + '#b#'
                players += [player]

            elif i.on_bye_week:
                # espn_api leaves game_played at 100 for a bye (it is only set
                # for players whose pro team has a game that week), so neither
                # the injury rule above nor the projection rule below can catch
                # these -- a bye needs its own branch.
                count += 1
                player = i.position + ' ' + i.name + ' - #b#BYE#b#'
                players += [player]

            elif i.projected_points <= warning and i.game_played == 0:
                count += 1
                player = i.position + ' ' + i.name + '#b#' + str(i.projected_points) + ' pts#b#'
                players += [player]

        if i.slot_position == 'IR' and \
            i.injuryStatus != 'INJURY_RESERVE' and i.injuryStatus != 'OUT':

            count += 1
            player = i.position + ' ' + i.name + ' - #b#Not IR eligible#b#, ' + str(i.projected_points) + ' pts'
            players += [player]
                
    list = ""
    report = ""

    for p in players:
        list += "* " + p + "\n"

    if count > 0:
        s = '%s#b#%s#b# - #b#%d#b#: \n%s \n' % (emotes[team.team_id], team.team_name, count, list[:-1])
        report =  [s.lstrip()]

    return report


def scan_inactives(lineup, team, users, emotes):
    """
    Retrieve a list of players from a given fantasy football league that have a status that indicates they're not playing 
    or if a player is on a team's IR but is eligible for play.

    Parameters
    ----------
    lineup : list
        A list of player objects that represents the lineup
    team : object
        The team object for which to retrieve the inactive players
    users : list
        A list of the server's user tags

    Returns
    -------
    list
        A list of strings containing the list of inactive, formatted as a list of player names and statuses.
    """

    count = 0
    players = []
    for i in lineup:
        if i.game_played <= 0:
            if i.slot_position != 'BE' and i.slot_position != 'IR' and i.position != 'P':
                if i.on_bye_week:
                    count +=1
                    if i.position == 'D/ST':
                        players += ['%s - #b#BYE#b#' % (i.name)]
                    else:
                        players += ['%s %s - #b#BYE#b#' % (i.position, i.name)]
                elif i.game_played == 0 and (i.injuryStatus in ['OUT, DOUBTFUL, INJURY_RESERVE'] or i.projected_points <= 0):
                    count +=1
                    players += ['%s %s - #b#%s#b#, %d pts' % (i.position, i.name, i.injuryStatus.title().replace('_', ' '), i.projected_points)]

            if i.slot_position == 'IR' and \
                i.injuryStatus not in ['INJURY_RESERVE', 'OUT']:

                count += 1
                players += ['%s %s - #b#Not on IR#b#, %d pts' % (i.position, i.name, i.projected_points)]

    inactive_list = ""
    inactives = ""

    for p in players:
        inactive_list += "#p# " + p + "\n"

    if count > 0:
        inactives = ['%s%s#b#%s#b# - #b#%d#b#: \n%s \n' % (users[team.team_id], emotes[team.team_id], team.team_name, count, inactive_list[:-1])]
    
    return inactives


def get_matchups(league, week=None, box_scores=None):
    """
    Retrieve the matchups for a given week in a fantasy football league.

    Parameters
    ----------
    league: object
        The league object for which to retrieve the matchups.
    week : int, optional
        The week number for which to retrieve the matchups, by default None.
    box_scores: list, optional
        Pre-fetched box scores for the same week, to avoid a duplicate API call.

    Returns
    -------
    str
        A string containing the matchups for the given week, formatted as a list of team names and abbreviation.
    """

    emotes = env_vars.split_emotes(league)
    if box_scores is None:
        box_scores = fetch_box_scores(league, week=week)
    matchups = box_scores

    if not any(i.away_team for i in matchups):
        # Nothing to pair up: every slot is a bye, or the week has no data.
        return util.NO_MATCHUP_DATA

    played = [i for i in matchups if i.away_team]

    full_names = ['%s#b#%s#b# vs %s#b#%s#b#' % (emotes[i.home_team.team_id], i.home_team.team_name, emotes[i.away_team.team_id], i.away_team.team_name) for i in played]

    # Every record in the message is padded against the widest one, home and
    # away together, so the "vs" and the away abbreviation stay in one column.
    records = util.align_records(
        [f"{team.wins}-{team.losses}" for i in played for team in (i.home_team, i.away_team)])
    abbrevs = ['%4s (%s) vs (%s) %s' % (i.home_team.team_abbrev, home, away, i.away_team.team_abbrev)
               for i, home, away in zip(played, records[::2], records[1::2])]

    text = ['#q##u##b#Matchups#b##u# '] + full_names + [''] + abbrevs

    return '\n'.join(text)


def get_close_scores(league, week=None, box_scores=None, threshold=CLOSE_SCORES_DEFAULT_THRESHOLD):
    """
    Retrieve the projected closest scores (10.999 points or closer) for a given week in a fantasy football league.

    Parameters
    ----------
    league: object
        The league object for which to retrieve the closest scores.
    week : int, optional
        The week number for which to retrieve the closest scores, by default None.
    box_scores: list, optional
        Pre-fetched box scores for the same week, to avoid a duplicate API call.
    threshold : int, optional
        Largest projected point difference a matchup can have and still be
        reported as close. Defaults to CLOSE_SCORES_DEFAULT_THRESHOLD; set the
        CLOSE_SCORES_THRESHOLD environment variable to change it.

    Returns
    -------
    str
        A string containing the projected closest scores for the given week, formatted as a list of team names and abbreviation.
    """

    emotes = env_vars.split_emotes(league)
    if box_scores is None:
        box_scores = fetch_box_scores(league, week=week)
    score = []

    for i in box_scores:
        if i.away_team:
            away_projected = get_projected_total(i.away_lineup)
            home_projected = get_projected_total(i.home_lineup)
            diffScore = away_projected - home_projected

            if (abs(diffScore) <= threshold and (not all_played(i.away_lineup) or not all_played(i.home_lineup))):
                # Print the lineup-derived projections, the same numbers the
                # margin above was measured from. i.home_projected /
                # i.away_projected are the BoxScore's own totals, which are
                # matchup-period aggregates during a 2-week playoff matchup --
                # so the printed gap could disagree with the threshold that
                # selected this matchup in the first place.
                score += ['%s#c#%4s %6.2f - %6.2f %4s#c#%s' % (emotes[i.home_team.team_id], i.home_team.team_abbrev, home_projected,
                                                    away_projected, i.away_team.team_abbrev, emotes[i.away_team.team_id])]

    if not score:
        return('')
    text = ['#q##u##b#Projected Close Scores#b##u#'] + score
    return '\n'.join(text)


def transaction_date(txn):
    """
    Return the date ESPN stamped on a transaction, as 'YYYY-MM-DD'.

    Parameters
    ----------
    txn : object
        An espn_api Transaction.

    Returns
    -------
    str or None
        The date string, or None when the transaction carries no timestamp, so
        that it can never match a report date.
    """
    timestamp = getattr(txn, 'date', None)
    if not timestamp:
        return None
    return date.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')


def waiver_player_positions(league, transactions, today):
    """
    Map {playerId: position} for the players in a day's executed waiver claims.

    league.player_info costs one request per call, and the report wants a
    position for every add and every drop -- N requests for an N-move waiver
    day, every day, for one field per player. espn_api accepts a list of ids
    and resolves them in a single player-card request, so one batched call
    replaces all of them.

    Parameters
    ----------
    league : object
        The league object the transactions belong to.
    transactions : list
        The transactions returned for the scoring period.
    today : str
        The report date, as 'YYYY-MM-DD'.

    Returns
    -------
    dict
        playerId to position. Ids ESPN does not resolve are simply absent, and
        callers fall back to 'N/A'.
    """
    player_ids = []
    for txn in transactions:
        if getattr(txn, 'status', None) != TXN_STATUS_EXECUTED:
            continue
        if transaction_date(txn) != today:
            continue
        for item in getattr(txn, 'items', []):
            player_id = getattr(item, 'playerId', None)
            if player_id is not None and player_id not in player_ids:
                player_ids.append(player_id)

    positions = {}
    for start in range(0, len(player_ids), PLAYER_CARD_BATCH):
        chunk = player_ids[start:start + PLAYER_CARD_BATCH]
        try:
            found = league.player_info(playerId=chunk)
        except Exception:
            # A failed lookup costs this chunk its positions ('N/A') rather
            # than failing the whole daily report.
            logger.warning('Could not resolve waiver player positions for %s', chunk, exc_info=True)
            continue
        if found is None:
            continue
        # Keyed off each returned Player's own playerId rather than by zipping
        # against the request: espn_api does not guarantee response order and
        # omits ids it cannot resolve.
        for player in (found if isinstance(found, list) else [found]):
            player_id = getattr(player, 'playerId', None)
            position = getattr(player, 'position', None)
            if player_id is not None and position:
                positions[player_id] = position
    return positions


def get_waiver_report(league, faab=False, scoring_period=None, test_date=None):
    """
    Generate a waiver report for a given league and scoring period.

    The report lists all waiver transactions that occurred on the specified date (defaults to today),
    including the team that made the transaction, the player(s) added, and the player(s) dropped (if applicable).
    If faab is True, the report will include FAAB amount spent and will be sorted from largest to smallest FAAB bid.

    Parameters
    ----------
    league : object
        The league object for which the report is being generated.
    faab : bool, optional
        If True, include FAAB amount spent and sort report by FAAB descending. Defaults to False.
    scoring_period : int, optional
        The scoring period to query transactions for. Defaults to league.scoringPeriodId.
    test_date : str, optional
        Date string (YYYY-MM-DD) to simulate 'today' for testing historical transactions. Defaults to current date.

    Returns
    -------
    str
        A formatted string containing the waiver report.
    """


    # Allow testing with a specific scoring period and date
    if scoring_period is None:
        scoring_period = league.scoringPeriodId

    try:
        # WAIVER_ERROR comes along so the losing claims on a contested player
        # are available for the outbid callout below. Only EXECUTED claims are
        # ever reported.
        transactions = league.transactions(scoring_period, types={'WAIVER', 'WAIVER_ERROR'})
    except Exception as exc:
        # espn_api raises instead of returning an empty list when a scoring
        # period has no transactions at all (league.py: `raise Exception('No
        # transactions found')`). This report runs every day, so a quiet waiver
        # wire is the normal case, not a failure -- and an empty report is not
        # worth messaging anyone about. Matching on the message is unpleasant,
        # but espn_api raises a bare Exception so there is no type to catch.
        # Anything else -- auth, a 5xx, a genuine outage -- must still surface.
        if 'No transactions found' not in str(exc):
            raise
        logger.info('No transactions for scoring period %s; nothing to report', scoring_period)
        return ''

    today = test_date if test_date else date.today().strftime('%Y-%m-%d')

    # Losing claims are used only to find each contested add's runner-up (best
    # losing) bid on the same player, so the report can say what the winner had
    # to beat. Keyed by playerId rather than the resolved name, since espn_api
    # maps ids it cannot resolve to the literal 'Unknown'.
    runner_ups = {}  # playerId -> (bid, team_name)
    for txn in transactions:
        if getattr(txn, 'status', None) == TXN_STATUS_EXECUTED:
            continue
        if transaction_date(txn) != today:
            continue
        bid = getattr(txn, 'bid_amount', None)
        if bid is None:
            continue
        team_name = getattr(getattr(txn, 'team', None), 'team_name', None)
        for item in getattr(txn, 'items', []):
            if getattr(item, 'type', None) != TXN_ITEM_ADD:
                continue
            player_id = getattr(item, 'playerId', None)
            if player_id is None:
                continue
            existing = runner_ups.get(player_id)
            if existing is None or bid > existing[0]:
                runner_ups[player_id] = (bid, team_name)

    positions = waiver_player_positions(league, transactions, today)

    entries = []  # (faab_amount, formatted block)
    for txn in transactions:
        # Only include transactions matching the report date that went through
        if transaction_date(txn) != today or txn.status != TXN_STATUS_EXECUTED:
            continue
        team_name = txn.team.team_name
        # espn_api always sets bid_amount but leaves it None for a non-FAAB
        # claim, which would render "$None" and break the descending sort.
        faab_amount = getattr(txn, 'bid_amount', None) or 0

        # Adds and drops are collected separately rather than in item order, so
        # every ADDED line precedes every DROPPED line in the rendered block.
        adds, drops = [], []
        for item in txn.items:
            # 'N/A' when ESPN did not resolve the id; league.player_info
            # returns None for those and None.position would crash the report.
            position = positions.get(getattr(item, 'playerId', None), 'N/A')
            if item.type == TXN_ITEM_DROP:
                drops.append(f"#p# DROPPED {position} - {item.player}")
            elif item.type == TXN_ITEM_ADD:
                if not faab:
                    adds.append(f"#p# ADDED {position} - {item.player}")
                    continue
                # Only a *rival's* losing bid is competition: a team that also
                # outbid its own failed claim on the same player beat nobody.
                runner_up = runner_ups.get(getattr(item, 'playerId', None))
                if runner_up and runner_up[1] == team_name:
                    runner_up = None
                callout = util.faab_bid_callout(
                    faab_amount,
                    runner_up[0] if runner_up else None,
                    runner_up[1] if runner_up else None,
                )
                adds.append(f"#p# ADDED {position} - {item.player} (${faab_amount}{callout})")

        block = f"{team_name} \n" + ''.join(f"{move}\n" for move in adds + drops)
        if faab:
            entries.append((faab_amount, block.lstrip()))
        else:
            entries.append((datetime.fromtimestamp(txn.date / 1000), block.lstrip()))

    if faab:
        # Sort by faab_amount descending
        entries.sort(key=lambda entry: entry[0], reverse=True)
    else:
        # Sort by time executed
        entries.sort(key=lambda x: x[0])
        entries = [item[1] for item in entries]

    # Only return a report if there are transactions
    if not entries:
        return ''

    return '\n'.join([f'#q##u##b#Waiver Report {today}#b##u#'] + [block for _, block in entries])


def combined_power_rankings(league, week=None):
    """
    This function returns the power rankings of the teams in the league for a specific week,
    along with the change in power ranking number and playoff percentage from the previous week.
    If the week is not provided, it defaults to the current week.
    The power rankings are determined using a 2 step dominance algorithm,
    as well as a combination of points scored and margin of victory.
    It's weighted 80/15/5 respectively.

    Parameters
    ----------
    league: object
        The league object for which the power rankings are being generated
    week : int, optional
        The week for which the power rankings are to be returned (default is current week)

    Returns
    -------
    str
        A string representing the power rankings with changes from the previous week, playoff chance, and simulated records
    """

    emotes = env_vars.split_emotes(league)

    # Check if the week is provided, if not use the previous week
    if not week:
        week = league.current_week - 1

    is_playoffs = False
    if week > league.settings.reg_season_count:
        is_playoffs = True

    p_rank_up_emoji = "🟢"
    p_rank_down_emoji = "🔻"
    p_rank_same_emoji = "🟰"

    # Get the power rankings for the previous 2 weeks
    current_rankings = league.power_rankings(week=week)
    previous_rankings = league.power_rankings(week=week-1) if week > 1 else []

    # Normalize the scores
    def normalize_rankings(rankings):
        if not rankings:
            return []
        max_score = max(float(score) for score, _ in rankings)
        try:
            normalized = [(f"{99.99 * float(score) / max_score:.2f}", team) for score, team in rankings]
        except ZeroDivisionError:
            normalized = [(f"{99.99 * float(score)}", team) for score, team in rankings]
        return normalized
    
    normalized_current_rankings = normalize_rankings(current_rankings)
    normalized_previous_rankings = normalize_rankings(previous_rankings)

    # Convert normalized previous rankings to a dictionary for easy lookup
    previous_rankings_dict = {team.team_abbrev: score for score, team in normalized_previous_rankings}

    sr = sim_record(league, week)

    # Prepare the output string
    title = '#q##u##b#Power Rankings#b##u#'
    if (is_playoffs):
        rankings_text = [title + ' PR Pts (%Δ) [Sim Record]']
    else:
        rankings_text = [title + ' PR Pts (%Δ) [PO Chance | Sim Record]']

    pos = 1
    for normalized_current_score, current_team in normalized_current_rankings:
        team_abbrev = current_team.team_abbrev
        rank_change_text = ''

        # Check if the team was present in the normalized previous rankings
        if team_abbrev in previous_rankings_dict:
            previous_score = previous_rankings_dict[team_abbrev]
            rank_change_percent = ((float(normalized_current_score) - float(previous_score)) / float(previous_score)) * 100
            rank_change_emoji = p_rank_up_emoji if rank_change_percent > 0 else p_rank_down_emoji if rank_change_percent < 0 else p_rank_same_emoji
            rank_change_text = f" ({rank_change_emoji} {abs(rank_change_percent):4.1f}%)"

        formatted_pos = '%2s' % pos
        if (is_playoffs):
            s = '%2s: %s #c#%4s: %s%-2s [%s]#c#' % (
                formatted_pos.replace(' ', '\u2002'), 
                emotes[current_team.team_id], 
                current_team.team_abbrev, 
                normalized_current_score, 
                rank_change_text, 
                sr[current_team][0])
        else:
            s = '%2s: %s #c#%4s: %s%-2s [%4.1f%% | %s]#c#' % (
                formatted_pos.replace(' ', '\u2002'), 
                emotes[current_team.team_id], 
                current_team.team_abbrev, 
                normalized_current_score, 
                rank_change_text, 
                current_team.playoff_pct, 
                sr[current_team][0])

        rankings_text.append(s)
        pos += 1
    
    return '\n'.join(rankings_text)


def sim_record(league, week=None):
    """
    This function takes in a league object and an optional week parameter. It then iterates through each result each week and determines what the records of each team would be had they faced every other team through each week of the season.

    Parameters:
    league (object): A league object containing information about the league and its teams.
    week (int, optional): The week for which the box scores should be retrieved. If no week is specified, the current week will be used.

    Returns:
    list: A list containing the head-to-head records for the week.
    """

    if not week:
        week = league.current_week - 1

    records = {}
    weekly_records = {}

    for t in league.teams:
        records[t] = ''
        weekly_records[t] = [0,0,0]

    for i in range(week):
        weekNumber = i+1
        box_scores = league.box_scores(weekNumber)
        weekly_scores = {}
        for i in box_scores: 
            if i.home_team != 0 and i.away_team != 0:
                weekly_scores[i.home_team] = [i.home_score]
                weekly_scores[i.away_team] = [i.away_score]

        for i in weekly_scores:
            for j in weekly_scores:
                if i != j:
                    if weekly_scores[i][0] > weekly_scores[j][0]:
                        weekly_records[i][0] += 1
                    elif weekly_scores[i][0] < weekly_scores[j][0]:
                        weekly_records[i][1] += 1
                    else: # Just in case of a tie
                        weekly_records[i][2] += 1
            
    for r in weekly_records:
        if weekly_records[r][2] > 0:
            records[r] = ['%s-%s-%s' % (weekly_records[r][0], weekly_records[r][1], weekly_records[r][2])]
        else:
            records[r] = ['%s-%s' % (weekly_records[r][0], weekly_records[r][1])]

    return (records)


def is_bye_box(box):
    """
    Check whether a box score is a bye, meaning one side has no team.

    espn_api sets the missing side's team to None (older versions used 0), and
    Matchup objects from scoreboard() never assign the attribute at all. The
    team that is present played nobody that week, so it takes part in no
    head-to-head trophy.

    This matters beyond the regular season: playoff weeks routinely carry byes
    for the top seeds, and a `team != 0` check lets a None team through, since
    None != 0 is True.

    Parameters
    ----------
    box : object
        A box score representing a single matchup.

    Returns
    -------
    bool
        True when either side of the matchup is missing.
    """
    return not getattr(box, 'home_team', None) or not getattr(box, 'away_team', None)


def get_starter_counts(league):
    """
    Get the number of starters for each position

    Parameters
    ----------
    league : object
        The league object for which the starter counts are being generated

    Returns
    -------
    dict
        A dictionary containing the number of players at each position within the starting lineup.
    """

    return {pos: cnt for pos, cnt in league.settings.position_slot_counts.items() if pos not in ['BE', 'IR'] and cnt != 0}


def best_flex(flexes, player_pool, num):
    """
    Given a list of flex positions, a dictionary of player pool, and a number of players to return,
    this function returns the best flex players from the player pool.

    Parameters
    ----------
    flexes : list
        a list of strings representing the flex positions
    player_pool : dict
        a dictionary with keys as position and values as a dictionary with player name as key and value as score
    num : int
        number of players to return from the player pool

    Returns
    ----------
    best : dict
        a dictionary containing the best flex players from the player pool
    player_pool : dict
        the updated player pool after removing the best flex players
    """

    pool = {}
    # iterate through each flex position
    for flex_position in flexes:
        # add players from flex position to the pool
        try:
            pool = pool | player_pool[flex_position]
        except KeyError:
            pass
    # sort the pool by score in descending order
    pool = {k: v for k, v in sorted(pool.items(), key=lambda item: item[1], reverse=True)}
    # get the top num players from the pool
    best = dict(list(pool.items())[:num])
    # remove the best flex players from the player pool
    for pos in player_pool:
        for p in best:
            if p in player_pool[pos]:
                player_pool[pos].pop(p)
    return best, player_pool


def optimal_lineup_score(lineup, starter_counts):
    """
    This function returns the optimal lineup score based on the provided lineup and starter counts.

    Parameters
    ----------
    lineup : list
        A list of player objects for which the optimal lineup score is being generated
    starter_counts : dict
        A dictionary containing the number of starters for each position

    Returns
    -------
    tuple
        A tuple containing the optimal lineup score, the provided lineup score, the difference between the two scores,
        and the percentage of the provided lineup's score compared to the optimal lineup's score.
    """

    best_lineup = {}
    position_players = {}

    # get all players and points
    score = 0
    score_pct = 0
    best_score = 0

    for player in lineup:
        if player.slot_position == 'IR':
            # An IR-slotted player cannot legally be started, so they are never
            # a candidate for the optimal lineup. Bench players still are.
            # Counting them inflates the optimal score and so understates every
            # manager's percentage of it.
            continue
        try:
            position_players[player.position][player.name] = player.points
        except KeyError:
            position_players[player.position] = {}
            position_players[player.position][player.name] = player.points
        if player.slot_position != 'BE':
            score += player.points

    # sort players by position for points
    for position in starter_counts:
        try:
            position_players[position] = {k: v for k, v in sorted(
                position_players[position].items(), key=lambda item: item[1], reverse=True)}
            best_lineup[position] = dict(list(position_players[position].items())[:starter_counts[position]])
            position_players[position] = dict(list(position_players[position].items())[starter_counts[position]:])
        except KeyError:
            best_lineup[position] = {}

    # flexes. need to figure out best in other single positions first
    for position in starter_counts:
        # flex
        if 'D/ST' not in position and '/' in position:
            flex = position.split('/')
            result = best_flex(flex, position_players, starter_counts[position])
            best_lineup[position] = result[0]
            position_players = result[1]

    # Offensive Player. need to figure out best in other positions first
    if 'OP' in starter_counts:
        flex = ['RB', 'WR', 'TE', 'QB']
        result = best_flex(flex, position_players, starter_counts['OP'])
        best_lineup['OP'] = result[0]
        position_players = result[1]

    # Defensive Line flex (DT/DE). Resolve before the wider DP flex below, so
    # DP does not take a lineman that DL was going to need.
    if 'DL' in starter_counts:
        flex = ['DT', 'DE']
        result = best_flex(flex, position_players, starter_counts['DL'])
        best_lineup['DL'] = result[0]
        position_players = result[1]

    # Defensive Back flex (CB/S). Resolve before the wider DP flex, for the
    # same reason as DL above.
    if 'DB' in starter_counts:
        flex = ['CB', 'S']
        result = best_flex(flex, position_players, starter_counts['DB'])
        best_lineup['DB'] = result[0]
        position_players = result[1]

    # Defensive Player. need to figure out best in other positions first
    if 'DP' in starter_counts:
        flex = ['DT', 'DE', 'LB', 'CB', 'S']
        result = best_flex(flex, position_players, starter_counts['DP'])
        best_lineup['DP'] = result[0]
        position_players = result[1]

    for position in best_lineup:
        best_score += sum(best_lineup[position].values())

    score_pct = 0
    if best_score != 0:
        score_pct = (score / best_score) * 100

    return (best_score, score, best_score - score, score_pct)


def optimal_team_scores(league, week=None):
    """
    This function returns the optimal team scores or managers.

    Parameters
    ----------
    league : object
        The league object for which the optimal team scores are being generated
    week : int, optional
        The week for which the optimal team scores are to be returned (default is the previous week)

    Returns
    -------
    str 
        A string representing the full report of the optimal team scores.
    """

    emotes = env_vars.split_emotes(league)
    if not week:
        if league.scoringPeriodId > league.finalScoringPeriod:
            week = league.finalScoringPeriod
        else: 
            week = league.current_week - 1
            
    box_scores = league.box_scores(week=week)
    results = []
    best_scores = {}
    starter_counts = get_starter_counts(league)

    for i in box_scores:
        if is_bye_box(i):
            continue
        best_scores[i.home_team] = optimal_lineup_score(i.home_lineup, starter_counts)
        best_scores[i.away_team] = optimal_lineup_score(i.away_lineup, starter_counts)

    best_scores = {key: value for key, value in sorted(best_scores.items(), key=lambda item: item[1][3], reverse=True)}

    i = 1
    for score in best_scores:
        formatted_pos = '%2s' % i
        s = ['%2s: %s #c#%4s: %6.2f [%6.2f - %.2f%%]#c#' %
                (formatted_pos.replace(' ', '\u2002'), emotes[score.team_id], score.team_abbrev, best_scores[score][0],
                best_scores[score][1], best_scores[score][3])]
        results += s
        i += 1

    if not results:
        return ('')

    text = ['#q##u##b#Best Possible Scores#b##u#  [Actual - % of optimal]'] + results + ['\u200e']
    return '\n'.join(text)


def get_achievers_trophy(league, low_team_id, high_team_id, week=None):
    """
    This function returns the overachiever and underachiever of the league
    based on the difference between the projected score and the actual score,
    only if the over/under achievers are not the same as the highest/lowest scorers, respectively.

    Parameters
    ----------
    league: object
        The league object for which the overachiever and underachiever are being determined
    week : int, optional
        The week for which the overachiever and underachiever are to be returned (default is current week)
    box_scores : list, optional
        Pre-fetched box scores for the same week, to avoid a duplicate API call.

    Returns
    -------
    str
        A string representing the overachiever and underachiever of the league
    """

    box_scores = league.box_scores(week=week)
    emotes = env_vars.split_emotes(league)
    achiever_str = []
    best_performance = -9999
    worst_performance = 9999
    over_achiever = None
    under_achiever = None
    for i in box_scores:
        if is_bye_box(i):
            continue
        home_performance = i.home_score - i.home_projected
        away_performance = i.away_score - i.away_projected

        if home_performance > best_performance:
            best_performance = home_performance
            over_achiever = i.home_team
        if home_performance < worst_performance:
            worst_performance = home_performance
            under_achiever = i.home_team
        if away_performance > best_performance:
            best_performance = away_performance
            over_achiever = i.away_team
        if away_performance < worst_performance:
            worst_performance = away_performance
            under_achiever = i.away_team

    if best_performance > 0 and over_achiever.team_id != high_team_id:
        achiever_str += ['📈 #c#Overachiever:#c# %s \n#p# #b#%s#b# was %.2f points over their projection' % (emotes[over_achiever.team_id], over_achiever.team_name, best_performance)]

    if worst_performance < 0 and under_achiever.team_id != low_team_id:
        achiever_str += ['📉 #c#Underachiever:#c# %s \n#p# #b#%s#b# was %.2f points under their projection' % (emotes[under_achiever.team_id], under_achiever.team_name, abs(worst_performance))]

    return achiever_str


def get_weekly_score_with_win_loss(league, week=None, box_scores=None):
    if box_scores is None:
        box_scores = fetch_box_scores(league, week=week)
    weekly_scores = {}
    for i in box_scores:
        # A bye has no result to record. The old `!= 0` test let a None team
        # through and put None in this dict as a key, which then blew up in
        # every caller that read `.team_abbrev` off it.
        if is_bye_box(i):
            continue
        if i.home_score > i.away_score:
            weekly_scores[i.home_team] = [i.home_score, 'W']
            weekly_scores[i.away_team] = [i.away_score, 'L']
        else:
            weekly_scores[i.home_team] = [i.home_score, 'L']
            weekly_scores[i.away_team] = [i.away_score, 'W']
    return dict(sorted(weekly_scores.items(), key=lambda item: item[1], reverse=True))


def get_lucky_trophy(league, week=None):
    """
    This function takes in a league object and an optional week parameter. It retrieves the box scores for the specified league and week, and creates a dictionary with the weekly scores for each team. The teams are sorted in descending order by their scores, and the team with the lowest score and won is determined to be the lucky team for the week. The team with the highest score and lost is determined to be the unlucky team for the week. The function returns a list containing the lucky and unlucky teams, along with their records for the week.
    Parameters:
    league (object): A league object containing information about the league and its teams.
    week (int, optional): The week for which the box scores should be retrieved. If no week is specified, the current week will be used.
    box_scores (list, optional): Pre-fetched box scores for the same week, to avoid a duplicate API call.
    Returns:
    list: A list containing the lucky and unlucky teams, along with their records for the week.
    """

    weekly_scores = get_weekly_score_with_win_loss(league, week=week)
    emotes = env_vars.split_emotes(league)
    losses = 0
    unlucky_team = None
    lucky_team = None
    unlucky_record = ''
    lucky_record = ''
    num_teams = len(weekly_scores) - 1

    for t in weekly_scores:
        if weekly_scores[t][1] == 'L':
            unlucky_team = t
            unlucky_record = str(num_teams - losses) + '-' + str(losses)
            break
        losses += 1

    wins = 0
    weekly_scores = dict(sorted(weekly_scores.items(), key=lambda item: item[1]))
    for t in weekly_scores:
        if weekly_scores[t][1] == 'W':
            lucky_team = t
            lucky_record = str(wins) + '-' + str(num_teams - wins)
            break
        wins += 1


    lucky_str = ['🍀 #c#Lucky:#c# %s \n#p# #b#%s#b# was %s against the league, but got the win' % (emotes[lucky_team.team_id], lucky_team.team_name, lucky_record)]
    unlucky_str = ['💀 #c#Unlucky:#c# %s \n#p# #b#%s#b# was %s against the league, but still took an L' % (emotes[unlucky_team.team_id], unlucky_team.team_name, unlucky_record)]
    return (lucky_str + unlucky_str)


def get_mvp_trophy(league, week=None):
    """
    This function returns the weekly most valuable and least valuable players,
    determined by algorithm of: (actual score - projected score)/projected score

    Parameters
    ----------
    league: object
        The league object for which the MVP and LVP are being determined
    week : int, optional
        The week for which the MVP and LVP are to be returned (default is current week)

    Returns
    -------
    str
        A string representing the MVP an LVP of the league
    """

    emotes = env_vars.split_emotes(league)

    players = get_player_achievers(league, week=week, return_number=1)

    best = players[0][0]
    worst = players[1][0]

    mvp_score = f"{best['points']} points ({best['projected']} proj, {best['proj_diff']} diff ratio)"
    lvp_score = f"{worst['points']} points ({worst['projected']} proj, {worst['proj_diff']} diff ratio)"

    mvp_str = ['👍 #c#Week MVP:#c# %s \n#p# %s %s, #b#%s#b# with %s' % (emotes[best['fantasy_team'].team_id], best['position'], best['name'], best['fantasy_team'].team_abbrev, mvp_score)]
    lvp_str = ['👎 #c#Week LVP:#c# %s \n#p# %s %s, #b#%s#b# with %s' % (emotes[worst['fantasy_team'].team_id], worst['position'], worst['name'], worst['fantasy_team'].team_abbrev, lvp_score)]
    return (mvp_str + lvp_str)


def get_trophies(league, extra_trophies, week=None, box_scores=None):
    """
    Returns trophies for the highest score, lowest score, closest score, and biggest win.

    Parameters
    ----------
    league : object
        The league object for which the trophies are to be returned
    week : int, optional
        The week for which the trophies are to be returned (default is current week)
    box_scores : list, optional
        Pre-fetched box scores for the same week, to avoid a duplicate API call.
        Also passed on to the lucky, achiever and optimal-lineup trophies, so
        the whole trophy set costs a single box_scores call.

    Returns
    -------
    str
        A string representing the trophies
    """
    if not week:
        week = league.current_week - 1

    emotes = env_vars.split_emotes(league)
    if box_scores is None:
        box_scores = fetch_box_scores(league)
    matchups = box_scores

    low_score = 9999
    low_team = -1

    high_score = -1
    high_team = -1

    closest_score = 9999
    close_winner = -1
    close_loser = -1
    close_emotes = ''

    biggest_blowout = -1
    blown_out_team = -1
    ownerer_team = -1
    blowout_emotes = ''

    for i in matchups:
        if i.home_score > high_score:
            high_score = i.home_score
            high_team = i.home_team
        if i.home_score < low_score:
            low_score = i.home_score
            low_team = i.home_team
        if i.away_score > high_score:
            high_score = i.away_score
            high_team = i.away_team
        if i.away_score < low_score:
            low_score = i.away_score
            low_team = i.away_team

        if i.away_score - i.home_score != 0 and \
            abs(i.away_score - i.home_score) < closest_score:
            closest_score = abs(i.away_score - i.home_score)
            if i.away_score - i.home_score < 0:
                close_winner = i.home_team
                close_loser = i.away_team
            else:
                close_winner = i.away_team
                close_loser = i.home_team

        if abs(i.away_score - i.home_score) > biggest_blowout:
            biggest_blowout = abs(i.away_score - i.home_score)
            if i.away_score - i.home_score < 0:
                ownerer_team = i.home_team
                blown_out_team = i.away_team
            else:
                ownerer_team = i.away_team
                blown_out_team = i.home_team
        
        if emotes[1]:
            close_emotes = '%s> %s' % (emotes[close_winner.team_id], emotes[close_loser.team_id])
            blowout_emotes = '%s< %s' % (emotes[blown_out_team.team_id], emotes[ownerer_team.team_id])
        

    high_score_str = ['👑 #c#Highest score:#c# %s \n#p# #b#%s#b# with %.2f points' % (emotes[high_team.team_id], high_team.team_name, high_score)]
    low_score_str = ['💩 #c#Lowest score:#c# %s \n#p# #b#%s#b# with %.2f points' % (emotes[low_team.team_id], low_team.team_name, low_score)]
    close_score_str = ['🧊 #c#Closest Win:#c# %s \n#p# #b#%s#b# barely beat #b#%s#b# by a margin of %.2f' % (close_emotes, close_winner.team_name, close_loser.team_name, closest_score)]
    blowout_str = ['💥 #c#Biggest Loss:#c# %s \n#p# #b#%s#b# got blown out by #b#%s#b# by a margin of %.2f' % (blowout_emotes, blown_out_team.team_name, ownerer_team.team_name, biggest_blowout)]

    text = ['#q##u##b#Trophies of the week#b##u# '] + high_score_str + low_score_str + close_score_str + blowout_str

    if extra_trophies == True:
        text += get_achievers_trophy(league, low_team.team_id, high_team.team_id, week) + get_lucky_trophy(league, week) + get_mvp_trophy(league, week)

    return '\n'.join(text)


def get_player_achievers(league, week=None, return_number=2):
    """
    Returns the top and bottom N players who exceeded or fell short of their projection the most in starting lineups for the given week.
    """
    if not week:
        week = league.current_week - 1
    box_scores = fetch_box_scores(league, week=week)
    player_diffs = []
    for matchup in box_scores:
        for team, team_lineup in zip([matchup.home_team, matchup.away_team], [matchup.home_lineup, matchup.away_lineup]):
            for player in team_lineup:
                if player.slot_position not in ['BE', 'IR'] and hasattr(player, 'projected_points') and player.projected_points is not None and player.position != 'D/ST':
                    diff = round(player.points - player.projected_points, 2)
                    proj_diff = round(diff/player.projected_points, 2) if player.projected_points != 0 else 0
                    player_diffs.append({
                        'name': player.name,
                        'team': player.proTeam if hasattr(player, 'proTeam') else '',
                        'position': player.position,
                        'fantasy_team': team if team else None,
                        'points': player.points,
                        'projected': player.projected_points,
                        'diff': diff,
                        'proj_diff': proj_diff
                    })
    sorted_diffs = sorted(player_diffs, key=lambda x: x['proj_diff'], reverse=True)
    best = sorted_diffs[:return_number]
    worst = sorted_diffs[-return_number:]
    return best, worst
