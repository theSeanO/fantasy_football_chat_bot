from datetime import date
import gamedaybot.utils as utils
import env_vars

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
    # Gets current week's scoreboard
    box_scores = league.box_scores(week=week)
    score = ['%s`%4s %6.2f - %6.2f %4s` %s' % (emotes[i.home_team.team_id], i.home_team.team_abbrev, i.home_score,
                                    i.away_score, i.away_team.team_abbrev, emotes[i.away_team.team_id]) for i in box_scores
             if i.away_team]

    if week == league.current_week - 1:
        text = ['__**Final Score Update:**__ ']
    else:
        text = ['__**Score Update**__']
    
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

    # Gets current week's scoreboard projections
    box_scores = league.box_scores(week=week)
    score = ['%s`%4s %6.2f - %6.2f %4s` %s' % (emotes[i.home_team.team_id], i.home_team.team_abbrev, get_projected_total(i.home_lineup),
                                    get_projected_total(i.away_lineup), i.away_team.team_abbrev, emotes[i.away_team.team_id]) for i in box_scores
             if i.away_team]

    text = ['__**Approximate Projected Scores**__'] + score
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

    text = ['__**Current Standings:**__ '] + standings_txt + ['']
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
    
    text = ['__**Players to Monitor:**__ '] + monitor
    if random_phrase == True:
        text += utils.get_random_phrase()
    
    return '\n'.join(text)


def get_inactives(league, week=None):
    users = env_vars.split_users(league)
    box_scores = league.box_scores(week=week)
    inactives = []
    text = ''

    for i in box_scores:
        inactives += scan_inactives(i.home_lineup, i.home_team, users)
        inactives += scan_inactives(i.away_lineup, i.away_team, users)

    if not inactives:
        return ('')

    text = ['__**Inactive Players:**__ '] + inactives
    if random_phrase == True:
        text += utils.get_random_phrase()

    return '\n'.join(text)


def scan_roster(lineup, team, warning, emotes):
    count = 0
    players = []
    for i in lineup:
        if i.slot_position != 'BE' and i.slot_position != 'IR' and i.position != 'D/ST':
            if (i.pro_opponent == 'None') or (i.injuryStatus != 'ACTIVE' and i.injuryStatus != 'NORMAL') or (i.projected_points <= warning):
                count += 1
                player = i.position + ' ' + i.name + ' - '
                if i.pro_opponent == 'None':
                    player += '**BYE**'
                elif i.injuryStatus != 'ACTIVE' and i.injuryStatus != 'NORMAL':
                    player += '**' + i.injuryStatus.title().replace('_', ' ') + '**'
                elif i.projected_points <= warning:
                    player += '**' + str(i.projected_points) + ' pts**'
                players += [player]
        elif i.position == 'D/ST' and (i.pro_opponent == 'None' or i.projected_points <= warning):
            count += 1
            player = i.name + ' - '
            if i.pro_opponent == 'None':
                player += '**BYE**'
            elif i.projected_points <= warning:
                player += '**' + str(i.projected_points) + ' pts**'
            players += [player]
                
    list = ""
    report = ""

    for p in players:
        list += p + "\n"

    if count > 0:
        s = '%s**%s** - **%d**: \n%s \n' % (emotes[team.team_id], team.team_name, count, list[:-1])
        report =  [s.lstrip()]

    return report


def scan_inactives(lineup, team, users):
    count = 0
    players = []
    for i in lineup:
        if i.slot_position != 'BE' and i.slot_position != 'IR' and i.position != 'D/ST':
            if i.pro_opponent == 'None':
                count +=1
                players += ['%s %s - **BYE**' % (i.position, i.name)]
            elif i.game_played == 0 and (i.injuryStatus == 'OUT' or i.injuryStatus == 'DOUBTFUL' or i.projected_points <= 0):
                count +=1
                players += ['%s %s - **%s**, %d pts' % (i.position, i.name, i.injuryStatus.title().replace('_', ' '), i.projected_points)]
        elif i.position == 'D/ST' and i.pro_opponent == 'None':
            count += 1
            players += ['%s - **BYE**' % (i.name)]
            

    inactive_list = ""
    inactives = ""

    for p in players:
        inactive_list += p + "\n"

    if count > 0:
        inactives = ['%s**%s** - **%d**: \n%s \n' % (users[team.team_id], team.team_name, count, inactive_list[:-1])]
    
    return inactives


