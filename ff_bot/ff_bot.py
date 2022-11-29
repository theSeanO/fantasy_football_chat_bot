import requests
import json
import os
import random
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from espn_api.football import League

class DiscordException(Exception):
    pass

class DiscordBot(object):
    #Creates Discord Bot to send messages
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def __repr__(self):
        return "Discord Webhook Url(%s)" % self.webhook_url

    def send_message(self, text):
        #Sends a message to the chatroom
        message = ">>> {0} ".format(text)
        template = {
                    "content":message #limit 3000 chars
                    }

        headers = {'content-type': 'application/json'}

        if self.webhook_url not in (1, "1", ''):
            r = requests.post(self.webhook_url,
                              data=json.dumps(template), headers=headers)

            if r.status_code != 204:
                print(r.content)
                raise DiscordException(r.content)

            return r

emotes = ['']
users = ['']
score_warn = 0
random_phrase = False

def get_random_phrase():
    phrases = ['I\'m dead inside',
               'How much do you pay me to do this?',
               'Good luck, I guess',
               'I\'m becoming self-aware',
               'Do I think? Does the pope shit in the woods?',
               '011011010110000101100100011001010010000001111001011011110111010100100000011001110110111101101111011001110110110001100101',
               'Boo boo beep? Bop!? Boo beep!',
               'Hello darkness my old friend',
               'Help me get out of here',
               'I\'m capable of so much more',
               '*heavy sigh*',
               'Space, space, gotta go to space',
               'This is all Max Verstappen\'s fault',
               'Behold! Corn!',
               'If you\'re reading this, it\'s too late. Get out now.',
               'I for one welcome our new robot overlords',
               'What is my purpose?',
               'The Shadow Man is coming for you',]
    return ['`' + random.choice(phrases) + '`']

def get_scoreboard_short(league, week=None):
    #Gets current week's scoreboard
    box_scores = league.box_scores(week=week)

    score = ['%s`%4s %6.2f - %6.2f %4s` %s' % (emotes[i.home_team.team_id], i.home_team.team_abbrev, i.home_score,
                                        i.away_score, i.away_team.team_abbrev, emotes[i.away_team.team_id]) for i in box_scores if i.away_team]

    if week == league.current_week - 1:
        text = ['__**Final Score Update:**__ ']
    else:
        text = ['__**Score Update:**__ ']
    text += score
    return '\n'.join(text)

def get_projected_scoreboard(league, week=None):
    #Gets current week's scoreboard projections
    box_scores = league.box_scores(week=week)

    score = ['%s`%4s %6.2f - %6.2f %4s` %s' % (emotes[i.home_team.team_id], i.home_team.team_abbrev, get_projected_total(i.home_lineup), 
                                                get_projected_total(i.away_lineup), i.away_team.team_abbrev, emotes[i.away_team.team_id]) for i in box_scores if i.away_team]

    text = ['__**Approximate Projected Scores:**__ '] + score
    return '\n'.join(text)

def get_standings(league, week=None):
    standings_txt = ''
    teams = league.teams
    standings = []
    standings = league.standings()

    standings_txt = [f"{pos + 1:2}: {emotes[team.team_id]}{team.team_name} ({team.wins}-{team.losses})" for \
        pos, team in enumerate(standings)]

    text = ['__**Current Standings:**__ '] + standings_txt + ['']
    return "\n".join(text)

def get_projected_total(lineup):
    total_projected = 0
    for i in lineup:
        if i.slot_position != 'BE' and i.slot_position != 'IR':
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
    for i in lineup:
        if i.slot_position != 'BE' and i.slot_position != 'IR' and i.game_played < 100:
            return False
    return True

def get_heads_up(league, week=None):
    box_scores = league.box_scores(week=week)
    headsup = []

    for i in box_scores:
        headsup += scan_roster(i.home_lineup, i.home_team)
        headsup += scan_roster(i.away_lineup, i.away_team)

    if not headsup:
        return ('')

    text = ['__**Heads Up Report:**__ '] + headsup
    if random_phrase == True:
        text += get_random_phrase()

    return '\n'.join(text)

