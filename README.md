# ESPN Fantasy Football Discord Chat Bot
![GitHub last commit](https://img.shields.io/github/last-commit/theSeanO/fantasy_football_chat_bot)
![GitHub Release](https://img.shields.io/github/v/release/theSeanO/fantasy_football_chat_bot)
[![Tests](https://github.com/theseano/fantasy_football_chat_bot/actions/workflows/test.yml/badge.svg)](https://github.com/theseano/fantasy_football_chat_bot/actions/workflows/test.yml)
[![Publish image](https://github.com/theseano/fantasy_football_chat_bot/actions/workflows/publish_image.yaml/badge.svg)](https://github.com/theseano/fantasy_football_chat_bot/actions/workflows/publish_image.yaml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Automated league updates in your league's chat: scoreboards, standings, Power Rankings,
weekly trophies, waiver reports, matchup previews, and Players to Monitor - posted on a
schedule so nobody has to open the ESPN app to start an argument.

Main code forked from https://github.com/dtcarls/fantasy_football_chat_bot

---

## Table of Contents

* [What it sends, and when](#what-it-sends-and-when)
* [What's different from the main repo?](#whats-different-from-the-main-repo)
* [Self-hosting](#self-hosting)
  * [What you need](#what-you-need)
  * [1. Set up your chat app](#1-set-up-your-chat-app)
  * [2. Get your ESPN league info](#2-get-your-espn-league-info)
  * [3. Configure](#3-configure)
  * [4. Run it](#4-run-it)
  * [Every season: the rollover checklist](#every-season-the-rollover-checklist)
  * [Running functions on demand](#running-functions-on-demand)
* [User and emote IDs](#user-and-emote-ids)
* [Development](#development)
* [FAQ](#faq)
* [Support](#support)
* [License](#license)

---

## What it sends, and when

Times marked **local** use your `TIMEZONE` setting. Times marked **ET** are always
Eastern, because they're pinned to kickoff windows. Nothing sends outside `START_DATE`
to `END_DATE`, and the bot goes quiet once the league's matchup periods are over.

| Message | Day | Time | What it is |
|---|---|---|---|
| Scoreboard + projections | Sun | 4:00 PM & 8:00 PM ET | Live scores as the afternoon and evening games land |
| Scoreboard + projections | Mon & Fri | 7:30 AM local | Morning recap of Thursday and Sunday |
| Close Scores | Sun & Mon | 6:30 PM ET | Games projected within `CLOSE_SCORES_THRESHOLD` points (15 by default) that still have players to play - the ones to watch on SNF & MNF |
| Final scores + trophies | Tue | 7:30 AM local | Last week's finals plus weekly awards |
| Standings | Tue | 6:30 PM local | Current standings + points for |
| Power Rankings | Tue | 6:30 PM local | Two-step dominance rankings with week-over-week movement, plus Playoff Chance & Simulated Record |
| Optimal Scores | Tue | 6:30 PM local | Each team's optimized score and the % of it that they managed, displayed per matchup |
| Waiver Report | Wed | 7:31 AM local | Every add/drop from the day, with FAAB bids and the outbid rival in FAAB leagues |
| Matchups + projections | Thu | 7:30 PM ET | Next week's matchups with records |
| Monitor Report | Fri | 6:30 PM local | Starters carrying an injury status, on a bye, or projected for 0 - plus anyone parked in an IR slot who isn't IR-eligible |
| Inactives Report | Sun | 12:05 PM ET | One more report of starters to watch, based on the real inactive reports for Sunday's early games |

Optional: `DAILY_WAIVER` moves the Waiver Report to a daily send, and `MONITOR_REPORT`
(on by default) controls the Monitor and Inactives Reports.

---

## What's different from the main repo?

- Mainly, this fork is for **Discord ONLY**. It has custom formatting specifically for Discord, in addition to user tagging and emote support. It also only offers self-hosting options. Check out [GameDayBot.com](https://www.GameDayBot.com/) for hosting options and different subscription tiers. 
- Adds an extra method of determining team dominance, Simulated Record, which calculates how many games a given team would have won had they faced each team every week
- Adds a Waiver Report that provides a quick overview of the adds and drops that have taken place on waiver days *[ESPN_S2 and SWID variables are REQUIRED for this functionality]*
- Adds a Monitor Report, which lets players know if they have any players that they might not want to start
- Adds an Inactive Report, which lets players know when they have players that are designated Out, or would otherwise score them 0 points
- Adds the Optimal Scores report, which tabulates how many points each team could have scored, and how much of that score they got
- Adds another possible Environmental Variable, SCORE_WARNING, which is a number that can be set as a threshold for the Monitor Report
- When provided in the Environmental Variables USERS and EMOTES, bot will display them in the scheduled updates
- Custom formatting changes
- Additional trophies, which will display when the Environmental Variable EXTRA_TROPHIES is set to 1:
  - Week MVP: Player with the highest score differential. Calculated with (actual score - projected score)/projected score
  - Week LVP: Player with the lowest score differential.
  - Overachiever: Team with the highest score over their projected score (actual score - projected score). Awarded when this is different from the highest overall scorer.
  - Underachiever: Team with the lowest score under their projected score. Awarded when this is different from the lowest overall scorer.
  - Plus extra trophies for the end of the season: most moves, highest score, optimal benching, efficiency, best/worst performance, and season MVP/LVP

---
# Self-hosting

> Don't run two copies of the bot in the same chat - you'll double every message. In
> general, let the commissioner do the setup.

## What you need

* **An ESPN fantasy football league** - public, or private with cookies (see below). The
  league must be full for ESPN's API to return usable data.
* **A chat destination** - a GroupMe bot ID, a Slack incoming webhook, and/or a Discord
  webhook. Set as many as you want; each configured platform gets every message.
* **Somewhere to run it 24/7.** The bot is a long-lived process with an internal cron
  scheduler - it has to stay running to send anything. A Raspberry Pi, a VPS, a
  home server, or any container host works.
* **Docker**, or **Python 3.9+** if you'd rather run it directly. The image and CI both
  use 3.11, so that's the best-tested version.

## 1. Set up your chat app

<details>
  <summary><b>Discord</b></summary>

Log in to Discord and open your server's settings.

![](https://i.imgur.com/bDk2ttJ.png)

Go to **Integrations → Webhooks**.

![](https://i.imgur.com/mfFHGbT.png)

Create a webhook, name it, and pick the channel it posts to.

![](https://i.imgur.com/NAJLv6D.png)

Copy the **Webhook URL** - that's `DISCORD_WEBHOOK_URL`.

![](https://i.imgur.com/U4MKZSY.png)
</details>

## 2. Get your ESPN league info

**League ID** - open your league on [fantasy.espn.com](https://fantasy.espn.com) and take
the `leagueId` value out of the URL.

<details>
  <summary><b>Private leagues: ESPN_S2 and SWID</b></summary>

Private leagues need two cookies. Public leagues don't - including for the Waiver
Report, which reads ESPN's transactions endpoint and works unauthenticated.

**The easy way - a Chrome extension.** Install
[ESPN Private League Setup](https://chromewebstore.google.com/detail/espn-private-league-setup/bjmalaafoepfooflcnhjejnopgefjgia),
log in to ESPN, and it reads out your `ESPN_S2` and `SWID` for you. It's published by
gamedaybot.com, and the values work anywhere - here, or on the hosted service.

**By hand, if you'd rather not install anything:**

1. Log in to [fantasy.espn.com](https://fantasy.espn.com) in Chrome or Firefox.
2. Right-click anywhere → **Inspect**.
3. **Application → Storage → Cookies → http://fantasy.espn.com**.
4. Copy the values of `espn_s2` and `SWID`.

`SWID` can be given with or without the surrounding `{}` - the bot adds them if missing.

These cookies expire (and are invalidated when you change your ESPN password). If the bot
suddenly can't see a private league, refresh them first before assuming something worse.
</details>

## 3. Configure

Everything is environment variables. Set at least one chat destination and `LEAGUE_ID`;
the rest have defaults.

| Variable | Required | Default | Description |
|---|---|---|---|
| `LEAGUE_ID` | **Yes** | - | Your ESPN league ID |
| `DISCORD_WEBHOOK_URL` | **Yes** | - | Webhook URL from your Discord channel |
| `LEAGUE_YEAR` | Recommended | `2026` | Season year. **Set it every season** - the default only tracks whichever season this release was cut for, and goes stale the moment the next one starts |
| `START_DATE` | Recommended | `2026-09-10` | Bot stays silent before this date (`YYYY-MM-DD`) |
| `END_DATE` | Recommended | `2027-01-10` | Bot stays silent after this date (`YYYY-MM-DD`) |
| `TIMEZONE` | No | `America/New_York` | [TZ identifier](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List) for the "local" sends |
| `ESPN_S2` | Private leagues | - | ESPN cookie |
| `SWID` | Private leagues | - | ESPN cookie |
| `MONITOR_REPORT` | No | `True` | Friday afternoon & Sunday morning Players to Monitor messages |
| `SCORE_WARNING` | No | 0 | Sets a lower score threshold for the Monitor message |
| `DAILY_WAIVER` | No | `False` | Send the Waiver Report daily rather than only on Wednesday |
| `CLOSE_SCORES_THRESHOLD` | No | `15` | Largest projected point gap that still counts as a close matchup. Lower it for fewer, tighter games. A value that isn't a whole number is ignored |
| `INIT_MSG` | No | - | Message posted on startup. Leave unset for a silent start - the process restarts more often than you'd think |
| `EXTRA_TROPHIES` | No | `False` | Extra trophies will be included when final scores are posted |
| `USERS` | No | - | List of Discord user IDs, comma separated, in the format of \<@[-ID 1 HERE-]\> ,\<@[-ID 2 HERE-]\> ,etc. |
| `EMOTES` | No | - | List of Discord emote IDs, comma separated, in the format of \<:[-Emote shortcut-]:[-Emote ID-]\> ,\<:[-Emote shortcut-]:[-Emote ID-]\> ,etc. |
| `TEST` | No | `False` | Used for troubleshooting -- set to 1 so bot will provide test output instead |

Two older variables, `WAIVER_REPORT` and `TEST`, are still read but no longer do
anything - leave them unset. `RANDOM_PHRASE` and `TOP_HALF_SCORING` have been removed
entirely; if either is still in your config, drop it. If you use `TEST` to troubleshoot, remember to set it back to `False` or `0` when you're finished. 

## 4. Run it

<details open>
  <summary><b>Docker Compose</b> (easiest to keep running)</summary>

Edit the `environment:` block in [`docker-compose.yml`](docker-compose.yml) with your
values, then:

```bash
git clone https://github.com/theseano/fantasy_football_chat_bot
cd fantasy_football_chat_bot
docker compose up -d
```

`restart: always` is already set, so it comes back after a reboot. Logs:
`docker compose logs -f`.
</details>

<details>
  <summary><b>Docker</b></summary>

```bash
git clone https://github.com/theseano/fantasy_football_chat_bot
cd fantasy_football_chat_bot
docker build -t fantasy_football_chat_bot .

docker run -d --restart=always \
  -e LEAGUE_ID=1234567 \
  -e LEAGUE_YEAR=2026 \
  -e START_DATE=2026-09-10 \
  -e END_DATE=2027-01-10 \
  -e TIMEZONE=America/Chicago \
  -e DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..." \
  fantasy_football_chat_bot
```

Prebuilt images are published to GHCR, so you can skip the build:

| Tag | What it points at |
|---|---|
| `ghcr.io/theseano/fantasy_football_chat_bot:latest` | The newest release |
| `ghcr.io/theseano/fantasy_football_chat_bot:v2026.09.10` | One specific release |
| `ghcr.io/theseano/fantasy_football_chat_bot:<commit-sha>` | One specific commit |

Every merge to `main` is built, tested, and released automatically under a dated tag -
`v2026.09.10`, and `v2026.09.10.1` for a second release the same day - which also moves
`latest`. Releases are listed on the
[releases page](https://github.com/theseano/fantasy_football_chat_bot/releases) with
generated notes.

Use `latest` if you'd rather `docker pull` and restart than track version numbers. Pin a
dated tag if you want to choose when you move: `latest` changes whenever `main` does.
</details>

<details>
  <summary><b>Python, no Docker</b></summary>

```bash
git clone https://github.com/theseano/fantasy_football_chat_bot
cd fantasy_football_chat_bot
pip install -r requirements.txt

export LEAGUE_ID=1234567
export LEAGUE_YEAR=2026
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python3 gamedaybot/espn/espn_bot.py
```

This runs in the foreground forever. Use `systemd`, `supervisord`, `tmux`, or anything
else that will restart it - if the process dies, the messages stop.
</details>

**Verify it's alive:** set `INIT_MSG` to anything, start the bot, confirm the message
lands in your chat, then unset it and restart.

## Every season: the rollover checklist

Nothing here is automatic. Before Week 1:

1. Set `LEAGUE_YEAR` to the new season.
2. Set `START_DATE` and `END_DATE` to the new season's window.
3. Refresh `ESPN_S2` / `SWID` if you use a private league - the
   [Chrome extension](https://chromewebstore.google.com/detail/espn-private-league-setup/bjmalaafoepfooflcnhjejnopgefjgia)
   makes this a few seconds.
4. Pull the latest release - ESPN changes their API most years, and the fix usually
   lands in [`espn-api`](https://github.com/cwendt94/espn-api) and gets picked up here.
5. Restart and confirm with an `INIT_MSG`.

If doing this every August is the part you'd rather skip,
[GameDayBot.com](https://www.GameDayBot.com/) handles all five and the mid-season cookie
expiry that isn't on this list.

## Running functions on demand

Every message type is a function name you can call directly - useful for testing without
waiting until Tuesday:

```bash
python3 -c "from gamedaybot.espn.espn_bot import espn_bot; espn_bot('get_standings')"
```

Valid names: `get_scoreboard_short`, `get_projected_scoreboard`, `get_matchups`,
`get_monitor`, `get_close_scores`, `get_power_rankings`, `get_trophies`, `get_standings`,
`get_final`, `get_waiver_report`, `win_matrix`, `trophy_recap`, `init`.

`win_matrix` (how the standings would look if everyone played everyone) and
`trophy_recap` (season-long trophy tally) aren't on the schedule - they're on-demand
only, and they read best at the end of a season.

### User and Emote IDs

If you're using Discord and would like to go to the effort, you can provide lists of your Discord user and emote IDs in the Environment Variables.

- USERS: List of Discord user IDs, comma separated, in the format of \<@[ID 1 HERE]\> ,\<@[ID 2 HERE]\> ,etc.
- EMOTES: List of Discord emote IDs, comma separated, in the format of \<:[Emote shortcut]:[Emote ID]\> ,\<:[Emote shortcut]:[Emote ID]\> ,etc.

Replace the [ ] and the content within with the IDs.

To get IDs, first enable Developer Mode in Discord's Advanced settings.

For Users, just right click the user in the server list and select "Copy ID". User IDs must go in the order of the teams in the league.

Emotes MUST be from the server-specific list. To get the ID, say '\\:[Emote shortcut]:' in any text channel and copy the text that appears.

Both the Users and Emotes lists need to go in order that the teams joined your league. On your league page, go to League -> Members, which will give you a list of teams in this order. Additionally, each team has a team ID that reflects this order. You can visit each team page to make sure your order is correct. If you have deleted a team in the past, then that number does not get reused and you will need to leave their entry in the list blank, with nothing between the commas. For instance, if Team 2 was deleted your list would look like: "ID1 ,,ID3 ,..."

Make sure to include a space before the comma before each user and emote ID, it's important for formatting messages. 

---

## Development

```bash
git clone https://github.com/theseano/fantasy_football_chat_bot
cd fantasy_football_chat_bot

pip install -r requirements.txt
pip install -r requirements-test.txt

pytest                       # run the tests
pytest tests/test_utils.py   # run one file
```

Lint config is in `setup.cfg` (max line length 120). Note the pinned `flake8==3.3.0`
predates Python 3.11 and won't start on it - install a current flake8 to lint.

`tests/dry_run_all_functions.py` prints every message against a real league - handy for
eyeballing formatting changes before they hit a chat full of people.

Pull requests are welcome, especially fixes to ESPN parsing and support for additional
chat platforms.

## FAQ

**The bot isn't sending anything.**
Check, in order: the process is still running; today is between `START_DATE` and
`END_DATE`; `LEAGUE_YEAR` is the current season; your league is full; the webhook still
works (set `INIT_MSG` and restart). If you're still stuck, open an
[issue](https://github.com/theseano/fantasy_football_chat_bot/issues) or ask in the
[Discord](https://discord.gg/VFXSkcgjxh) so the answer helps the next person too. Maybe check the [main repo](https://github.com/dtcarls/fantasy_football_chat_bot/issues) for help as well. 

**The Waiver Report is always empty.**
It only reports waiver transactions from that same day, so a quiet waiver wire produces no
message at all - that's normal, not a failure. It does not need `ESPN_S2`/`SWID`; it
works on public leagues.

**How are Power Rankings calculated?**
Two-step dominance, weighted 80% dominance / 15% average points scored / 5% average
margin of victory. Watch the gaps between teams rather than the raw number.
[Algorithm source](https://github.com/cwendt94/espn-api/pull/12/files) ·
[dominance matrix explainer](https://www.youtube.com/watch?v=784TmwaHPOw).

**How do I change the timezone?**
Set `TIMEZONE` to a [TZ identifier](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List),
e.g. `America/Chicago`. The Sunday scoreboards, Monday Close Scores and Thursday Matchups
stay on Eastern - they're tied to kickoff times, not to your league.

**Is there a version for Yahoo / CBS / NFL.com?**
Not in this repo. [GameDayBot.com](https://www.GameDayBot.com/) supports Sleeper
alongside ESPN.

**Is there a version for Messenger / WhatsApp / Teams?**
No, but pull requests adding a chat platform are welcome - see
[`gamedaybot/chat/`](gamedaybot/chat/) for how small a platform module is.

**Can I run this for two leagues?**
Run a second instance with its own config. One process serves one league. On
[GameDayBot.com](https://www.GameDayBot.com/) a second league is a second subscription in
the same server, with no second anything to deploy.

## Support

* [GitHub issues](https://github.com/theseano/fantasy_football_chat_bot/issues) - bugs and
  feature requests
  * [Main repo issues](https://github.com/dtcarls/fantasy_football_chat_bot/issues) - for more help
* [Discord](https://discord.gg/VFXSkcgjxh) - troubleshooting and release notifications

[![Discord Banner 2](https://discordapp.com/api/guilds/878995504225218620/widget.png?style=banner2)](https://discord.gg/bkShnqTTP8)



## License

[GPL-3.0](LICENSE).