def get_matchups(league, week=None):
    emotes = env_vars.split_emotes(league)
    # Gets current week's Matchups
    matchups = league.box_scores(week=week)
    scores = []

    for i in matchups:
        if i.away_team:
            home_team = '%s**%s** (%s-%s)' % (emotes[i.home_team.team_id], i.home_team.team_name, i.home_team.wins, i.home_team.losses)
            away_team = '%s**%s** (%s-%s)' % (emotes[i.away_team.team_id], i.away_team.team_name, i.away_team.wins, i.away_team.losses)
            scores += [home_team.lstrip() + ' vs ' + away_team.lstrip()]

    text = ['__**Matchups:**__ '] + scores + [' ']
    if random_phrase == True:
        text += utils.get_random_phrase()

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
    # Gets current closest scores (15.999 points or closer)
    box_scores = league.box_scores(week=week)
    score = []

    for i in box_scores:
        if i.away_team:
            diffScore = i.away_score - i.home_score
            if (-16 < diffScore <= 0 and not all_played(i.away_lineup)) or (0 <= diffScore < 16 and not all_played(i.home_lineup)):
                score += ['%s`%4s %6.2f - %6.2f %4s`%s' % (emotes[i.home_team.team_id], i.home_team.team_abbrev, i.home_score,
                                                 i.away_score, i.away_team.team_abbrev, emotes[i.away_team.team_id])]
    if not score:
        return('')
    text = ['__**Close Scores**__'] + score
    return '\n'.join(text)


def get_waiver_report(league, faab=False):
    """
    This function generates a waiver report for a given league.
    The report lists all the waiver transactions that occurred on the current day,
    including the team that made the transaction, the player added and the player dropped (if applicable).

    Parameters
    ----------
    league: object
        The league object for which the report is being generated
    faab : bool, optional
        A flag to indicate whether the report should include FAAB amount spent, by default False.

    Returns
    -------
    str
        A string containing the waiver report
    """

    # Get the recent activity of the league
    emotes = env_vars.split_emotes(league)
    activities = league.recent_activity(50)
    # Initialize an empty list to store the report
    report = []
    # Get the current date
    today = date.today().strftime('%Y-%m-%d')
    text = ''

    # Iterate through each activity
    for activity in activities:
        actions = activity.actions
        d2 = date.fromtimestamp(activity.date/1000).strftime('%Y-%m-%d')
        if d2 == today:  # only get waiver activites from today
            if len(actions) == 1 and actions[0][1] == 'WAIVER ADDED':
                if faab:
                    s = '%s**%s** \nADDED%s %s ($%s)\n' % (emotes[actions[0][0].team_id], actions[0][0].team_name, ' '+actions[0][2].position if actions[0][2].position != 'D/ST' else '', actions[0][2].name, actions[0][3])
                else:
                    s = '%s**%s** \nADDED%s %s\n' % (emotes[actions[0][0].team_id], actions[0][0].team_name, ' '+actions[0][2].position if actions[0][2].position != 'D/ST' else '', actions[0][2].name)
                report += [s.lstrip()]
            elif len(actions) > 1:
                if actions[0][1] == 'WAIVER ADDED' or  actions[1][1] == 'WAIVER ADDED':
                    if actions[0][1] == 'WAIVER ADDED':
                        if faab:
                            s = '%s**%s** \nADDED%s %s ($%s)\nDROPPED %s %s\n' % (emotes[actions[0][0].team_id], actions[0][0].team_name, ' '+actions[0][2].position if actions[0][2].position != 'D/ST' else '', actions[0][2].name, actions[0][3], ' '+actions[1][2].position if actions[1][2].position != 'D/ST' else '', actions[1][2].name)
                        else:
                            s = '%s**%s** \nADDED%s %s, \nDROPPED%s %s\n' % (emotes[actions[0][0].team_id], actions[0][0].team_name, ' '+actions[0][2].position if actions[0][2].position != 'D/ST' else '', actions[0][2].name, ' '+actions[1][2].position if actions[1][2].position != 'D/ST' else '', actions[1][2].name)
                    else:
                        if faab:
                            s = '%s**%s** \nADDED%s %s ($%s)\nDROPPED %s %s\n' % (emotes[actions[0][0].team_id], actions[0][0].team_name, ' '+actions[1][2].position if actions[1][2].position != 'D/ST' else '', actions[1][2].name, actions[1][3], ' '+actions[0][2].position if actions[0][2].position != 'D/ST' else '', actions[0][2].name)
                        else:
                            s = '%s**%s** \nADDED%s %s, \nDROPPED%s %s\n' % (emotes[actions[0][0].team_id], actions[0][0].team_name, ' '+actions[1][2].position if actions[1][2].position != 'D/ST' else '', actions[1][2].name, ' '+actions[0][2].position if actions[0][2].position != 'D/ST' else '', actions[0][2].name)
                    report += [s.lstrip()]

    report.reverse()

    if not report:
        report += ['No waiver transactions']
    else:
        text = ['__**Waiver Report %s:**__' % today] + report + ['']

    if random_phrase == True:
        text += utils.get_random_phrase()

    return '\n'.join(text)


