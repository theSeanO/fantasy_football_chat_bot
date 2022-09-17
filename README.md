For troubleshooting, join the Discord!

[![Discord Banner 2](https://discordapp.com/api/guilds/878995504225218620/widget.png?style=banner2)](https://discord.gg/bkShnqTTP8)

# ESPN Fantasy Football Discord Chat Bot

This package creates a docker container that runs a Discord chat bot to send ESPN Fantasy Football information to a Discord chat room.

Main code forked from https://github.com/dtcarls/fantasy_football_chat_bot

**What are the differences from the main repo?**

- Adds an extra method of determining team dominance, Simulated Record, which calculates how many games a given team would have won had they faced each team every week
- Adds a Waiver Report that provides a quick overview of the adds and drops that have taken place on waiver days *[ESPN_S2 and SWID variables are REQUIRED for this functionality]*
- Adds a Heads Up Report, which lets players know if they have any players that they might not want to start
- Adds an Inactive Report, which lets players know when they have players that are designated Out, or would otherwise score them 0 points
- Adds the Best Possible Scores report, which tabulates how many points each team could have scored, and how much of that score they got
- Adds a possible Environmental Variable, TUES_SCHED, which can be activated if a game is delayed until Tuesday for COVID-19, and moves all scheduled jobs up a day
- Adds another possible Environmental Variable, SCORE_WARNING, which is a number that can be set as a threshold for the Heads Up Report
- Adds extra places for the fun random phrases that can be activated with the variable RANDOM_PHRASE
- When provided in the Environmental Variables USERS and EMOTES, bot will display them in the scheduled updates
- Custom formatting changes
- Custom forks and changes for my two leagues
- Additional trophies, which will display when the Environmental Variable EXTRA_TROPHIES is set to 1:
  - Week MVP: Player with the highest score differential. Calculated with (actual score - projected score)/projected score
  - Week LVP: Player with the lowest score differential.
  - Overachiever: Team with the highest score over their projected score (actual score - projected score). Awarded when this is different from the highest overall scorer.
  - Underachiever: Team with the lowest score under their projected score. Awarded when this is different from the lowest overall scorer.


**What does this do?**

- Sends out the following messages on this schedule:
- Scoreboard - Sun - 16:00, 20:00 east coast time (Current ESPN fantasy scoreboard)
- Scoreboard - Mon,Fri - 7:30 local time (Current ESPN fantasy scoreboard)
- Close Scores - Sun,Mon - 18:30 east coast time (Games that are within 16 points to keep an eye on during the Sunday & Monday night games)
- Final scores and Trophies- Tue - 7:30 local time
- Current standings - Tue - 18:30 local time
- Power rankings - Tue - 18:30 local time
- Best possible scores - Tue - 18:30 local time
- Waiver report - Wed - 7:30 local time
- Heads up report - Wed - 18:30 local time
- Matchups - Thu - 18:30 east coast time (Upcoming matchups before Thursday night game)
- Inactive player report - Sun - 12:05 east coast time (Right after inactive reports for the first games on Sunday)

Table of Contents
=================

  * [Setting up Discord and deploying app in Heroku](#setting-up-discord-and-deploying-app-in-heroku)
     * [Discord setup](#discord-setup)
     * [Heroku setup](#heroku-setup)
     * [User and Emote IDs](#user-and-emote-ids)
     * [Private Leagues](#private-leagues)
  * [Troubleshooting / FAQ](#troubleshooting--faq)
  * [Self Hosting, Development and Testing](#self-hosting-development-and-testing)

## Setting up Discord and deploying app in Heroku

**Do not deploy 2 of the same bot in the same chat. In general, you should let your commissioner do the setup**

### Discord setup
 <details>
  <summary>Click to expand!</summary>

Log into or create a Discord account

Go to or create a Discord server to receive messages in

Open the server settings

![](https://i.imgur.com/bDk2ttJ.png)

Go to Webhooks

![](https://i.imgur.com/mfFHGbT.png)

Create a webhook, give it a name and pick which channel to receive messages in

![](https://i.imgur.com/NAJLv6D.png)

Save the "Webhook URL" on this page

![](https://i.imgur.com/U4MKZSY.png)
</details>

### Heroku setup

Heroku is what we will be using to host the chat bot

**Starting November 28, 2022, Heroku plans to stop offering free product plans and plans to start shutting down free dynos and data services.** 
The original creator of this bot offers a hosting service for lower than the new costs of Heroku at https://www.GameDayBot.com/

You will lose some features of this fork (Discord formatting w/ emotes & user tagging, extra options, extra trophies), but I have worked with the original fork to implement a few of my changes. 

Go to https://id.heroku.com/login and sign up or login


:warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning:

:rotating_light:**Click this purple button to automatically deploy the code:**:rotating_light:

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

:warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning::warning:

Go to your dashboard (https://dashboard.heroku.com/apps)
Now you will need to setup your environment variables so that it works for your league. Click Settings at your dashboard. Then click "Reveal Config Vars" button and you will see something like this.

![](https://i.imgur.com/7a1V6v8.png)

Now we will need to edit these variables. (click the pencil to the right of the variable to modify)
See [Environment Variables Section](#environment-variables) for documentation on each variable. 

Note: App will restart when you change any variable, so your chat room may be semi-spammed with the init message of "Hi". 
You can change the INIT_MSG variable to be blank to have no init message. 
It should also be noted that Heroku seems to restart the app about once a day

After you have set up your variables you will need to turn it on. Navigate to the "Resources" tab of your Heroku app Dashboard.
You should see something like below. Click the pencil on the right and toggle the buton so it is blue like depicted and click "Confirm."
![](https://i.imgur.com/J6bpV2I.png)

You're done! You now have a fully featured GroupMe/Slack/Discord chat bot for ESPN leagues! If you have an INIT_MSG you will see it exclaimed in your GroupMe, Discord, or Slack chat room.

Unfortunately to do auto deploys of the latest version you need admin access to the repository on git. You can check for updates on the github page (https://github.com/dtcarls/ff_bot/commits/master) and click the deploy button again; however, this will deploy a new instance and the variables will need to be edited again.

### Environment Variables

<details>
  <summary>Click to expand!</summary>

- DISCORD_WEBHOOK_URL: This is your Webhook URL from the Discord Settings page (REQUIRED)
- LEAGUE_ID: This is your ESPN league id (REQUIRED)
- START_DATE: This is when the bot will start paying attention and sending messages to your chat.
- END_DATE: This is when the bot will stop paying attention and stop sending messages to your chat.
- LEAGUE_YEAR: ESPN League year to look at
- TIMEZONE: The timezone that the messages will look to send in. (America/New_York by default)
- INIT_MSG: The message that the bot will say when it is started (“Hi” by default, leave blank for no message)
- TOP_HALF_SCORING: If set to True, when standings are posted on Wednesday it will also include top half scoring wins
- RANDOM_PHRASE: If set to True, when matchups, heads up report, inactive report, waiver report, and final scores are posted, will include a random phrase from a list
- EXTRA_TROPHIES: If set to True, when extra trophies will be included when final scores are posted
- SCORE_WARNING: Assign a score value for the Heads Up report to warn users about (default is 0)
- TUES_SCHED: If set to True, will move updates accordingly for a COVID delayed game to Tuesday
- ESPN_S2: **Required** for private leagues. See [Private Leagues Section](#private-leagues) for documentation
- SWID: **Required** for private leagues. See [Private Leagues Section](#private-leagues) for documentation
- USERS: List of Discord user IDs, comma separated, in the format of \<@[-ID 1 HERE-]\> ,\<@[-ID 2 HERE-]\> ,etc.
- EMOTES: List of Discord emote IDs, comma separated, in the format of \<:[-Emote shortcut-]:[-Emote ID-]\> ,\<:[-Emote shortcut-]:[-Emote ID-]\> ,etc.
- TEST: Used for troubleshooting--set to 1 so bot will provide test output instead

</details>

### User and Emote IDs

<details>
  <summary>Click to expand!</summary>

If you're using Discord and would like to go to the effort, you can provide lists of your Discord user and emote IDs in the Environment Variables.

- USERS: List of Discord user IDs, comma separated, in the format of \<@[ID 1 HERE]\> ,\<@[ID 2 HERE]\> ,etc.
- EMOTES: List of Discord emote IDs, comma separated, in the format of \<:[Emote shortcut]:[Emote ID]\> ,\<:[Emote shortcut]:[Emote ID]\> ,etc.

Replace the [ ] and the content within with the IDs.

To get IDs, first enable Developer Mode in Discord's Advanced settings.

For Users, just right click the user in the server list and select "Copy ID". User IDs must go in the order of the teams in the league.

Emotes MUST be from the server-specific list. To get the ID, say '\\:[Emote shortcut]:' in any text channel and copy the text that appears.

Both the Users and Emotes lists need to go in order that the teams joined your league. On your league page, go to League -> Members, which will give you a list of teams in this order. Additionally, each team has a team ID that reflects this order. You can visit each team page to make sure your order is correct. If you have deleted a team in the past, then that number does not get reused and you will need to leave their entry in the list blank, with nothing between the commas. For instance, if Team 2 was deleted your list would look like: "ID1 ,,ID3 ,..."

Make sure to include a space before the comma before each user and emote ID, it's important for formatting messages. 

</details>

### Private Leagues

<details>
  <summary>Click to expand!</summary>

For private league you will need to get your swid and espn_s2.
You can find these two values after logging into your espn fantasy football account on espn's website.
(Chrome Browser)
Right click anywhere on the website and click inspect option.
From there click Application on the top bar.
On the left under Storage section click Cookies then http://fantasy.espn.com.
From there you should be able to find your swid and espn_s2 variables and values.

There is a new **Experimental (may not work)** option to use a username and password for espn to access private leagues instead of having to use swid and s2.

</details>

## Troubleshooting / FAQ

<details>
  <summary>Click to expand!</summary>

**League must be full.**

The bot isn't working
Did you miss a step in the instructions? Try doing it from scratch again. If still no luck, open an issue (https://github.com/dtcarls/fantasy_football_chat_bot/issues) so the answer can be shared with others.

How are power ranks calculated?
They are calculated using 2 step dominance, as well as a combination of points scored and margin of victory. Weighted 80/15/5 respectively. I wouldn't so much pay attention to the actual number but more of the gap between teams. Full source of the calculations can be seen here: https://github.com/cwendt94/ff-espn-api/commit/61f8a34de5c42196ba0b1552aa25282297f070c5

Is there a version of this for Yahoo/CBS/NFL/[insert other site]?
No, this would require a significant rework for other sites.

I'm not getting the init message
Are you sure you flipped the switch in Heroku to activate the worker (the toggle should be blue)? The other common mistake is misconfigured environment variables.

I keep getting the init message
Remove your init message and it will stop. The init message is really for first setup to ensure it is working.

How do I set another timezone?
Specify your variable https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List

Is there a version of this for Messenger/WhatsApp/[insert other chat]?
No, but I am open to pull requests implementing their API for additional cross platform support.
</details>

## Self Hosting, Development, and Testing

<details>
  <summary>Click to expand!</summary>

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Clone the repo
First and foremost, clone a copy of this repo to your machine:
``` bash 
git clone https://github.com/sdvgallardo/fantasy_football_chat_bot-vS.git ff_bot
```

### With Docker:

To host with Docker, fill in `docker-compose.yml` with your [Environment Variables](#environment-variables). Variables with "" *must* be wrapped in quotes.

If you are running Docker on a Raspberry Pi, you will need to change the Python image in the Dockerfile to `slim-buster`
```bash
cd ff_bot
docker compose up -d
```

#### Restarting Docker
If changes are made to the bot, or you adjust your environment variables, you will need to stop and recompose the container:
```bash
cd ff_bot
docker stop [container name]
docker compose up -d
```


### Without Docker:
You can also directly run just the Python script.

Start by running the install:
```bash
cd ff_bot
python3 setup.py install
```
You may also need to install the required dependencies with `pip install -r requirements.txt`.

Then, export your environment variables and run `ff_bot.py`.

```bash
export DISCORD_WEBHOOK_URL=[enter your Webhook URL]
export LEAGUE_ID=[enter ESPN league ID]
export LEAGUE_YEAR=[enter league year]
cd ff_bot
python3 ff_bot/ff_bot.py
```

### Running the tests

Automated tests for this package are included in the `tests` directory. After installation, you can run these tests by changing the directory to the `ff_bot` directory and running the following:

```python3
python3 setup.py test
```
</details>