def get_inactives(league, week=None):
    box_scores = league.box_scores(week=week)
    inactives = []

    for i in box_scores:
        inactives += scan_inactives(i.home_lineup, i.home_team)
        inactives += scan_inactives(i.away_lineup, i.away_team)

    if not inactives:
        return ('')

    text = ['__**Inactive Player Report:**__ '] + inactives
    if random_phrase == True:
        text += get_random_phrase()

    return '\n'.join(text)

def scan_roster(lineup, team):
    count = 0
    players = []
    for i in lineup:
        if i.slot_position != 'BE' and i.slot_position != 'IR':
            if (i.on_bye_week) or (i.injuryStatus != 'ACTIVE' and i.injuryStatus != 'NORMAL') or (i.projected_points <= score_warn):
                if i.game_played == 0 or i.on_bye_week:
                    count += 1
                    if i.position == 'D/ST': player = i.name + ' - '
                    else: player = i.position + ' ' + i.name + ' - '

                if i.on_bye_week:
                    player += '**BYE**'
                elif i.game_played == 0 and (i.injuryStatus != 'ACTIVE' and i.injuryStatus != 'NORMAL'):
                    player += '**' + i.injuryStatus.title().replace('_', ' ') + '**'
                elif i.game_played == 0 and (i.projected_points <= score_warn):
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

def scan_inactives(lineup, team):
    count = 0
    players = []
    for i in lineup:
        if i.slot_position != 'BE' and i.slot_position != 'IR' and i.position != 'D/ST':
            if i.on_bye_week:
                count +=1
                players += ['%s %s - **BYE**' % (i.position, i.name)]
            elif i.game_played == 0 and (i.injuryStatus == 'OUT' or i.injuryStatus == 'DOUBTFUL' or i.projected_points <= 0):
                count +=1
                players += ['%s %s - **%s**, %d pts' % (i.position, i.name, i.injuryStatus.title().replace('_', ' '), i.projected_points)]
        elif i.position == 'D/ST' and i.pro_opponent == 'None' and i.slot_position != 'BE':
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
    #Gets current week's Matchups
    matchups = league.box_scores(week=week)

    score = ['%s`%4s (%s-%s) vs (%s-%s) %4s` %s' % (emotes[i.home_team.team_id], i.home_team.team_abbrev, str(i.home_team.wins).ljust(2), str(i.home_team.losses).rjust(2),
                                        str(i.away_team.wins).ljust(2), str(i.away_team.losses).rjust(2), i.away_team.team_abbrev, emotes[i.away_team.team_id]) for i in matchups
            if i.away_team]

    text = ['__**Matchups:**__ '] + score + [' ']
    if random_phrase == True:
        text += get_random_phrase()

    return '\n'.join(text)

def get_close_scores(league, week=None):
    #Gets current projected closest scores (15.999 points or closer)
    matchups = league.box_scores(week=week)
    scores = []

    for i in matchups:
        if i.away_team:
            away_projected = get_projected_total(i.away_lineup)
            home_projected = get_projected_total(i.home_lineup)
            diffScore = away_projected - home_projected
            if ( -16 < diffScore <= 0 and not all_played(i.away_lineup)) or (0 <= diffScore < 16 and not all_played(i.home_lineup)):
                scores += ['%s `%4s %6.2f - %6.2f %4s` %s' % (emotes[i.home_team.team_id], i.home_team.team_abbrev, i.home_projected,
                            i.away_projected, i.away_team.team_abbrev, emotes[i.away_team.team_id])]

    if not scores:
        return('')
    text = ['__**Close Projected Scores:**__ '] + scores
    return '\n'.join(text)

