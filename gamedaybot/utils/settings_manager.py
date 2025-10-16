# settings_manager.py
import os
import aiosqlite
import discord
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Use a persistent path if provided; default to local file for dev
DB_PATH = os.getenv("SETTINGS_DB_PATH", "settings.db")

# Ensure the directory exists if a path like /data/settings.db is used
_db_dir = os.path.dirname(DB_PATH)
if _db_dir:
    Path(_db_dir).mkdir(parents=True, exist_ok=True)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id TEXT PRIMARY KEY,
                league_id TEXT,
                season TEXT,
                swid TEXT,
                espn_s2 TEXT,
                channel_id TEXT,
                autopost_enabled INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY,
                league_id TEXT,
                team_id TEXT
            )
        """)
        await db.commit()


async def set_guild_settings(guild_id, league_id, season, swid, espn_s2, channel_id):
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO guild_settings (
                guild_id, league_id, season, swid, espn_s2, channel_id, autopost_enabled
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                COALESCE((SELECT autopost_enabled FROM guild_settings WHERE guild_id = ?), 0)
            )
        """, (str(guild_id), league_id, season, swid, espn_s2, channel_id, str(guild_id)))
        await db.commit()

async def get_guild_settings(interaction: discord.Interaction):
    await init_db()
    guild_id = str(interaction.guild.id)
    settings = None
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT league_id, season, swid, espn_s2, channel_id, autopost_enabled
            FROM guild_settings
            WHERE guild_id = ?
        """, (str(guild_id),)) as cursor:
            row = await cursor.fetchone()
            if row:
                settings = {
                    "league_id": int(row[0]),
                    "season": int(row[1]),
                    "swid": row[2],
                    "espn_s2": row[3],
                    "channel_id": int(row[4]),
                    "autopost_enabled": bool(row[5])
                }

    if settings == None:
        await interaction.followup.send("❌ This server hasn't been set up. Use `/setup` first.", ephemeral=True)
        return
    
    return settings
        
async def set_user_settings(user_id, league_id, team_id):
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO user_settings (
                user_id, league_id, team_id
            )
            VALUES (
                ?, ?, ?
            )
        """, (str(user_id), league_id, team_id,))
        await db.commit()

async def get_user_settings(interaction: discord.Interaction):
    await init_db()
    user_id = str(interaction.user.id)
    team = None
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, league_id, team_id
            FROM user_settings
            WHERE user_id = ?
        """, (str(user_id),)) as cursor:
            row = await cursor.fetchone()
            if row:
                team = {
                    "user_id": int(row[0]),
                    "league_id": int(row[1]),
                    "team_id": row[2]
                }
    
    if team == None:
        await interaction.followup.send("❌ No team saved yet. Use `/teams` to view, then `/set_team`.", ephemeral=True)
        return
    
    return team

async def set_autopost(guild_id, enabled):
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE guild_settings SET autopost_enabled = ? WHERE guild_id = ?",
            (int(enabled), str(guild_id))
        )
        await db.commit()

def get_discord_bot_token():
    return os.environ.get("DISCORD_TOKEN")
