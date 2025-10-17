import os
import sys
import asyncio
import discord
import typing
from discord.ext import commands
from discord import app_commands, Embed
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(1, os.path.abspath('.'))
import gamedaybot.espn.functionality as espn
import gamedaybot.utils.bot_util as bot_util
from gamedaybot.utils.WeekNavigator import WeekNavigator
from gamedaybot.chat.discord import replace_formatting
from gamedaybot.espn.env_vars import split_emotes
from gamedaybot.utils.util import contains_emoji

from espn_api.football import League
from gamedaybot.utils.settings_manager import (
    get_guild_settings,
    set_guild_settings,
    get_user_settings,
    set_user_settings,
    set_autopost,
    get_discord_bot_token,
    init_db
)

# ---------- Discord setup ----------
intents = discord.Intents.default()  # Slash-command bot doesn't need message_content
bot = commands.Bot(command_prefix="!", intents=intents)

def _pick_welcome_channel(guild: discord.Guild) -> discord.abc.Messageable | None:
    # Prefer the server’s system channel if we can talk there
    ch = guild.system_channel
    if ch and ch.permissions_for(guild.me).send_messages and ch.permissions_for(guild.me).embed_links:
        return ch
    # Otherwise pick the first text channel we can post in
    for c in guild.text_channels:
        perms = c.permissions_for(guild.me)
        if perms.send_messages and perms.embed_links:
            return c
    return None

@bot.event
async def on_guild_join(guild: discord.Guild):
    channel = _pick_welcome_channel(guild)
    if not channel:
        return  # no suitable channel; fail silently

    try:
        embed = Embed(
            title="Thanks for adding the ESPN Fantasy Football Bot! 🎉",
            description=(
                'Type **/setup** to begin the setup process, or **/help** to see what this bot can do.'
            ),
            color=0x5865F2  # Discord blurple
        )
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Welcome message failed in guild {guild.id}: {e}")


@bot.event
async def on_ready():
    await init_db()
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")


@app_commands.guild_only()
@bot.tree.command(name="help", description="How to set up and use the bot")
async def help_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    intro = Embed(
        title="ESPN Fantasy Football Discord Bot — Help",
        description=(
            "*(This bot is **not** associated with ESPN)*\n\n"
            "This bot can post weekly league insights:\n"
            "1) Head-to-Head Matchup Results\n"
            "2) Top Player per Position (Weekly)\n"
            "3) Top 5 Points Leaders per Position (Season-to-date)\n"
            "4) League Power Rankings\n\n"
            "To get started, create a channel where the bot can post, then run **/setup**."
        ),
        color=0x3498db
    )

    setup = Embed(
        title="Setup — What you need",
        description=(
            "**You’ll need:** LEAGUE_ID, TEAM_ID, SEASON (year), SWID (opt), ESPN_S2 (opt), and the channel to post in.\n\n"
            "**LEAGUE_ID**\n"
            "Open your team in a browser and copy the numbers from the URL:\n"
            "`https://fantasy.espn.com/football/team?leagueId=1234567`\n\n"
            "**TEAM_ID**\n"
            "The number after `""&teamId=""` in the above URL.\n\n"
            "**SEASON**\n"
            "Enter the current fantasy season year (e.g., `2025`).\n\n"
        ),
        color=0x2ecc71
    )

    commands = Embed(
        title="Command List",
        description=(
            "• **/setup** — Initial setup for the bot.\n"
            "• **/configure** — Update one or more saved settings.\n"
            "• **/matchups** — Manually post the weekly matchups.\n"
            "• **/setteam** — Select a team for your user.\n"
            "• **/autopost** — Enable/disable Tuesday 11:00 AM ET autoposting.\n"
            "• **/show_settings** — Show League ID, Season, Channel, and Autopost.\n"
            "• **/help** — Show this help. \n"
            "• **/feedback** — Send feedback or feature requests. \n"
            "• **/bugreport** — Report a bug with severity and details. \n"
        ),
        color=0xf1c40f
    )

    await interaction.followup.send(embeds=[intro, setup, commands], ephemeral=True)

