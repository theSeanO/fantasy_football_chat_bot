import os
import sys
import asyncio
import discord
import typing
from collections import defaultdict
from discord import Webhook
from discord.ext import commands
from discord.ui import Button, View, Select
from discord import app_commands, Embed
from discord.app_commands import checks as app_checks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(1, os.path.abspath('.'))
import gamedaybot.espn.functionality as espn
from gamedaybot.chat.discord import replace_formatting

from espn_api.football import League
from settings_manager import (
    get_guild_settings,
    set_guild_settings,
    set_autopost,
    get_discord_bot_token,
    init_db
)

# ---------- Discord setup ----------
intents = discord.Intents.default()  # Slash-command bot doesn't need message_content
bot = commands.Bot(command_prefix="!", intents=intents)

# Scheduler in ET (DST-aware): Tuesdays @ 11:00 AM
scheduler = AsyncIOScheduler(timezone=ZoneInfo("America/New_York"))

#Webhook URLs for home server
HOME_BUGS_WEBHOOK_URL = os.getenv("HOME_BUGS_WEBHOOK_URL", "")
HOME_FEEDBACK_WEBHOOK_URL = os.getenv("HOME_FEEDBACK_WEBHOOK_URL", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# ---------- Global ESPN concurrency gate ----------
ESPN_MAX_CONCURRENCY = int(os.getenv("ESPN_MAX_CONCURRENCY", "1"))       # how many ESPN calls at once
ESPN_TIMEOUT_SECONDS = int(os.getenv("ESPN_TIMEOUT_SECONDS", "25"))       # per-call timeout
_ESPN_GATE = asyncio.Semaphore(ESPN_MAX_CONCURRENCY)

async def espn_call(func, *args, **kwargs):
    """
    Run a blocking espn_api call in a worker thread with:
      - global concurrency limit (queue instead of fail)
      - timeout guard
    """
    async with _ESPN_GATE:
        return await asyncio.wait_for(
            asyncio.to_thread(func, *args, **kwargs),
            timeout=ESPN_TIMEOUT_SECONDS
        )
    
# ---- Global job queue (all guilds share this) ----
_GLOBAL_QUEUE: asyncio.Queue[discord.Interaction] = asyncio.Queue()
_GLOBAL_WORKERS: list[asyncio.Task] = []

# Still keep a per-guild lock so two jobs from the SAME server don't overlap
_GUILD_LOCKS = defaultdict(lambda: asyncio.Lock())

# How many jobs to process in parallel (separate from ESPN_MAX_CONCURRENCY)
QUEUE_WORKERS = int(os.getenv("QUEUE_WORKERS", "1"))  # 1 = strict FIFO; >1 = parallel consumption

# ---------- ESPN image/constants ----------
PLAYER_IMG = "https://a.espncdn.com/i/headshots/nfl/players/full/{player_id}.png"
TEAM_IMG = "https://a.espncdn.com/i/teamlogos/nfl/500/{code}.png"

TEAM_LOGO = {
    "49ers": "sf", "Bears": "chi", "Bengals": "cin", "Bills": "buf", "Broncos": "den",
    "Browns": "cle", "Buccaneers": "tb", "Cardinals": "ari", "Chargers": "lac", "Chiefs": "kc",
    "Colts": "ind", "Commanders": "wsh", "Cowboys": "dal", "Dolphins": "mia", "Eagles": "phi",
    "Falcons": "atl", "Giants": "nyg", "Jaguars": "jax", "Jets": "nyj", "Lions": "det",
    "Packers": "gb", "Panthers": "car", "Patriots": "ne", "Raiders": "lv", "Rams": "lar",
    "Ravens": "bal", "Saints": "no", "Seahawks": "sea", "Steelers": "pit", "Texans": "hou",
    "Titans": "ten", "Vikings": "min"
}
DESIRED_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST']

async def build_league_from_settings(settings) -> League:
    # espn_api does network IO in League(...), so offload it too
    return await espn_call(
        League,
        league_id=int(settings["league_id"]),
        year=int(settings["season"]),
    )

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
    _ensure_global_workers()   # <--- start workers
    scheduler.start()
    print(f"✅ Logged in as {bot.user}")

def _ensure_global_workers():
    # Start exactly QUEUE_WORKERS background tasks
    alive = [t for t in _GLOBAL_WORKERS if not t.done()]
    missing = max(0, QUEUE_WORKERS - len(alive))
    for _ in range(missing):
        _GLOBAL_WORKERS.append(asyncio.create_task(_global_worker()))

async def _global_worker():
    while True:
        interaction: discord.Interaction = await _GLOBAL_QUEUE.get()
        try:
            # Per-guild mutex so same guild requests don't overlap
            async with _GUILD_LOCKS[interaction.guild.id]:
                await _process_weeklyrecap(interaction)
        except Exception as e:
            try:
                await interaction.followup.send(
                    f"❌ Error while processing queued recap: `{e}`",
                    ephemeral=True
                )
            except Exception:
                pass
        finally:
            _GLOBAL_QUEUE.task_done()

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
            "**You’ll need:** LEAGUE_ID, SEASON (year), SWID, ESPN_S2, and the channel to post in.\n\n"
            "**LEAGUE_ID**\n"
            "Open your league in a browser and copy the numbers from the URL:\n"
            "`https://fantasy.espn.com/football/league?leagueId=1234567`\n\n"
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
            "• **/weeklyrecap** — Manually post the weekly recap.\n"
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
        test_league = await espn_call(
            League, league_id=int(league_id), year=int(season), swid=swid if swid else '', espn_s2=espn_s2 if espn_s2 else ''
        )
        _ = await espn_call(lambda: list(test_league.teams))
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
    settings = await get_guild_settings(str(interaction.guild.id))
    if not settings:
        await interaction.followup.send("❌ This server hasn't been set up. Use `/setup` first.", ephemeral=True)
        return

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
    s = await get_guild_settings(str(interaction.guild.id))
    if not s:
        await interaction.followup.send("No settings saved yet. Use `/setup`.", ephemeral=True)
        return
    msg = (
        f"League ID: {s['league_id']}\n"
        f"Season: {s['season']}\n"
        f"Channel: <#{s['channel_id']}>\n"
        f"Autopost: {'Enabled' if s.get('autopost_enabled') else 'Disabled'}"
    )
    await interaction.followup.send(msg, ephemeral=True)

# Weekly recap (with per-guild lock)
@app_commands.guild_only()
@bot.tree.command(name="matchups", description="Manually trigger matchups")
async def matchups_slash(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)

    settings = await get_guild_settings(str(interaction.guild.id))
    if not settings:
        await interaction.followup.send("❌ This server hasn't been set up. Use `/setup` first.", ephemeral=True)
        return

    channel = (
        interaction.guild.get_channel(int(settings["channel_id"]))
        if settings.get("channel_id") else interaction.channel
    )
    perms = channel.permissions_for(interaction.guild.me)
    if not perms.send_messages or not perms.embed_links:
        await interaction.followup.send(
            f"❌ I don’t have permission to post embeds in {channel.mention}.",
            ephemeral=True
        )
        return

    # Build league + robust current week
    league = await build_league_from_settings(settings)
    matchups = espn.get_matchups(league)

    await interaction.followup.send(replace_formatting(matchups), ephemeral=True)


# ---------- Entrypoint ----------
if __name__ == "__main__":
    asyncio.run(bot.start(get_discord_bot_token()))