def combined_power_rankings(league, week=None):
    emotes = env_vars.split_emotes(league)
    if not week:
        week = league.current_week

    pr = league.power_rankings(week=week)
    sr = sim_record_percent(league, week=week)
    sr_sorted = sim_record_percent(league, week=week)

    combRankingDict = {x: 0. for x in league.teams}

    pos = 0
    for i in pr:
        for j in sr:
            if i[1].team_id == j[1].team_id:
                sr_sorted[pos] = j
        pos+=1

    ranks = []
    pos = 1

    for i in pr:
        if i:
            ranks += ['%s: %s%s (%s - %.1f - %s)' % (pos, emotes[i[1].team_id], i[1].team_name, i[0], i[1].playoff_pct, sr_sorted[pos-1][0])]
        pos += 1

    text = ['__**Power Rankings:**__ (PR points - Playoff % - Simulated Record)'] + ranks + ['']

    if random_phrase == True:
        text += utils.get_random_phrase()

    return '\n'.join(text)

def sim_record_percent(league, week):
    #This script gets power rankings, given an already-connected league and a week to look at. Requires espn_api
    #Get what week most recently passed
    lastWeek = league.current_week

    if week:
        lastWeek = week

    #initialize dictionaries to stash the projected record/expected wins for each week, and to stash each team's score for each week
    projRecDicts = {i: {x: None for x in league.teams} for i in range(lastWeek)}
    teamScoreDicts = {i: {x: None for x in league.teams} for i in range(lastWeek)}

    #initialize the dictionary for the final power ranking
    powerRankingDict = {x: 0. for x in league.teams}

    for i in range(lastWeek): #for each week that has been played
        weekNumber = i+1      #set the week
        boxes = league.box_scores(weekNumber)	#pull box scores from that week
        for box in boxes:							#for each boxscore
            teamScoreDicts[i][box.home_team] = box.home_score	#plug the home team's score into the dict
            teamScoreDicts[i][box.away_team] = box.away_score	#and the away team's

        for team in teamScoreDicts[i].keys():		#for each team
            wins = 0
            losses = 0
            ties = 0
            oppCount = len(list(teamScoreDicts[i].keys()))-1
            for opp in teamScoreDicts[i].keys():		#for each potential opponent
                if team==opp:							#skip yourself
                    continue
                if teamScoreDicts[i][team] > teamScoreDicts[i][opp]:	#win case
                    wins += 1
                if teamScoreDicts[i][team] < teamScoreDicts[i][opp]:	#loss case
                    losses += 1

            if wins + losses != oppCount:			#in case of an unlikely tie
                ties = oppCount - wins - losses

            projRecDicts[i][team] = (float(wins) + (0.5*float(ties)))/float(oppCount) #store the team's projected record for that week

    for team in powerRankingDict.keys():			#for each team
        powerRankingDict[team] = sum([projRecDicts[i][team] for i in range(lastWeek)])/float(lastWeek) #total up the expected wins from each week, divide by the number of weeks

    powerRankingDictSortedTemp = {k: v for k, v in sorted(powerRankingDict.items(), key=lambda item: item[1],reverse=True)} #sort for presentation purposes
    powerRankingDictSorted = {x: ('{:.3f}'.format(powerRankingDictSortedTemp[x])) for x in powerRankingDictSortedTemp.keys()}  #put into a prettier format
    return [(powerRankingDictSorted[x],x) for x in powerRankingDictSorted.keys()]    #return in the format that the bot expects