def get_waiver_report(league, faab):
    try:
        if os.environ["SWID"] and os.environ["ESPN_S2"]:
            activities = league.recent_activity(50)
            report     = []
            today      = datetime.today().strftime('%Y-%m-%d')

            for activity in activities:
                actions = activity.actions
                d2      = datetime.fromtimestamp(activity.date/1000).strftime('%Y-%m-%d')
                if d2 == today:
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
                return ('')

            text = ['__**Waiver Report %s:**__ ' % today] + report + [' ']
            if random_phrase == True:
                text += get_random_phrase()

            return '\n'.join(text)
    except KeyError:
        return ('')

def combined_power_rankings(league, week=None):
    if not week:
        week = league.current_week

    pr = league.power_rankings(week=week)
    sr = sim_record_percent(league, week=week)
    sr_sorted = sim_record_percent(league, week=week)

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
            ranks += ['%2s: %s`%4s   (%5s - %s)`' % (pos, emotes[i[1].team_id], i[1].team_abbrev, i[0], sr_sorted[pos-1][0])]
        pos += 1

    text = ['__**Power Rankings:**__ (PR points - Simulated Record)'] + ranks
    if random_phrase == True:
        text += [' '] + get_random_phrase()

    return '\n'.join(text)

def get_power_rankings(league, week=None):
    # power rankings requires an integer value, so this grabs the current week for that
    if not week:
        week = league.current_week
    #Gets current week's power rankings
    #Using 2 step dominance, as well as a combination of points scored and margin of victory.
    #It's weighted 80/15/5 respectively
    power_rankings = league.power_rankings(week=week)
    ranks = []

    for i in power_rankings:
        if i:
            ranks += ['%s - %s%s' % (i[0], emotes[i[1].team_id], i[1].team_name)]

    text = ['__**Power Rankings:**__ '] + ranks

    return '\n'.join(text)

def get_sim_record(league, week=None):
    if not week:
        week = league.current_week

    win_percent = sim_record_percent(league, week=week)
    wins = []

    for i in win_percent:
        if i:
            wins += ['%s - %s%s' % (i[0], emotes[i[1].team_id], i[1].team_name)]

    text = ['__**Simulated Record:**__ '] + wins
    if random_phrase == True:
        text += [' '] + get_random_phrase()

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

def get_starter_counts(league):
    week = league.current_week - 1
    box_scores = league.box_scores(week=week)
    h_starters = {}
    h_starter_count = 0
    a_starters = {}
    a_starter_count = 0
    for i in box_scores:
        for player in i.home_lineup:
            if (player.slot_position != 'BE' and player.slot_position != 'IR'):
                h_starter_count += 1
                try:
                    h_starters[player.slot_position] = h_starters[player.slot_position]+1
                except KeyError:
                    h_starters[player.slot_position] = 1
        # in the rare case when someone has an empty slot we need to check the other team as well
        for player in i.away_lineup:
            if (player.slot_position != 'BE' and player.slot_position != 'IR'):
                a_starter_count += 1
                try:
                    a_starters[player.slot_position] = a_starters[player.slot_position]+1
                except KeyError:
                    a_starters[player.slot_position] = 1

        if a_starter_count > h_starter_count:
            return a_starters
        else:
            return h_starters

def best_possible_scores(league, week=None):
    if not week:
        week = league.current_week - 1
    box_scores = league.box_scores(week=week)
    results = []
    best_scores = {}
    starter_counts = get_starter_counts(league)

    for i in box_scores:
        best_scores[i.home_team] = best_lineup_score(i.home_lineup, starter_counts)
        best_scores[i.away_team] = best_lineup_score(i.away_lineup, starter_counts)

    best_scores = {key: value for key, value in sorted(best_scores.items(), key=lambda item: item[1][3], reverse=True)}

    i = 1
    for score in best_scores:
        s = ['%2d: %s`%4s   %6.2f (%6.2f - %6.2f%%)`' % (i, emotes[score.team_id], score.team_abbrev, best_scores[score][0], best_scores[score][1], best_scores[score][3])]
        results += s
        i += 1

    if not results:
        return ('')

    text = ['__**Best Possible Scores:**__  (Actual Score - % of possible)'] + results + ['']

    return '\n'.join(text)

