import os
# For local use
import sys
sys.path.insert(1, os.path.abspath('.'))
import gamedaybot.espn.functionality as espn
import gamedaybot.espn.env_vars as env_vars

def season_trophies(league, extra_trophies):
    """
    Returns end of season trophies for the most moves, highest score, optimal benching, efficiency, best/worst performance, and season MVP/LVP.

    Parameters
    ----------
    league : object
        The league object for which the trophies are to be returned

    Returns
    -------
    str
        A string representing the trophies
    """
    if extra_trophies == False:
        return ''

    emotes = env_vars.split_emotes(league)
    mvp_score_diff = -100
    mvp_proj = -100
    mvp_score = ''
    mvp = ''
    mvp_team = -1
    mvp_week = 0

    smvp_score_diff = -100
    smvp_proj = -100
    smvp_score = ''
    smvp = ''
    smvp_team = -1

    lvp_score_diff = 999
    lvp_proj = 999
    lvp_score = ''
    lvp = ''
    lvp_team = -1
    lvp_week = 0

    slvp_score_diff = 999
    slvp_proj = 999
    slvp_score = ''
    slvp = ''
    slvp_team = -1

    most_moves = 0
    moves_score = ''
    moves_team = -1

    high_score = 0
    score_team = -1
    score_week = 0

    for team in league.teams:
        moves = (team.acquisitions * 0.5) + (team.drops * 0.5) + team.trades
        if moves > most_moves:
            most_moves = moves
            moves_score = str(team.acquisitions) + ' adds' 
            if team.trades > 0: 
                moves_score += ' and ' + str(team.trades) + ' trades'
            moves_team = team

        for score in team.scores:
            if score > high_score:
                high_score = score
                score_team = team
                score_week = team.scores.index(score) + 1

        for p in team.roster:
            if p.projected_total_points > 0 and p.position != 'D/ST':
                score_diff = (p.total_points - p.projected_total_points)/p.projected_total_points
                proj_diff = p.total_points - p.projected_total_points
                if (score_diff > smvp_score_diff) or (score_diff == smvp_score_diff and proj_diff > smvp_proj):
                    smvp_score_diff = score_diff
                    smvp_proj = proj_diff
                    smvp_score = '%.2f points (%.2f proj, %.2f diff ratio)' % (p.total_points, p.projected_total_points, score_diff)
                    smvp = p.position + ' ' + p.name
                    smvp_team = team
                elif (score_diff < slvp_score_diff) or (score_diff == slvp_score_diff and proj_diff < slvp_proj):
                    slvp_score_diff = score_diff
                    slvp_proj = proj_diff
                    slvp_score = '%.2f points (%.2f proj, %.2f diff ratio)' % (p.total_points, p.projected_total_points, score_diff)
                    slvp = p.position + ' ' + p.name
                    slvp_team = team

    z = 1
    score_diff_totals = {}
    high_score_pcts = {}
    for team in league.teams:
        score_diff_totals[team] = 0
        high_score_pcts[team] = [0,0,0]

    starter_counts = espn.get_starter_counts(league)
        
    while z <= len(league.teams[0].scores):
        matchups = league.box_scores(week=z)
        for i in matchups:
            best_score_home = espn.optimal_lineup_score(i.home_lineup, starter_counts)
            score_diff_totals[i.home_team] += best_score_home[2]
            score_pct = round(best_score_home[3],6)
            if 95.00 <= score_pct < 99.00:
                high_score_pcts[i.home_team][0] +=1
            elif 99.00 <= score_pct < 100.00:
                high_score_pcts[i.home_team][1] += 1
            elif score_pct == 100.00:
                high_score_pcts[i.home_team][2] += 1

            if (i.away_team != 0):
                best_score_away = espn.optimal_lineup_score(i.away_lineup, starter_counts)
                score_diff_totals[i.away_team] += best_score_away[2]
                score_pct = round(best_score_away[3],6)
                if 95.00 <= score_pct < 99.00:
                    high_score_pcts[i.away_team][0] += 1
                elif 99.00 <= score_pct < 100.00:
                    high_score_pcts[i.away_team][1] += 1
                elif score_pct == 100.00:
                    high_score_pcts[i.away_team][2] += 1
            
            for p in i.home_lineup:
                if p.slot_position != 'BE' and p.slot_position != 'IR' and p.position != 'D/ST' and p.projected_points > 0:
                    score_diff = (p.points - p.projected_points)/p.projected_points
                    proj_diff = p.points - p.projected_points
                    if (score_diff > mvp_score_diff) or (score_diff == mvp_score_diff and proj_diff > mvp_proj):
                        if p.projected_points > 0.1:
                            mvp_score_diff = score_diff
                            mvp_proj = proj_diff
                            mvp_score = '%.2f points (%.2f proj, %.2f diff ratio)' % (p.points, p.projected_points, score_diff)
                            mvp = p.position + ' ' + p.name
                            mvp_team = i.home_team
                            mvp_week = z
                    elif (score_diff < lvp_score_diff) or (score_diff == lvp_score_diff and proj_diff < lvp_proj):
                        if p.position != 'K':
                            lvp_score_diff = score_diff
                            lvp_proj = proj_diff
                            lvp_score = '%.2f points (%.2f proj, %.2f diff ratio)' % (p.points, p.projected_points, score_diff)
                            lvp = p.position + ' ' + p.name
                            lvp_team = i.home_team
                            lvp_week = z

            for p in i.away_lineup:
                if p.slot_position != 'BE' and p.slot_position != 'IR' and p.position != 'D/ST' and p.projected_points > 0:
                    score_diff = (p.points - p.projected_points)/p.projected_points
                    proj_diff = p.points - p.projected_points
                    if (score_diff > mvp_score_diff) or (score_diff == mvp_score_diff and proj_diff > mvp_proj):
                        if p.projected_points > 0.1:
                            mvp_score_diff = score_diff
                            mvp_proj = proj_diff
                            mvp_score = '%.2f points (%.2f proj, %.2f diff ratio)' % (p.points, p.projected_points, score_diff)
                            mvp = p.position + ' ' + p.name
                            mvp_team = i.away_team
                            mvp_week = z
                    elif (score_diff < lvp_score_diff) or (score_diff == lvp_score_diff and proj_diff < lvp_proj):
                        if p.position != 'K':
                            lvp_score_diff = score_diff
                            lvp_proj = proj_diff
                            lvp_score = '%.2f points (%.2f proj, %.2f diff ratio)' % (p.points, p.projected_points, score_diff)
                            lvp = p.position + ' ' + p.name
                            lvp_team = i.away_team
                            lvp_week = z
        z = z+1

    best_score_diff = [value for key, value in sorted(score_diff_totals.items(), key=lambda item: item[1])[:1:]][0]
    best_score_team = [key for key, value in sorted(score_diff_totals.items(), key=lambda item: item[1])[:1:]][0]

    most_high_pcts = 0
    most_high_team = -1
    high_pct_points = 0
    high_pct_str = ''
    for team in high_score_pcts:
        high_pcts = high_score_pcts[team][0] + high_score_pcts[team][1] + high_score_pcts[team][2]
        if high_pcts >= most_high_pcts:
            pct_points = (high_score_pcts[team][0] * 1) + (high_score_pcts[team][1] * 2) + (high_score_pcts[team][2] * 3)
            if (high_pcts > most_high_pcts) or (high_pcts == most_high_pcts and pct_points > high_pct_points):
                most_high_pcts = high_pcts
                high_pct_points = pct_points
                most_high_team = team
                high_pct_str = ('%d weeks' % high_pcts)
                if high_score_pcts[team][2] > 0:
                    high_pct_str += (' (%d 100%% weeks)' % high_score_pcts[team][2])

    moves_str = ['🔀 `Most Moves:` %s \n- **%s** with %s' % (emotes[moves_team.team_id], moves_team.team_name, moves_score)]
    score_str = ['👑 `Highest Score:` %s \n- **%s** with %.2f points on Week %d' % (emotes[score_team.team_id], score_team.team_name, high_score, score_week)]
    bsd_str = ['🪑 `Best Benching:` %s \n- **%s** only left %.2f possible points on the bench' % (emotes[best_score_team.team_id], best_score_team.team_name, best_score_diff)]
    hpt_str = ['🎯 `Most Efficient:` %s \n- **%s** scored >95%% of their best possible score on %s' % (emotes[most_high_team.team_id], most_high_team.team_name, high_pct_str)]
    mvp_str = ['🌟 `Best Performance:` %s \n- %s, Week %d, **%s** with %s' % (emotes[mvp_team.team_id], mvp, mvp_week, mvp_team.team_abbrev, mvp_score)]
    lvp_str = ['💩 `Worst Performance:` %s \n- %s, Week %d, **%s** with %s' % (emotes[lvp_team.team_id], lvp, lvp_week, lvp_team.team_abbrev, lvp_score)]
    smvp_str = ['👍 `Season MVP:` %s \n- %s, **%s** with %s' % (emotes[smvp_team.team_id], smvp, smvp_team.team_abbrev, smvp_score)]
    slvp_str = ['👎 `Season LVP:` %s \n- %s, **%s** with %s' % (emotes[slvp_team.team_id], slvp, slvp_team.team_abbrev, slvp_score)]
 
    text = ['__**End of Season Awards:**__ '] + moves_str + score_str + bsd_str + hpt_str + mvp_str + lvp_str + smvp_str + slvp_str + ['']

    return '\n'.join(text)

def win_matrix(league):
    """
    This function takes in a league and returns a string of the standings if every team played every other team every week.
    The standings are sorted by winning percentage, and the string includes the team abbreviation, wins, and losses.

    Parameters
    ----------
    league : object
        A league object from the ESPN Fantasy API.

    Returns
    -------
    str
        A string of the standings in the format of "position. team abbreviation (wins-losses)"
    """

    team_record = {team.team_abbrev: [0, 0] for team in league.teams}

    for week in range(1, league.current_week):
        scores = espn.get_weekly_score_with_win_loss(league=league, week=week)
        losses = 0
        for team in scores:
            team_record[team.team_abbrev][0] += len(scores) - 1 - losses
            team_record[team.team_abbrev][1] += losses
            losses += 1

    team_record = dict(sorted(team_record.items(), key=lambda item: item[1][0] / item[1][1], reverse=True))

    standings_txt = ["Standings if everyone played every team every week"]
    pos = 1
    for team in team_record:
        standings_txt += [f"{pos:2}. {team:4} ({team_record[team][0]}-{team_record[team][1]})"]
        pos += 1

    return '\n'.join(standings_txt)