def best_possible_scores(league, week=None):
    emotes = env_vars.split_emotes(league)
    week = league.current_week - 1
    box_scores = league.box_scores(week=week)
    results = []
    best_scores = {}

    for i in box_scores:
        best_scores[i.home_team] = best_lineup_score(i.home_lineup)
        best_scores[i.away_team] = best_lineup_score(i.away_lineup)

    best_scores = {key: value for key, value in sorted(best_scores.items(), key=lambda item: item[1][3], reverse=True)}

    i = 1
    for score in best_scores:
        s = ['%d: %s%s: %.2f (%.2f - %.2f%%)' % (i, emotes[score.team_id], score.team_name, best_scores[score][0], best_scores[score][1], best_scores[score][3])]
        results += s
        i += 1

    if not results:
        return ('')

    text = ['__**Best Possible Scores:**__  (Actual Score - % of possible)'] + results + ['']

    return '\n'.join(text)

def best_lineup_score(lineup):
    score = 0
    best_score = 0
    num_qb = num_flex = num_te = num_k = num_dst = 1
    num_rb = num_wr = 2

    qb = {}
    rb = {}
    wr = {}
    te = {}
    dst = {}
    k = {}

    for p in lineup:
        if p.position == 'QB':
            qb[p.name] = p.points
        elif p.position == 'RB':
            rb[p.name] = p.points
        elif p.position == 'WR':
            wr[p.name] = p.points
        elif p.position == 'TE':
            te[p.name] = p.points
        elif p.position == 'D/ST':
            dst[p.name] = p.points
        elif p.position == 'K':
            k[p.name] = p.points
        if p.slot_position not in ['BE', 'IR']:
            score += p.points

    best_qb = {key: value for key, value in sorted(qb.items(), key=lambda item: item[1], reverse=True)[:num_qb:]}
    best_rb = {key: value for key, value in sorted(rb.items(), key=lambda item: item[1], reverse=True)[:num_rb:]}
    best_wr = {key: value for key, value in sorted(wr.items(), key=lambda item: item[1], reverse=True)[:num_wr:]}
    best_te = {key: value for key, value in sorted(te.items(), key=lambda item: item[1], reverse=True)[:num_te:]}
    best_dst = {key: value for key, value in sorted(dst.items(), key=lambda item: item[1], reverse=True)[:num_dst:]}
    best_k = {key: value for key, value in sorted(k.items(), key=lambda item: item[1], reverse=True)[:num_k:]}

    flex = {}
    for p in lineup:
        if p.position in ['RB', 'WR', 'TE']:
            if p.name not in best_rb and p.name not in best_wr and p.name not in best_te:
                flex[p.name] = p.points

    best_flex = {key: value for key, value in sorted(flex.items(), key=lambda item: item[1], reverse=True)[:num_flex:]}

    best_score += sum(best_qb.values())
    best_score += sum(best_rb.values())
    best_score += sum(best_wr.values())
    best_score += sum(best_te.values())
    best_score += sum(best_flex.values())
    best_score += sum(best_dst.values())
    best_score += sum(best_k.values())

    score_diff = best_score - score
    score_pct = (score / best_score) * 100

    # Only needed this for testing
    # team_str = ''
    # team_str += 'QB: ' + (', '.join(best_qb.keys())) 
    # team_str += ' | RB: ' + (', '.join(best_rb.keys())) 
    # team_str += ' | WR: ' + (', '.join(best_wr.keys())) 
    # team_str += ' | TE: ' + (', '.join(best_te.keys())) 
    # team_str += ' | Flex: ' + (', '.join(best_flex.keys())) 
    # team_str += ' | ' + (', '.join(best_dst.keys())) 
    # team_str += ' | K: ' + (', '.join(best_k.keys())) 
    # s = ['%s**%s**: %.2f (%.2f actual, %.2f diff) %s' % (emotes[team.team_id],team.team_name, best_score, score, score_diff, team_str)]

    return (best_score, score, score_diff, score_pct)