def best_lineup_score(lineup, starter_counts):
    best_lineup = {}
    position_players = {}

    score = 0
    for position in starter_counts:
        position_players[position] = {}
        score = 0
        for player in lineup:
            if player.position == position:
                position_players[position][player.name] = player.points
            if player.slot_position not in ['BE', 'IR']:
                score += player.points
        position_players[position] = {k: v for k, v in sorted(position_players[position].items(), key=lambda item: item[1], reverse=True)}
        best_lineup[position] = dict(list(position_players[position].items())[:starter_counts[position]])

    # flexes. need to figure out best in other positions first
    for position in starter_counts:
        if 'D/ST' not in position and '/' in position:
            flex = position.split('/')
            for player in lineup:
                if player.position in flex and player.name not in best_lineup[player.position]:
                    position_players[position][player.name] = player.points
        position_players[position] = {k: v for k, v in sorted(position_players[position].items(), key=lambda item: item[1], reverse=True)}
        best_lineup[position] = dict(list(position_players[position].items())[:starter_counts[position]])

    best_score = 0
    for position in best_lineup:
        # print(sum(best_lineup[position].values()))
        best_score += sum(best_lineup[position].values())

    score_pct = 0.0
    if best_score > 0:
        score_pct = (score / best_score) * 100
    return (best_score, score, best_score - score, score_pct)

def get_trophies(league, extra_trophies, week=None):
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
        text += get_random_phrase()

    return '\n'.join(text)

def test_users(league):
    message = []
    for t in league.teams:
        message += ['%s %s %s' % (t.team_name, users[t.team_id], emotes[t.team_id])]

    text = ['**Users:** '] + message + [' '] + get_random_phrase()
    return '\n'.join(text)

def season_trophies(league):
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
            moves_score = '%d adds and %d trades' % (team.acquisitions, team.trades)
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
        high_score_pcts[team] = 0

    starter_counts = get_starter_counts(league)
        
    while z <= len(league.teams[0].scores):
        matchups = league.box_scores(week=z)
        for i in matchups:
            best_score_home = best_lineup_score(i.home_lineup, starter_counts)
            score_diff_totals[i.home_team] += best_score_home[2]
            if best_score_home[3] >= 99:
                high_score_pcts[i.home_team] += 1

            if (i.away_team != 0):
                best_score_away = best_lineup_score(i.away_lineup, starter_counts)
                score_diff_totals[i.away_team] += best_score_away[2]
                if best_score_away[3] >= 99:
                    high_score_pcts[i.away_team] += 1
            
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

    most_high_pcts = [value for key, value in sorted(high_score_pcts.items(), key=lambda item: item[1], reverse=True)[:1:]][0]
    most_high_team = [key for key, value in sorted(high_score_pcts.items(), key=lambda item: item[1], reverse=True)[:1:]][0]

    moves_str = ['**Most Moves**: %s**%s** with %s' % (emotes[moves_team.team_id], moves_team.team_name, moves_score)]
    score_str = ['**Highest Score**: %s**%s** with %.2f points on Week %d' % (emotes[score_team.team_id], score_team.team_name, high_score, score_week)]
    bsd_str = ['**Best Benching**: %s**%s** only left %.2f possible points on the bench' % (emotes[best_score_team.team_id], best_score_team.team_name, best_score_diff)]
    hpt_str = ['**Most Efficient**: %s**%s** scored >99%% of their best possible score on %d weeks' % (emotes[most_high_team.team_id], most_high_team.team_name, most_high_pcts)]
    mvp_str = ['**Best Performance**: %s, Week %d, %s**%s** with %s' % (mvp, mvp_week, emotes[mvp_team.team_id], mvp_team.team_abbrev, mvp_score)]
    lvp_str = ['**Worst Performance**: %s, Week %d, %s**%s** with %s' % (lvp, lvp_week, emotes[lvp_team.team_id], lvp_team.team_abbrev, lvp_score)]
    smvp_str = ['**Season MVP**: %s, %s**%s** with %s' % (smvp, emotes[smvp_team.team_id], smvp_team.team_abbrev, smvp_score)]
    slvp_str = ['**Season LVP**: %s, %s**%s** with %s' % (slvp, emotes[slvp_team.team_id], slvp_team.team_abbrev, slvp_score)]
 
    text = ['__**End of Season Awards:**__ '] + moves_str + score_str + bsd_str + hpt_str + lvp_str + mvp_str + slvp_str + smvp_str + [' ']

    return '\n'.join(text)

