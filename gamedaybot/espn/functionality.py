from datetime import date
import gamedaybot.utils.util as util
import gamedaybot.espn.env_vars as env_vars

random_phrase = env_vars.get_random_phrase()

def get_scoreboard_short(league, week=None):
    """
    Retrieve the scoreboard for a given week of the fantasy football season.

    Parameters
    ----------
    league: espn_api.football.League
        The league for which to retrieve the scoreboard.
    week: int
        The week of the season for which to retrieve the scoreboard.

    Returns
    -------
    list of dict
        A list of dictionaries representing the games on the scoreboard for the given week. Each dictionary contains
        information about a single game, including the teams and their scores.
    """

    emotes = env_vars.split_emotes(league)
    box_scores = league.box_scores(week=week)
    score = ['%s#c#%4s %6.2f - %6.2f %4s#c# %s' % (emotes[i.home_team.team_id], i.home_team.team_abbrev, i.home_score,
                                    i.away_score, i.away_team.team_abbrev, emotes[i.away_team.team_id]) for i in box_scores
             if i.away_team]

    if week == league.current_week - 1:
        text = ['#u##b#Final Score Update#b##u# ']
    else:
        text = ['#u##b#Score Update#b##u#']
    
    text += score
    return '\n'.join(text)

def get_projected_scoreboard(league, week=None):
    emotes = env_vars.split_emotes(league)
    """
    Retrieve the projected scoreboard for a given week of the fantasy football season.

    Parameters
    ----------
    league: espn_api.football.League
        The league for which to retrieve the projected scoreboard.
    week: int
        The week of the season for which to retrieve the projected scoreboard.

    Returns
    -------
    list of dict
        A list of dictionaries representing the projected games on the scoreboard for the given week. Each dictionary
        contains information about a single game, including the teams and their projected scores.
    """

    box_scores = league.box_scores(week=week)
    score = ['%s#c#%4s %6.2f - %6.2f %4s#c# %s' % (emotes[i.home_team.team_id], i.home_team.team_abbrev, i.home_projected,
                                    i.away_projected, i.away_team.team_abbrev, emotes[i.away_team.team_id]) for i in box_scores
             if i.away_team]

    text = ['#u##b#Approximate Projected Scores#b##u#'] + score
    return '\n'.join(text)


def get_standings(league, top_half_scoring=False, week=None):
    """
    Retrieve the current standings for a fantasy football league, with an option to include top-half scoring.

    Parameters
    ----------
    league: object
        The league object for which to retrieve the standings.
    top_half_scoring: bool, optional
        If True, include top-half scoring in the standings calculation. Defaults to False.
    week: int, optional
        The week for which to retrieve the standings. Defaults to the current week of the league.

    Returns
    -------
    str
        A string containing the current standings, formatted as a list of teams with their records and positions.
    """

    emotes = env_vars.split_emotes(league)
    standings_txt = ''
    teams = league.teams
    standings = []
    if not top_half_scoring:
        standings = league.standings()
        standings_txt = [f"{pos + 1}: {emotes[team.team_id]}{team.team_name} ({team.wins}-{team.losses})" for \
            pos, team in enumerate(standings)]
    else:
        # top half scoring can be enabled by default in ESPN now.
        # this should generally not be used
        top_half_totals = {t.team_name: 0 for t in teams}
        if not week:
            week = league.current_week
        for w in range(1, week):
            top_half_totals = top_half_wins(league, top_half_totals, w)

        for t in teams:
            wins = top_half_totals[t.team_name] + t.wins
            standings.append((wins, t.losses, t.team_name, emotes[t.team_id]))

        standings = sorted(standings, key=lambda tup: tup[0], reverse=True)
        standings_txt = [f"{pos + 1}: {emote}{team_name} ({wins}-{losses}) (+{top_half_totals[team_name]})" for \
            pos, (wins, losses, team_name, emote) in enumerate(standings)]
        
    title = ['#u##b#Current Standings#b##u#']

    text = title + standings_txt + ['']
    return "\n".join(text)


