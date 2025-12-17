import re

def clean_team_name(name):
    # This regex pattern will match any character outside the regular ASCII range
    cleaned_name = re.sub(r'[^\x00-\x7F]+', '', name)
    return cleaned_name.strip()

# Step 1: Basic Data Extraction
def extract_players_weekly_scores(league, week):
    """
    Extract all players and their weekly scores for a given week.
    
    Args:
    - league (League): The league object.
    - week (int): The week number.
    
    Returns:
    - List[BoxScore]: List of box scores containing player scores for the given week.
    """
    return league.box_scores(week)


# Step 2: Top/Bottom Stats
def top_scorer_of_week(league, week):
    """
    Determines the top scoring player of a given week.
    
    Args:
    - league (League): The league object.
    - week (int): The week number.
    
    Returns:
    - Tuple(Player, float): Top scoring player and their score.
    """
    box_scores = extract_players_weekly_scores(league, week)
    
    max_score = float('-inf')
    top_player = None
    team = None
    
    for box_score in box_scores:
        # Checking players from both home and away teams
        for player in box_score.home_lineup:
            if player.points > max_score:
                max_score = player.points
                top_player = player
                team = box_score.home_team
        for player in box_score.away_lineup:
            if player.points > max_score:
                max_score = player.points
                top_player = player
                team = box_score.away_team

    return top_player, max_score, team


def worst_scorer_of_week(league, week):
    """
    Determines the worst scoring player of a given week.
    
    Args:
    - league (League): The league object.
    - week (int): The week number.
    
    Returns:
    - Tuple(Player, float): Worst scoring player and their score.
    """
    box_scores = extract_players_weekly_scores(league, week)
    
    min_score = float('inf')
    worst_player = None
    team = None
    
    for box_score in box_scores:
        # Checking players from both home and away teams
        for player in box_score.home_lineup:
            # Ignore players in the IR slot
            if player.slot_position == 'IR':
                continue
            if player.points < min_score:
                min_score = player.points
                worst_player = player
                team = box_score.home_team
        for player in box_score.away_lineup:
            # Ignore players in the IR slot
            if player.slot_position == 'IR':
                continue
            if player.points < min_score:
                min_score = player.points
                worst_player = player
                team = box_score.away_team
                
    return worst_player, min_score, team


def top_scorer_of_season(league):
    """
    Determines the top scoring player of the season using the total_points attribute.
    
    Args:
    - league (League): The league object.
    
    Returns:
    - Tuple(Player, float): Top scoring player and their score for the season.
    """
    
    max_score = float('-inf')
    top_player = None
    top_team = None
    
    # Iterating over all teams in the league
    for team in league.teams:
        # Iterating over each player in the team's roster
        for player in team.roster:
            if player.total_points > max_score:
                max_score = player.total_points
                top_player = player
                top_team = team
                
    return top_player, max_score, top_team


# Step 4: Player Bench/Starting Stats.
def highest_scoring_benched_player(league, current_week):
    """
    Identify the benched player who scored the most points for a given week and the team that rosters them.
    
    Args:
    - league (League): The league object.
    - current_week (int): The week number.
    
    Returns:
    - Tuple: Player object representing the highest scoring benched player and the Team object representing the team that rosters them.
    """
    box_scores = league.box_scores(current_week)
    benched_highest_player = None
    benched_highest_points = float('-inf')

    for box_score in box_scores:
        for player in box_score.home_lineup + box_score.away_lineup:
            if player.slot_position == 'BE' and player.points > benched_highest_points:
                benched_highest_points = player.points
                benched_highest_player = (player, box_score.home_team if player in box_score.home_lineup else box_score.away_team)

    return benched_highest_player

def lowest_scoring_starting_player(league, current_week):
    """
    Identify the starting player who scored the least points for a given week and the team that rosters them.
    
    Args:
    - league (League): The league object.
    - current_week (int): The week number.
    
    Returns:
    - Tuple: Player object representing the lowest scoring starting player and the Team object representing the team that rosters them.
    """
    box_scores = league.box_scores(current_week)
    current_week_lowest_player = None
    current_week_lowest_points = float('inf')

    for box_score in box_scores:
        for player in box_score.home_lineup + box_score.away_lineup:
            if player.slot_position != 'BE' and player.slot_position != 'IR':
                if player.points < current_week_lowest_points:
                    current_week_lowest_points = player.points
                    current_week_lowest_player = (player, box_score.home_team if player in box_score.home_lineup else box_score.away_team)

    return current_week_lowest_player

# Step 5: Match Stats
def biggest_blowout_match(league, week):
    """
    Identifies the biggest blowout match of the current week.
    
    Args:
    - league (League): The league object.
    - week (int): The week number.
    
    Returns:
    - BoxScore: Box score of the match with the largest score difference.
    """
    box_scores = league.box_scores(week)
    max_diff = float('-inf')
    blowout_match = None

    for match in box_scores:
        diff = abs(match.home_score - match.away_score)
        if diff > max_diff:
            max_diff = diff
            blowout_match = match

    if blowout_match:
        return blowout_match
        # return f"Box Score({blowout_match.home_team.team_name} ({blowout_match.home_score}) at {blowout_match.away_team.team_name} ({blowout_match.away_score}))"
    return None


def closest_game_match(league, week):
    """
    Identifies the closest game of the current week.
    
    Args:
    - league (League): The league object.
    - week (int): The week number.
    
    Returns:
    - BoxScore: Box score of the match with the smallest score difference.
    """
    box_scores = league.box_scores(week)
    min_diff = float('inf')
    closest_match = None

    for match in box_scores:
        diff = abs(match.home_score - match.away_score)
        if diff < min_diff:
            min_diff = diff
            closest_match = match

    if closest_match:
        # return f"Box Score({closest_match.home_team.team_name} ({closest_match.home_score}) at {closest_match.away_team.team_name} ({closest_match.away_score}))"
        return closest_match
    return None


def highest_scoring_team(league: int, week: int):
    """
    Determines the top scoring team of the week.

    Parameters:
    - league: An instance of the League class and week number
    
    Returns:
    - Tuple(Team, float): Top scoring team and their score.

    """
    # Get the matchups for the specified week
    matchups = league.scoreboard(week)
    
    # Determine the team with the highest score for the week
    max_score = 0
    top_team = None
    for matchup in matchups:
        if matchup.home_score > max_score:
            max_score = matchup.home_score
            top_team = matchup.home_team
        if matchup.away_score > max_score:
            max_score = matchup.away_score
            top_team = matchup.away_team
    
    # Return the team name and score in the desired format
    return top_team, max_score

def lowest_scoring_team(league: int, week: int):
    """
    Determines the worst scoring team of the week.
    
    Parameters:
    - league: An instance of the League class and week number
    
    Returns:
    - Tuple(Team, float): Worst scoring team and their score.

    """
    # Get the matchups for the specified week
    matchups = league.scoreboard(week)
    
    # Determine the team with the highest score for the week
    low_score = 9999999
    low_team = None
    for matchup in matchups:
        if matchup.home_score < low_score:
            low_score = matchup.home_score
            low_team = matchup.home_team
        if matchup.away_score < low_score:
            low_score = matchup.away_score
            low_team = matchup.away_team
    
    # Return the team name and score in the desired format
    return low_team, low_score