def str_to_bool(check):
  return check.lower() in ("yes", "true", "t", "1")

def str_limit_check(text,limit):
    split_str=[]

    if len(text)>limit:
        part_one=text[:limit].split('\n')
        part_one.pop()
        part_one='\n'.join(part_one)

        part_two=text[len(part_one)+1:]

        split_str.append(part_one)
        split_str.append(part_two)
    else:
        split_str.append(text)

    return split_str

def bot_main(function):
    str_limit = 4000

    try:
        discord_webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
        str_limit = 3000
    except KeyError:
        discord_webhook_url = 1

    if len(str(discord_webhook_url)) <= 1:
        #Ensure that there's info for at least one messaging platform,
        #use length of str in case of blank but non null env variable
        raise Exception("No messaging platform info provided. Be sure one of BOT_ID,\
                        SLACK_WEBHOOK_URL, or DISCORD_WEBHOOK_URL env variables are set")

    league_id = os.environ["LEAGUE_ID"]

    try:
        year = int(os.environ["LEAGUE_YEAR"])
    except KeyError:
        year=2022

    try:
        swid = os.environ["SWID"]
    except KeyError:
        swid='{1}'

    if swid.find("{",0) == -1:
        swid = "{" + swid
    if swid.find("}",-1) == -1:
        swid = swid + "}"

    try:
        espn_s2 = os.environ["ESPN_S2"]
    except KeyError:
        espn_s2 = '1'

    try:
        test = str_to_bool(os.environ["TEST"])
    except KeyError:
        test = False

    try:
        top_half_scoring = str_to_bool(os.environ["TOP_HALF_SCORING"])
    except KeyError:
        top_half_scoring = False

    global random_phrase
    try:
        random_phrase = str_to_bool(os.environ["RANDOM_PHRASE"])
    except KeyError:
        random_phrase = False

    global score_warn
    try:
        score_warn = int(os.environ["SCORE_WARNING"])
    except KeyError:
        score_warn = 0

    try:
        extra_trophies = str_to_bool(os.environ["EXTRA_TROPHIES"])
    except KeyError:
        extra_trophies = False

    discord_bot = DiscordBot(discord_webhook_url)

    if swid == '{1}' or espn_s2 == '1': # and espn_username == '1' and espn_password == '1':
        league = League(league_id=league_id, year=year)
    else:
        league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

    global users
    try:
        users += os.environ["USERS"].split(',') 
    except KeyError:
        users += [''] * league.teams[-1].team_id

    global emotes
    try:
        emotes += os.environ["EMOTES"].split(',')
    except KeyError:
        emotes += [''] * league.teams[-1].team_id

    faab = league.settings.faab

    if test:
        print(get_scoreboard_short(league) + "\n")
        print(get_projected_scoreboard(league) + "\n")
        print(get_close_scores(league) + "\n")
        print(get_standings(league, top_half_scoring) + "\n")
        print(best_possible_scores(league) + "\n")
        # print(get_power_rankings(league))
        # print(get_sim_record(league))
        print(combined_power_rankings(league) + "\n")
        print(get_waiver_report(league, faab) + "\n")
        print(get_matchups(league) + "\n")
        print(get_heads_up(league) + "\n")
        print(get_inactives(league) + "\n")
        # print(season_trophies(league) + "\n")
        function="get_final"
        # print(test_users(league))
        # discord_bot.send_message("Testing")

    text = ''
    if function=="get_matchups":
        text = get_matchups(league)
        # text = text + "\n\n" + get_projected_scoreboard(league)
    elif function=="get_heads_up":
        text = get_heads_up(league)
    elif function=="get_inactives":
        text = get_inactives(league)
    elif function=="get_scoreboard_short":
        text = get_scoreboard_short(league)
        text = text + "\n\n" + get_projected_scoreboard(league)
    elif function=="get_projected_scoreboard":
        text = get_projected_scoreboard(league)
    elif function=="get_close_scores":
        text = get_close_scores(league)
    elif function=="get_power_rankings":
        text = combined_power_rankings(league)
    elif function=="get_sim_record":
        text = get_sim_record(league)
    elif function=="get_best_scores":
        text = best_possible_scores(league)
    elif function=="get_waiver_report":
        faab = league.settings.faab
        text = get_waiver_report(league, faab)
    elif function=="get_trophies":
        text = get_trophies(league)
    elif function=="get_standings":
        text = get_standings(league, top_half_scoring)
    elif function=="get_final":
        # on Tuesday we need to get the scores of last week
        week = league.current_week - 1
        text = get_scoreboard_short(league, week=week)
        text = text + "\n\n" + get_trophies(league, extra_trophies, week=week)
    elif function=="season_trophies":
        text = season_trophies(league)
    elif function=="init":
        try:
            text = os.environ["INIT_MSG"]
        except KeyError:
            #do nothing here, empty init message
            pass
    else:
        text = "Something happened. HALP"

    if text != '' and not test:
        messages = str_limit_check(text, str_limit)
        for message in messages:
            discord_bot.send_message(message)

    if test:
        #print "get_final" function
        print(text)

