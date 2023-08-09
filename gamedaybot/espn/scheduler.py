from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from gamedaybot.espn.env_vars import get_env_vars
from gamedaybot.espn.espn_bot import espn_bot


def scheduler():
    """
    This function is used to schedule jobs to send messages.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    data = get_env_vars()
    game_timezone = 'America/New_York'
    sched = BlockingScheduler(job_defaults={'misfire_grace_time': 15 * 60})
    ff_start_date = data['ff_start_date']
    ff_end_date = data['ff_end_date']
    end_date = datetime.strptime(ff_end_date, "%Y-%m-%d").date()
    my_timezone = data['my_timezone']
    ready_text = "Ready!"

    #game day score update:              sunday at 4pm, 8pm east coast time.
    #final scores and trophies:          tuesday morning at 7:30am local time.
    #standings, PR, PO%, SR:             tuesday evening at 6:30pm local time.
    #matchups & projections:             thursday evening at 6:30pm east coast time.
    #heads up report:                    friday evening at 6:30pm local time.
    #inactives:                          sunday morning at 12:05pm east coast time.
    #score update:                       friday and monday morning at 7:30am local time.
    #close scores (within 15.99 points): sunday and monday evening at 6:30pm east coast time.
    #waiver report:                      wed-sun morning at 7:30am local time.
    #season end trophies:                on the End Date provided at 7:30am local time.

    sched.add_job(espn_bot, 'cron', ['get_scoreboard_short'], id='scoreboard2',
        day_of_week='sun', hour='16,20', start_date=ff_start_date, end_date=ff_end_date,
        timezone=game_timezone, replace_existing=True)
    
    sched.add_job(espn_bot, 'cron', ['get_final'], id='final',
        day_of_week='tue', hour=7, minute=30, start_date=ff_start_date, end_date=ff_end_date,
        timezone=my_timezone, replace_existing=True)

    sched.add_job(espn_bot, 'cron', ['get_standings'], id='standings',
        day_of_week='tue', hour=18, minute=30, start_date=ff_start_date, end_date=ff_end_date,
        timezone=my_timezone, replace_existing=True)

    sched.add_job(espn_bot, 'cron', ['get_optimal_scores'], id='optimal_scores',
        day_of_week='tue', hour=18, minute=30, second=5, start_date=ff_start_date, end_date=ff_end_date,
        timezone=my_timezone, replace_existing=True)

    sched.add_job(espn_bot, 'cron', ['get_power_rankings'], id='power_rankings',
        day_of_week='tue', hour=18, minute=30, second=10, start_date=ff_start_date, end_date=ff_end_date,
        timezone=my_timezone, replace_existing=True)

    sched.add_job(espn_bot, 'cron', ['get_matchups'], id='matchups',
        day_of_week='thu', hour=18, minute=30, start_date=ff_start_date, end_date=ff_end_date,
        timezone=game_timezone, replace_existing=True)

    sched.add_job(espn_bot, 'cron', ['get_projected_scoreboard'], id='proj_scoreboard',
        day_of_week='thu', hour=18, minute=30, second=3, start_date=ff_start_date, end_date=ff_end_date,
        timezone=game_timezone, replace_existing=True)

    sched.add_job(espn_bot, 'cron', ['get_heads_up'], id='headsup',
        day_of_week='fri', hour=18, minute=30, start_date=ff_start_date, end_date=ff_end_date,
        timezone=my_timezone, replace_existing=True)

    sched.add_job(espn_bot, 'cron', ['get_inactives'], id='inactives',
        day_of_week='sun', hour=12, minute=5, start_date=ff_start_date, end_date=ff_end_date,
        timezone=game_timezone, replace_existing=True)

    sched.add_job(espn_bot, 'cron', ['get_scoreboard_short'], id='scoreboard1',
        day_of_week='fri,mon', hour=7, minute=30, start_date=ff_start_date, end_date=ff_end_date,
        timezone=my_timezone, replace_existing=True)

    sched.add_job(espn_bot, 'cron', ['get_close_scores'], id='close_scores',
        day_of_week='sun,mon', hour=18, minute=30, start_date=ff_start_date, end_date=ff_end_date,
        timezone=game_timezone, replace_existing=True)

    if data['daily_waiver']:
        sched.add_job(espn_bot, 'cron', ['get_waiver_report'], id='waiver_report',
            day_of_week='wed,thu,fri,sat,sun', hour=6, minute=30, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)  
    else:
        sched.add_job(espn_bot, 'cron', ['get_waiver_report'], id='waiver_report',
            day_of_week='wed', hour=6, minute=30, start_date=ff_start_date, end_date=ff_end_date,
            timezone=my_timezone, replace_existing=True)  

    sched.add_job(espn_bot, 'date', ['season_trophies'], id='season_trophies',
        run_date=datetime(end_date.year, end_date.month, end_date.day, 7, 30), 
        timezone=my_timezone, replace_existing=True)

    try:
        if data['swid'] and data['espn_s2']:
            ready_text += " SWID and ESPN_S2 provided."
    except KeyError:
        ready_text += " SWID and ESPN_S2 not provided."

    print(ready_text)
    sched.start()
