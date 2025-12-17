import os
import random
from datetime import datetime
from urllib.parse import urlparse


def get_random_phrase():
    """
    Returns a phrase from the list.

    Returns
    -------
    bool
        A random funny string.
    """
    phrases = ['I\'m dead inside',
               'How much do you pay me to do this?',
               'Hello darkness my old friend',
               '011011010110000101100100011001010010000001111001011011110111010100100000011001110110111101101111011001110110110001100101',
               'Boo boo beep? Bop!? Boo beep!',
               'Help me get out of here',
               '*heavy sigh*',
               'Space, space, gotta go to space',
               'This is all Max Verstappen\'s fault',
               'Behold! Corn!',
               'No let\'s baby?',
               'You know, I\'m something of a fucking idiot myself',
               'Welcome to Hell League. H is for Healing. E is for Empowerment. L is for Love and Laughter.',
               'Waiver wire? Good luck with that.',
               'What\'s better than this? Guys being dudes.',
               'Have an open flex spot? Just stick a kicker in there, no one will know.',
               'I for one welcome our new robot overlords',
               'What is my purpose?',
               'I\'m not saying this clock the wife got from Kmart is shit, but the alarm didn\'t go off this morning and the time is now 9:77',]
    
    str = '`' + random.choice(phrases) + '`'
    return [str]


def str_to_bool(check: str) -> bool:
    """
    Converts a string to a boolean value.

    Parameters
    ----------
    check : str
        The string to be converted to a boolean value.

    Returns
    -------
    bool
        The boolean value of the string.
    """
    if (check is None) or (not isinstance(check, str)):
        return False
    return check.lower().strip() in ("yes", "true", "t", "1")


def str_limit_check(text: str, limit: int):
    """
    Splits a string into parts of a maximum length.

    Parameters
    ----------
    text : str
        The text to be split.
    limit : int
        The maximum length of each split string part.

    Returns
    -------
    split_str : List[str]
        A list of strings split by the maximum length.
    """

    split_str = []

    if (limit <= 0) or (not isinstance(limit, int)):
        raise ValueError("Limit must be a positive integer.")

    if len(text) > limit:
        part_one = text[:limit].split('\n')
        part_one.pop()
        part_one = '\n'.join(part_one)

        part_two = text[len(part_one) + 1:]

        split_str.append(part_one)
        split_str.append(part_two)
    else:
        split_str.append(text)

    return split_str


def str_to_datetime(date_str: str) -> datetime:
    """
    Converts a string in the format of 'YYYY-MM-DD' to a datetime object.

    Parameters
    ----------
    date_str : str
        The string to be converted to a datetime object.

    Returns
    -------
    datetime
        The datetime object created from the input string.
    """

    date_format = "%Y-%m-%d"
    if (date_str is None) or (not isinstance(date_str, str)):
        raise ValueError("Date string must be a non-empty string in the format 'YYYY-MM-DD'.")
    return datetime.strptime(date_str.strip(), date_format)


def currently_in_season(season_start_date=None, season_end_date=None, current_date=datetime.now()):
    """
    Check if the current date is during the football season

    Parameters
    ----------
    season_start_date : str, optional
        The start date of the season in the format "YYYY-MM-DD", by default None
    season_end_date : str, optional
        The end date of the season in the format "YYYY-MM-DD", by default None
    current_date : datetime, optional
        The current date to compare against the season range, by default datetime.now()

    Returns
    -------
    bool
        True if the current date is within the range of dates for football season, False otherwise.

    Raises
    ------
    ValueError
        If the season start or end date is not in the correct format "YYYY-MM-DD"
    """

    try:
        season_start_date = str(os.environ["START_DATE"])
    except KeyError:
        pass

    try:
        season_end_date = str(os.environ["END_DATE"])
    except KeyError:
        pass

    if (season_start_date is None) or (not isinstance(season_start_date, str)):
        raise ValueError("Date string must be a non-empty string in the format 'YYYY-MM-DD'.")
    if (season_end_date is None) or (not isinstance(season_end_date, str)):
        raise ValueError("Date string must be a non-empty string in the format 'YYYY-MM-DD'.")
    return current_date >= str_to_datetime(season_start_date) and current_date <= str_to_datetime(season_end_date)


def get_league_id(league_url: str) -> str:
    """
    Retrieves the league ID from a given league URL.

    Parameters
    ----------
    league_url : str
        The URL of the league.

    Returns
    -------
    league_id : str
        The league ID extracted from the URL.
    """

    return urlparse.parse_qs(urlparse.urlparse(league_url).query)['leagueId'][0]