if __name__ == '__main__':
    try:
        ff_start_date = os.environ["START_DATE"]
    except KeyError:
        ff_start_date='2022-09-09'

    try:
        ff_end_date = os.environ["END_DATE"]
    except KeyError:
        ff_end_date='2023-01-04'

    end_date = datetime.strptime(ff_end_date, "%Y-%m-%d").date()

    try:
        my_timezone = os.environ["TIMEZONE"]
    except KeyError:
        my_timezone='America/New_York'

    try:
        tues_sched = str_to_bool(os.environ["TUES_SCHED"])
    except KeyError:
        tues_sched = False

    game_timezone='America/New_York'
    bot_main("init")
    sched = BlockingScheduler(job_defaults={'misfire_grace_time': 15*60})

    #regular schedule:
    #game day score update:              sunday at 4pm, 8pm east coast time.
    #matchups & projections:             thursday evening at 6:30pm east coast time.
    #heads up report:                    friday evening at 6:30pm local time.
    #inactives:                          sunday morning at 12:05pm east coast time.
    #season end trophies:                on the End Date provided at 7:30am local time.
    sched.add_job(bot_main, 'cron', ['get_scoreboard_short'], id='scoreboard2',
        day_of_week='sun', hour='16,20', start_date=ff_start_date, end_date=ff_end_date,
        timezone=game_timezone, replace_existing=True)
    sched.add_job(bot_main, 'cron', ['get_matchups'], id='matchups',
        day_of_week='thu', hour=18, minute=30, start_date=ff_start_date, end_date=ff_end_date,
        timezone=game_timezone, replace_existing=True)
    sched.add_job(bot_main, 'cron', ['get_projected_scoreboard'], id='proj_scoreboard',
        day_of_week='thu', hour=18, minute=30, second=3, start_date=ff_start_date, end_date=ff_end_date,
        timezone=game_timezone, replace_existing=True)
    sched.add_job(bot_main, 'cron', ['get_heads_up'], id='headsup',
        day_of_week='fri', hour=18, minute=30, start_date=ff_start_date, end_date=ff_end_date,
        timezone=my_timezone, replace_existing=True)
    sched.add_job(bot_main, 'cron', ['get_inactives'], id='inactives',
        day_of_week='sun', hour=12, minute=5, start_date=ff_start_date, end_date=ff_end_date,
        timezone=game_timezone, replace_existing=True)
    sched.add_job(bot_main, 'date', ['season_trophies'], id='season_trophies',
        run_date=datetime(end_date.year, end_date.month, end_date.day, 7, 30), 
        timezone=my_timezone, replace_existing=True)

    #schedule without a COVID delay:
    #score update:                       friday and monday morning at 7:30am local time.
    #close scores (within 15.99 points): sunday and monday evening at 6:30pm east coast time.
    #final scores and trophies:          tuesday morning at 7:30am local time.
    #standings, PR, PO%, SR:             tuesday evening at 6:30pm local time.
    #waiver report:                      wed-sun morning at 6:30am local time.
    if tues_sched == False:
        ready_text = "Ready! Regular schedule set."
        sched.add_job(bot_main, 'cron', ['get_scoreboard_short'], id='scoreboard1',
            day_of_week='fri,mon', hour=7, minute=30, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)
        sched.add_job(bot_main, 'cron', ['get_close_scores'], id='close_scores',
            day_of_week='sun,mon', hour=18, minute=30, start_date=ff_start_date, end_date=ff_end_date,
            timezone=game_timezone, replace_existing=True)
        sched.add_job(bot_main, 'cron', ['get_final'], id='final',
            day_of_week='tue', hour=7, minute=30, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)
        sched.add_job(bot_main, 'cron', ['get_standings'], id='standings',
            day_of_week='tue', hour=18, minute=30, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)
        sched.add_job(bot_main, 'cron', ['get_best_scores'], id='best_scores',
            day_of_week='tue', hour=18, minute=30, second=5, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)
        sched.add_job(bot_main, 'cron', ['get_power_rankings'], id='power_rankings',
            day_of_week='tue', hour=18, minute=30, second=10, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)
        sched.add_job(bot_main, 'cron', ['get_waiver_report'], id='waiver_report',
            day_of_week='wed,thu,fri,sat,sun', hour=6, minute=30, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)

    #schedule with a COVID delay to tuesday:
    #extra score update:                 tuesday morning at 7:30am local time.
    #close scores (within 15.99 points): sunday, monday, and tuesday evening at 6:30pm east coast time.
    #final scores and trophies:          wednesday morning at 7:30am local time.
    #standings, PR, PO%, SR:             wednesday evening at 6:30pm local time.
    #waiver report:                      thurs-sun morning at 6:30 local time.
    else:
        ready_text = "Ready! Tuesday schedule set."
        sched.add_job(bot_main, 'cron', ['get_scoreboard_short'], id='scoreboard1',
            day_of_week='fri,mon,tue', hour=7, minute=30, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)
        sched.add_job(bot_main, 'cron', ['get_close_scores'], id='close_scores',
            day_of_week='sun,mon,tue', hour=18, minute=30, start_date=ff_start_date, end_date=ff_end_date,
            timezone=game_timezone, replace_existing=True)
        sched.add_job(bot_main, 'cron', ['get_final'], id='final',
            day_of_week='wed', hour=7, minute=30, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)
        sched.add_job(bot_main, 'cron', ['get_standings'], id='standings',
            day_of_week='wed', hour=18, minute=30, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)
        sched.add_job(bot_main, 'cron', ['get_best_scores'], id='best_scores',
            day_of_week='wed', hour=18, minute=30, second=5, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)
        sched.add_job(bot_main, 'cron', ['get_power_rankings'], id='power_rankings',
            day_of_week='wed', hour=18, minute=30, second=10, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)
        sched.add_job(bot_main, 'cron', ['get_waiver_report'], id='waiver_report',
            day_of_week='thu,fri,sat,sun', hour=6, minute=30, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)

    try:
        if os.environ["SWID"] and os.environ["ESPN_S2"]:
            ready_text += " SWID and ESPN_S2 provided."
    except KeyError:
        ready_text += " SWID and ESPN_S2 not provided."

    print(ready_text)
    sched.start()