def get_trophies(league, extra_trophies, week=None):
    emotes = env_vars.split_emotes(league)
    #Gets trophies for highest score, lowest score, overachiever, underachiever, week MVP & LVP, closest score, and biggest win
    matchups = league.box_scores(week=week)

    low_score = 9999
    low_team = -1

    high_score = -1
    high_team = -1

    closest_score = 9999
    close_winner = -1
    close_loser = -1

    biggest_blowout = -1
    blown_out_team = -1
    ownerer_team = -1

    over_diff = -1000
    over_team = -1

    under_diff = 999
    under_team = -1

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

        if (i.home_score - get_projected_final(i.home_lineup)) > over_diff:
            over_diff = i.home_score - get_projected_final(i.home_lineup)
            over_team = i.home_team
        elif (i.home_score - get_projected_final(i.home_lineup)) < under_diff:
            under_diff = i.home_score - get_projected_final(i.home_lineup)
            under_team = i.home_team

        if (i.away_score - get_projected_final(i.away_lineup)) > over_diff:
            over_diff = i.away_score - get_projected_final(i.away_lineup)
            over_team = i.away_team
        elif (i.away_score - get_projected_final(i.away_lineup)) < under_diff:
            under_diff = i.away_score - get_projected_final(i.away_lineup)
            under_team = i.away_team

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

    low_score_str = ['Lowest score: %s**%s** with %.2f points' % (emotes[low_team.team_id], low_team.team_name, low_score)]
    high_score_str = ['Highest score: %s**%s** with %.2f points' % (emotes[high_team.team_id], high_team.team_name, high_score)]
    over_str = ['Overachiever: %s**%s** with %.2f points more than their projection' % (emotes[over_team.team_id], over_team.team_name, over_diff)]
    under_str = ['Underachiever: %s**%s** with %.2f points less than their projection' % (emotes[under_team.team_id], under_team.team_name, abs(under_diff))]
    mvp_str = ['Week MVP: %s, %s**%s** with %s' % (mvp, emotes[mvp_team.team_id], mvp_team.team_abbrev, mvp_score)]
    lvp_str = ['Week LVP: %s, %s**%s** with %s' % (lvp, emotes[lvp_team.team_id], lvp_team.team_abbrev, lvp_score)]
    close_score_str = ['%s**%s** barely beat %s**%s** by a margin of %.2f' % (emotes[close_winner.team_id], close_winner.team_name, emotes[close_loser.team_id], close_loser.team_name, closest_score)]
    blowout_str = ['%s**%s** got blown out by %s**%s** by a margin of %.2f' % (emotes[blown_out_team.team_id], blown_out_team.team_name, emotes[ownerer_team.team_id], ownerer_team.team_name, biggest_blowout)]

    text = ['__**Trophies of the week:**__ '] + low_score_str + high_score_str + close_score_str + blowout_str

    if extra_trophies == True:
        if under_diff < 0 and low_team.team_name != under_team.team_name:
            text += under_str
        if over_diff > 0 and high_team.team_name != over_team.team_name:
            text += over_str
        text += lvp_str + mvp_str + [' ']
    else:
        text += [' ']

    if random_phrase == True:
        text += utils.get_random_phrase()

    return '\n'.join(text)