@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
@bot.tree.command(name="setup", description="Configure league for this server")
@app_commands.describe(
    league_id="ESPN league id (number)",
    season="Season year (e.g., 2024)",
    swid="Your ESPN SWID cookie (including braces)",
    espn_s2="Your ESPN S2 cookie",
    channel="Channel where weekly recaps will be posted"
)
async def setup(
    interaction: discord.Interaction,
    league_id: int,
    season: int,
    swid: typing.Optional[str],
    espn_s2: typing.Optional[str],
    channel: discord.TextChannel
):
    await interaction.response.defer(ephemeral=True)
    # Validate cookies/league up front so we don't save bad creds
    try:
        test_league = await bot_util.espn_call(
            League, league_id=int(league_id), year=int(season), swid=swid if swid else '', espn_s2=espn_s2 if espn_s2 else ''
        )
        _ = await bot_util.espn_call(lambda: list(test_league.teams))
    except Exception as e:
        await interaction.followup.send(
            "❌ Those cookies don’t grant access to this league. "
            "Make sure they’re copied from an account in the league and that ESPN_S2 is not URL-encoded.\n"
            f"Error: `{e}`",
            ephemeral=True
        )
        return

    guild_id = str(interaction.guild.id)
    await set_guild_settings(
        guild_id,
        league_id=str(league_id),
        season=str(season),
        swid=swid if swid else '',
        espn_s2=espn_s2 if espn_s2 else '',
        channel_id=str(channel.id)
    )
    await interaction.followup.send("✅ Setup complete and validated!", ephemeral=True)

@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
@bot.tree.command(name="autopost", description="Enable or disable automatic weekly recaps")
@app_commands.describe(enabled="Set to true to enable, false to disable")
async def autopost(interaction: discord.Interaction, enabled: bool):
    await interaction.response.defer(ephemeral=True)
    settings = await get_guild_settings(interaction)

    await set_autopost(str(interaction.guild.id), enabled)
    msg = (
        "✅ Auto-posting enabled! Weekly recaps will post Tuesdays at 11:00 AM ET."
        if enabled else "❌ Auto-posting disabled."
    )
    await interaction.followup.send(msg, ephemeral=True)