def top_half_wins(league, top_half_totals, week):
    box_scores = league.box_scores(week=week)

    scores = [(i.home_score, i.home_team.team_name) for i in box_scores] + \
        [(i.away_score, i.away_team.team_name) for i in box_scores if i.away_team]

    scores = sorted(scores, key=lambda tup: tup[0], reverse=True)

    for i in range(0, len(scores) // 2):
        points, team_name = scores[i]
        top_half_totals[team_name] += 1

    return top_half_totals


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


def get_projected_final(lineup):
    final_projected = 0
    for i in lineup:
        if i.slot_position != 'BE' and i.slot_position != 'IR':
            final_projected += i.projected_points
    return final_projected


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


def get_monitor(league, warning):
    """
    Retrieve a list of players from a given fantasy football league that should be monitored during a game.

    Parameters
    ----------
    league: object
        The league object for which to retrieve the monitor players.

    Returns
    -------
    str
        A string containing the list of players to monitor, formatted as a list of player names and status.
    """

    emotes = env_vars.split_emotes(league)
    box_scores = league.box_scores()
    monitor = []
    text = ''

    for i in box_scores:
        monitor += scan_roster(i.home_lineup, i.home_team, warning, emotes)
        monitor += scan_roster(i.away_lineup, i.away_team, warning, emotes)
    
    if not monitor:
        return ('')
    
    text = ['#u##b#Players to Monitor#b##u# '] + monitor
    if random_phrase == True:
        text += util.get_random_phrase()
    
    return '\n'.join(text)


def get_inactives(league, week=None):
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
    box_scores = league.box_scores(week=week)
    inactives = []
    text = ''

    for i in box_scores:
        inactives += scan_inactives(i.home_lineup, i.home_team, users, emotes)
        inactives += scan_inactives(i.away_lineup, i.away_team, users, emotes)

    if not inactives:
        return ('')

    text = ['#u##b#Inactive Players#b##u# '] + inactives
    if random_phrase == True:
        text += util.get_random_phrase()

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
        if i.slot_position != 'BE' and i.slot_position != 'IR' and i.position not in ['D/ST', 'P']:
            if (i.pro_opponent == 'None') or (i.injuryStatus != 'ACTIVE' and i.injuryStatus != 'NORMAL') or (i.projected_points <= warning):
                count += 1
                player = i.position + ' ' + i.name + ' - '
                if i.pro_opponent == 'None':
                    player += '#b#BYE#b#'
                elif i.injuryStatus != 'ACTIVE' and i.injuryStatus != 'NORMAL':
                    player += '#b#' + i.injuryStatus.title().replace('_', ' ') + '#b#'
                elif i.projected_points <= warning:
                    player += '#b#' + str(i.projected_points) + ' pts#b#'
                players += [player]
        elif i.position == 'D/ST' and i.slot_position !='BE' and (i.pro_opponent == 'None' or i.projected_points <= warning):
            count += 1
            player = i.name + ' - '
            if i.pro_opponent == 'None':
                player += '#b#BYE#b#'
            elif i.projected_points <= warning:
                player += '#b#' + str(i.projected_points) + ' pts#b#'
            players += [player]
            
        if i.slot_position == 'IR' and \
            i.injuryStatus != 'INJURY_RESERVE' and i.injuryStatus != 'OUT':

            count += 1
            players += ['%s %s - #b#Not on IR#b#, %d pts' % (i.position, i.name, i.projected_points)]
                
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
        if i.slot_position != 'BE' and i.slot_position != 'IR' and i.position != 'P':
            if i.pro_opponent == 'None':
                count +=1
                if i.position == 'D/ST':
                    players += ['%s - #b#BYE#b#' % (i.name)]
                else:
                    players += ['%s %s - #b#BYE#b#' % (i.position, i.name)]
            elif i.game_played == 0 and (i.injuryStatus == 'OUT' or i.injuryStatus == 'DOUBTFUL' or i.projected_points <= 0):
                count +=1
                players += ['%s %s - #b#%s#b#, %d pts' % (i.position, i.name, i.injuryStatus.title().replace('_', ' '), i.projected_points)]

        if i.slot_position == 'IR' and \
            i.injuryStatus != 'INJURY_RESERVE' and i.injuryStatus != 'OUT':

            count += 1
            players += ['%s %s - #b#Not on IR#b#, %d pts' % (i.position, i.name, i.projected_points)]

    inactive_list = ""
    inactives = ""

    for p in players:
        inactive_list += "#p# " + p + "\n"

    if count > 0:
        inactives = ['%s%s#b#%s#b# - #b#%d#b#: \n%s \n' % (users[team.team_id], emotes[team.team_id], team.team_name, count, inactive_list[:-1])]
    
    return inactives


def get_matchups(league, week=None):
    """
    Retrieve the matchups for a given week in a fantasy football league.

    Parameters
    ----------
    league: object
        The league object for which to retrieve the matchups.
    week : int, optional
        The week number for which to retrieve the matchups, by default None.

    Returns
    -------
    str
        A string containing the matchups for the given week, formatted as a list of team names and abbreviation.
    """

    emotes = env_vars.split_emotes(league)
    matchups = league.box_scores(week=week)
    scores = []

    for i in matchups:
        if i.away_team:
            home_team = '%s#b#%s#b# (%s-%s)' % (emotes[i.home_team.team_id], i.home_team.team_name, i.home_team.wins, i.home_team.losses)
            away_team = '%s#b#%s#b# (%s-%s)' % (emotes[i.away_team.team_id], i.away_team.team_name, i.away_team.wins, i.away_team.losses)
            scores += [home_team.lstrip() + ' vs ' + away_team.lstrip()]

    text = ['#u##b#Matchups#b##u# '] + scores + ['']
    if random_phrase == True:
        text += util.get_random_phrase()

    return '\n'.join(text)


def get_close_scores(league, week=None):
    """
    Retrieve the projected closest scores (10.999 points or closer) for a given week in a fantasy football league.

    Parameters
    ----------
    league: object
        The league object for which to retrieve the closest scores.
    week : int, optional
        The week number for which to retrieve the closest scores, by default None.

    Returns
    -------
    str
        A string containing the projected closest scores for the given week, formatted as a list of team names and abbreviation.
    """

    emotes = env_vars.split_emotes(league)
    box_scores = league.box_scores(week=week)
    score = []

    for i in box_scores:
        if i.away_team:
            # away_projected = get_projected_total(i.away_lineup)
            # home_projected = get_projected_total(i.home_lineup)
            diffScore = i.away_projected - i.home_projected
            if (-11 < diffScore <= 0 and not all_played(i.away_lineup)) or (0 <= diffScore < 11 and not all_played(i.home_lineup)):
                score += ['%s#c#%4s %6.2f - %6.2f %4s#c#%s' % (emotes[i.home_team.team_id], i.home_team.team_abbrev, i.home_projected,
                                                 i.away_projected, i.away_team.team_abbrev, emotes[i.away_team.team_id])]
    if not score:
        return('')
    text = ['#u##b#Projected Close Scores#b##u#'] + score
    return '\n'.join(text)


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
    transactions = league.transactions(scoring_period, types={'WAIVER'})
    report = []
    emotes = env_vars.split_emotes(league)
    report_items = []  # For sorting if faab
    today = test_date if test_date else date.today().strftime('%Y-%m-%d')
    text = ''

    for txn in transactions:
        # Only include transactions matching the test date and type WAIVER
        txn_date = None
        if txn.date:
            txn_date = date.fromtimestamp(txn.date / 1000).strftime('%Y-%m-%d')
        if txn_date == today and txn.status == 'EXECUTED':
            team_name = f'{emotes[txn.team.team_id]}#b#{txn.team.team_name}#b#'
            faab_amount = txn.bid_amount if hasattr(txn, 'bid_amount') else 0
            add_str = ''
            drop_str = ''
            for item in txn.items:
                if item.type == 'ADD':
                    if faab:
                        add_str += f"#p# ADDED {league.player_info(item.player).position} - {item.player} (${faab_amount})\n"
                    else:
                        add_str += f"#p# ADDED {league.player_info(item.player).position} - {item.player}\n"
                elif item.type == 'DROP':
                    drop_str += f"#p# DROPPED {league.player_info(item.player).position} - {item.player}\n"
            s = f"{team_name} \n{add_str}{drop_str}"
            if faab:
                report_items.append((faab_amount, s.lstrip()))
            else:
                report.append(s.lstrip())

    if faab:
        # Sort by faab_amount descending
        report_items.sort(key=lambda x: x[0], reverse=True)
        report = [item[1] for item in report_items]

    # Only return a report if there are transactions
    if report:
        text = [f'#u##b#Waiver Report {today}#b##u#'] + report

    return '\n'.join(text)


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
    title = '#u##b#Power Rankings#b##u#'
    rankings_text = [title + ' [PR Points (%Change) | Playoff Chance | Simulated Record]']
    pos = 1
    for normalized_current_score, current_team in normalized_current_rankings:
        team_abbrev = current_team.team_abbrev
        rank_change_text = ''

        # Check if the team was present in the normalized previous rankings
        if team_abbrev in previous_rankings_dict:
            previous_score = previous_rankings_dict[team_abbrev]
            rank_change_percent = ((float(normalized_current_score) - float(previous_score)) / float(previous_score)) * 100
            rank_change_emoji = p_rank_up_emoji if rank_change_percent > 0 else p_rank_down_emoji if rank_change_percent < 0 else p_rank_same_emoji
            rank_change_text = f" ({rank_change_emoji} {abs(rank_change_percent):.1f}%)"

        rankings_text.append(f"{pos}: {emotes[current_team.team_id]}`{current_team.team_abbrev:4s} [{normalized_current_score}{rank_change_text} | {current_team.playoff_pct:.1f}% | {sr[current_team][0]}]`")
        pos += 1

    if random_phrase == True:
        rankings_text += [''] + util.get_random_phrase()
    
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
        try:
            position_players[player.position][player.name] = player.points
        except KeyError:
            position_players[player.position] = {}
            position_players[player.position][player.name] = player.points
        if player.slot_position not in ['BE', 'IR']:
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
        if i.home_team != 0:
            best_scores[i.home_team] = optimal_lineup_score(i.home_lineup, starter_counts)
        if i.away_team != 0:
            best_scores[i.away_team] = optimal_lineup_score(i.away_lineup, starter_counts)

    best_scores = {key: value for key, value in sorted(best_scores.items(), key=lambda item: item[1][3], reverse=True)}

    i = 1
    for score in best_scores:
        s = ['%s: %s #c#%4s: %6.2f [%6.2f - %.2f%%]#c#' %
                (i, emotes[score.team_id], score.team_abbrev, best_scores[score][0],
                best_scores[score][1], best_scores[score][3])]
        results += s
        i += 1

    if not results:
        return ('')


    text = [''] + ['#u##b#Best Possible Scores#b##u#  [Actual - % of optimal]'] + results + ['']
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
    for i in box_scores:
        home_performance = i.home_score - i.home_projected
        away_performance = i.away_score - i.away_projected

        if i.home_team != 0:
            if home_performance > best_performance:
                best_performance = home_performance
                over_achiever = i.home_team
            if home_performance < worst_performance:
                worst_performance = home_performance
                under_achiever = i.home_team
        if i.away_team != 0:
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


def get_weekly_score_with_win_loss(league, week=None):
    box_scores = league.box_scores(week=week)
    weekly_scores = {}
    for i in box_scores:
        if i.home_team != 0 and i.away_team != 0:
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
    Returns:
    list: A list containing the lucky and unlucky teams, along with their records for the week.
    """

    weekly_scores = get_weekly_score_with_win_loss(league, week=week)
    emotes = env_vars.split_emotes(league)
    losses = 0
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
    matchups = league.box_scores(week=week)
    mvp_score_diff = -100
    mvp_proj = -100
    mvp_score = ''
    mvp = ''
    mvp_team = -1

    lvp_score_diff = 999
    lvp_proj = 999
    lvp_score = ''
    lvp = ''
    lvp_team = -1

    for i in matchups:
        for p in i.home_lineup:
            if p.slot_position != 'BE' and p.slot_position != 'IR' and p.position != 'D/ST' and p.projected_points > 0:
                score_diff = (p.points - p.projected_points)/p.projected_points
                proj_diff = p.points - p.projected_points
                if (score_diff > mvp_score_diff) or (score_diff == mvp_score_diff and proj_diff > mvp_proj):
                    mvp_score_diff = score_diff
                    mvp_proj = proj_diff
                    mvp_score = '%.2f points (%.2f proj, %.2f diff ratio)' % (p.points, p.projected_points, score_diff)
                    mvp = p.position + ' ' + p.name
                    mvp_team = i.home_team
                elif (score_diff < lvp_score_diff) or (score_diff == lvp_score_diff and proj_diff < lvp_proj):
                    lvp_score_diff = score_diff
                    lvp_proj = proj_diff
                    lvp_score = '%.2f points (%.2f proj, %.2f diff ratio)' % (p.points, p.projected_points, score_diff)
                    lvp = p.position + ' ' + p.name
                    lvp_team = i.home_team
        for p in i.away_lineup:
            if p.slot_position != 'BE' and p.slot_position != 'IR' and p.position != 'D/ST' and p.projected_points > 0:
                score_diff = (p.points - p.projected_points)/p.projected_points
                proj_diff = p.points - p.projected_points
                if (score_diff > mvp_score_diff) or (score_diff == mvp_score_diff and proj_diff > mvp_proj):
                    mvp_score_diff = score_diff
                    mvp_proj = proj_diff
                    mvp_score = '%.2f points (%.2f proj, %.2f diff ratio)' % (p.points, p.projected_points, score_diff)
                    mvp = p.position + ' ' + p.name
                    mvp_team = i.away_team
                elif (score_diff < lvp_score_diff) or (score_diff == lvp_score_diff and proj_diff < lvp_proj):
                    lvp_score_diff = score_diff
                    lvp_proj = proj_diff
                    lvp_score = '%.2f points (%.2f proj, %.2f diff ratio)' % (p.points, p.projected_points, score_diff)
                    lvp = p.position + ' ' + p.name
                    lvp_team = i.away_team

    mvp_str = ['👍 #c#Week MVP:#c# %s \n#p# %s, #b#%s#b# with %s' % (emotes[mvp_team.team_id], mvp, mvp_team.team_abbrev, mvp_score)]
    lvp_str = ['👎 #c#Week LVP:#c# %s \n#p# %s, #b#%s#b# with %s' % (emotes[lvp_team.team_id], lvp, lvp_team.team_abbrev, lvp_score)]
    return (mvp_str + lvp_str)

def get_trophies(league, extra_trophies, week=None):
    """
    Returns trophies for the highest score, lowest score, closest score, and biggest win.

    Parameters
    ----------
    league : object
        The league object for which the trophies are to be returned
    week : int, optional
        The week for which the trophies are to be returned (default is current week)

    Returns
    -------
    str
        A string representing the trophies
    """
    if not week:
        week = league.current_week - 1

    emotes = env_vars.split_emotes(league)
    matchups = league.box_scores(week=week)

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

    text = ['#u##b#Trophies of the week#b##u# '] + high_score_str + low_score_str + close_score_str + blowout_str

    if extra_trophies == True:
        text += get_achievers_trophy(league, low_team.team_id, high_team.team_id, week) + get_lucky_trophy(league, week) + get_mvp_trophy(league, week) + ['']
    else:
        text += ['']

    if random_phrase == True:
        text += util.get_random_phrase()

    return '\n'.join(text)


def get_player_achievers(league, week=None, return_number=2):
    """
    Returns the top and bottom N players who exceeded or fell short of their projection the most in starting lineups for the given week.
    """
    if not week:
        week = league.current_week - 1
    box_scores = league.box_scores(week=week)
    player_diffs = []
    for matchup in box_scores:
        for team, team_lineup in zip([matchup.home_team, matchup.away_team], [matchup.home_lineup, matchup.away_lineup]):
            for player in team_lineup:
                if player.slot_position not in ['BE', 'IR'] and hasattr(player, 'projected_points') and player.projected_points is not None:
                    diff = round(player.points - player.projected_points, 2)
                    player_diffs.append({
                        'name': player.name,
                        'team': player.proTeam if hasattr(player, 'proTeam') else '',
                        'fantasy_team': team.team_abbrev if team else '',
                        'points': player.points,
                        'projected': player.projected_points,
                        'diff': diff
                    })
    sorted_diffs = sorted(player_diffs, key=lambda x: x['diff'], reverse=True)
    best = sorted_diffs[:return_number]
    worst = sorted_diffs[-return_number:]
    return best, worst