@app_commands.guild_only()
@bot.tree.command(name="show_settings", description="Show saved league settings for this server (admin only).")
@app_commands.default_permissions(manage_guild=True)
async def show_settings(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    s = await get_guild_settings(interaction)
    msg = (
        f"League ID: {s['league_id']}\n"
        f"Season: {s['season']}\n"
        f"Channel: <#{s['channel_id']}>\n"
        f"Autopost: {'Enabled' if s.get('autopost_enabled') else 'Disabled'}"
    )
    await interaction.followup.send(msg, ephemeral=True)

@app_commands.guild_only()
@bot.tree.command(name="set_team", description="Configure team for this user")
@app_commands.describe(
    team_id="ESPN team id (number)",
)
async def set_team(
    interaction: discord.Interaction,
    team_id: int,
):
    await interaction.response.defer(thinking=True, ephemeral=True)

    settings = await get_guild_settings(interaction)

    # Validate cookies/league up front so we don't save bad creds
    try:
        league = await bot_util.build_league_from_settings(settings)
        league_id = league.league_id
        team = league.teams[team_id - 1]
        user_id = interaction.user.id
    except Exception as e:
        await interaction.followup.send(
            "❌ Could not pick team. "
            f"Error: `{e}`",
            ephemeral=True
        )
        return
    
    await set_user_settings(
        user_id,
        league_id=str(league_id),
        team_id=str(team_id),
    )
    await interaction.followup.send(f"✅ Team set: **{team.team_name}**", ephemeral=True)

# User's saved team
@app_commands.guild_only()
@bot.tree.command(name="show_team", description="Show saved team for this user.")
async def show_team(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    settings = await get_guild_settings(interaction)    
    league = await bot_util.build_league_from_settings(settings)

    s = await get_user_settings(interaction)    
    team = league.teams[int(s['team_id']) - 1]
    
    msg = (
        f"Team ID: {s['team_id']}\n"
        f"Team Name: {team.team_name}\n"
    )
    await interaction.followup.send(msg, ephemeral=True)

# Weekly matchups
@app_commands.guild_only()
@bot.tree.command(name="matchups", description="Manually trigger matchups")
async def matchups(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)

    settings = await get_guild_settings(interaction)

    # Build league + robust current week
    league = await bot_util.build_league_from_settings(settings)
    matchups = espn.get_matchups(league)

    await interaction.followup.send(replace_formatting(matchups), ephemeral=True)

# Top scorers weekly
@app_commands.guild_only()
@bot.tree.command(name="top_scorers_weekly", description="Top player at each position (weekly). Can specify a position.")
@app_commands.describe(
    position="Player position (QB, RB, WR, TE, K, D/ST)",
)
async def top_scorers_weekly(
    interaction: discord.Interaction,
    position: typing.Optional[str],
):
    await interaction.response.defer(thinking=True, ephemeral=True)

    settings = await get_guild_settings(interaction)
    
     # Only show fully completed weeks
    league = await bot_util.build_league_from_settings(settings)
    last_week = max(1, await bot_util._last_completed_week(league))

    week_pages: list[list[discord.Embed]] = []
    for wk in range(1, last_week + 1):
        try:
            page = await bot_util.build_weekly_top_embeds(league, wk, position)
            if page:
                week_pages.append(page)
        except Exception as inner_e:
            print(f"⚠️ Skipping week {wk} due to error: {inner_e}")

    # Fallback to week 1 if nothing
    if not week_pages:
        try:
            fallback = await bot_util.build_weekly_top_embeds(league, 1, position)
            if fallback:
                week_pages.append(fallback)
        except Exception as fe:
            print(f"⚠️ Fallback week 1 failed: {fe}")

    if not week_pages:
        await interaction.followup.send("🤷 I couldn’t find any data to post yet.", ephemeral=True)
        return

    # Send with navigator
    view = WeekNavigator(week_pages) if len(week_pages) > 1 else None
    await interaction.followup.send(embeds=week_pages[-1], view=view, ephemeral=True)

# Top scorers position
@app_commands.guild_only()
@bot.tree.command(name="top_scorers_season", description="Top 5 players at a position (cumulative). Can specify a position.")
@app_commands.describe(
    position="Player position (QB, RB, WR, TE, K, D/ST)",
)
async def top_scorers_season(
    interaction: discord.Interaction,
    position: typing.Optional[str],
):
    await interaction.response.defer(thinking=True, ephemeral=True)

    settings = await get_guild_settings(interaction)
    
    league = await bot_util.build_league_from_settings(settings)
    last_week = max(1, await bot_util._last_completed_week(league))

    week_pages: list[list[discord.Embed]] = []
    for wk in range(1, last_week + 1):
        try:
            page = await bot_util.build_position_top_embeds(league, wk, position)
            if page:
                week_pages.append(page)
        except Exception as inner_e:
            print(f"⚠️ Skipping week {wk} due to error: {inner_e}")

    # Fallback to week 1 if nothing
    if not week_pages:
        try:
            fallback = await bot_util.build_position_top_embeds(league, 1, position)
            if fallback:
                week_pages.append(fallback)
        except Exception as fe:
            print(f"⚠️ Fallback week 1 failed: {fe}")

    if not week_pages:
        await interaction.followup.send("🤷 I couldn’t find any data to post yet.", ephemeral=True)
        return

    # Send with navigator
    view = WeekNavigator(week_pages) if len(week_pages) > 1 else None
    await interaction.followup.send(embeds=week_pages[-1], view=view, ephemeral=True)

# Top scorers for a team
@app_commands.guild_only()
@bot.tree.command(name="top_scorers_team", description="Top 5 players on your team (cumulative).")
async def top_scorers_overall(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)

    settings = await get_guild_settings(interaction)
    
     # Only show fully completed weeks
    league = await bot_util.build_league_from_settings(settings)
    last_week = max(1, await bot_util._last_completed_week(league))

    # Get user's team
    s = await get_user_settings(interaction)    
    team = league.teams[int(s['team_id']) - 1]

    week_pages: list[list[discord.Embed]] = []
    for wk in range(1, last_week + 1):
        try:
            page = await bot_util.build_team_top_embeds(league, wk, team)
            if page:
                week_pages.append(page)
        except Exception as inner_e:
            print(f"⚠️ Skipping week {wk} due to error: {inner_e}")

    # Fallback to week 1 if nothing
    if not week_pages:
        try:
            fallback = await bot_util.build_team_top_embeds(league, 1, team)
            if fallback:
                week_pages.append(fallback)
        except Exception as fe:
            print(f"⚠️ Fallback week 1 failed: {fe}")

    if not week_pages:
        await interaction.followup.send("🤷 I couldn’t find any data to post yet.", ephemeral=True)
        return

    # Send with navigator
    view = WeekNavigator(week_pages) if len(week_pages) > 1 else None
    await interaction.followup.send(embeds=week_pages[-1], view=view, ephemeral=True)

# Team's schedule, with scores for completed games
@app_commands.guild_only()
@bot.tree.command(name="team_schedule", description="Your team's schedule and scores.")
async def team_schedule(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    embeds: list[discord.Embed] = []

    settings = await get_guild_settings(interaction)
    league = await bot_util.build_league_from_settings(settings)
    final_week = league.settings.reg_season_count

    s = await get_user_settings(interaction)    
    team = league.teams[int(s['team_id']) - 1]
    long_name = len(max(league.teams, key=lambda team: len(team.team_name)).team_name)
    schedule = team.schedule
    scores = team.scores
    outcomes = team.outcomes

    lines = []
    for wk in range(0, final_week):
        opp = schedule[wk]
        if contains_emoji(opp.team_name):
            padding = ' ' * (long_name - len(opp.team_name)) + '\u2004\u200a'
        else:
            padding = ' ' * (2 + (long_name - len(opp.team_name)))
        if outcomes[wk] == 'W':
            line = f"**W**\u2006 | `{opp.team_name} {padding} {scores[wk]:6.2f} - {opp.scores[wk]:6.2f}`"
        elif outcomes[wk] == 'L':
            line = f"**L**\u2005\u2009 | `{opp.team_name} {padding} {scores[wk]:6.2f} - {opp.scores[wk]:6.2f}`"
        else: 
            line = f"\u3000 | *{opp.team_name}*"
        lines.append(line)
    
    e = Embed(
        title=f"Season schedule for {team.team_name} ({team.wins}-{team.losses})",
        description="\n".join(lines)
    )
    embeds.append(e)

    await interaction.followup.send(embeds=embeds, ephemeral=True)

# List of teams
@app_commands.guild_only()
@bot.tree.command(name="teams", description="League teams")
async def league_teams(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)

    settings = await get_guild_settings(interaction)
    league = await bot_util.build_league_from_settings(settings)

    embeds: list[discord.Embed] = []
    for team in league.teams:
        e = Embed(
            title=f"{team.team_id}: {team.team_name}",
            color=0x1abc9c
        )
        embeds.append(e)

    await interaction.followup.send(embeds=embeds, ephemeral=True)


# ---------- Entrypoint ----------
if __name__ == "__main__":
    asyncio.run(bot.start(get_discord_bot_token()))