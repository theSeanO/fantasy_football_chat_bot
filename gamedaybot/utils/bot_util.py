
import os
import asyncio
import discord
from discord import Embed
from espn_api.football import League

# ---------- Global ESPN concurrency gate ----------
ESPN_MAX_CONCURRENCY = int(os.getenv("ESPN_MAX_CONCURRENCY", "1"))       # how many ESPN calls at once
ESPN_TIMEOUT_SECONDS = int(os.getenv("ESPN_TIMEOUT_SECONDS", "25"))       # per-call timeout
_ESPN_GATE = asyncio.Semaphore(ESPN_MAX_CONCURRENCY)

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

# ---------- Helpers ----------

async def build_league_from_settings(settings) -> League:
    # espn_api does network IO in League(...), so offload it too
    return await espn_call(
        League,
        league_id=int(settings["league_id"]),
        year=int(settings["season"]),
    )

async def _is_week_complete(league, week: int) -> bool:
    """
    A week is 'complete' if every matchup has real scores for both teams
    (not None), and each team has at least one lineup entry with points.
    This avoids treating future/in-progress weeks as complete.
    """
    try:
        boxes = await espn_call(league.box_scores, week=week)
    except Exception:
        return False

    if not boxes:
        return False

    for g in boxes:
        # If any score is None, week isn't done.
        if (getattr(g, "home_score", None) is None) or (getattr(g, "away_score", None) is None):
            return False

        # Require at least one player with points on each side to avoid 0–0 placeholders.
        def _has_points(lineup):
            for bp in lineup or []:
                pts = getattr(bp, "points", None)
                if pts is not None and float(pts) > 0.0:
                    return True
            return False

        if not _has_points(getattr(g, "home_lineup", [])):  # if lineups are empty/non-scored, it's likely not final
            return False
        if not _has_points(getattr(g, "away_lineup", [])):
            return False

    return True


async def _last_completed_week(league) -> int:
    """
    Walk from week 1 up to 'current' and return the highest week that
    satisfies _is_week_complete. Fallback to 1 if nothing else qualifies.
    """
    current_week = (
        int(getattr(league, "current_week", 0) or 0)
        or int(getattr(league, "nfl_week", 0) or 0)
        or 1
    )
    last_done = 0
    for wk in range(1, max(1, current_week) + 1):
        if await _is_week_complete(league, wk):
            last_done = wk
    return last_done or 1

async def build_league_from_settings(settings) -> League:
    # espn_api does network IO in League(...), so offload it too
    return await espn_call(
        League,
        league_id=int(settings["league_id"]),
        year=int(settings["season"]),
    )

# --- Scoring precision detection (0, 1, or 2 decimal places) ---
_PRECISION_CACHE: dict[int, int] = {}

def _fmt_points(val: float | int | None, precision: int) -> str:
    if val is None:
        return "0"
    return f"{float(val):.{precision}f}"

async def detect_scoring_precision(league) -> int:
    """
    Infer precision by sampling box score values and checking if they
    align to 0, 1, or 2 decimal places. Caches per-league.
    """
    league_id = int(getattr(league, "league_id", 0) or 0)
    if league_id in _PRECISION_CACHE:
        return _PRECISION_CACHE[league_id]

    # Choose up to two weeks to sample: current and week 1 (defensive)
    current_week = (
        int(getattr(league, "current_week", 0) or 0)
        or int(getattr(league, "nfl_week", 0) or 0)
        or 1
    )
    weeks_to_try = [max(1, current_week)]
    if current_week != 1:
        weeks_to_try.append(1)

    samples: list[float] = []
    for wk in weeks_to_try:
        try:
            boxes = await espn_call(league.box_scores, week=wk)
            for g in boxes:
                # team scores
                if g.home_score is not None: samples.append(float(g.home_score))
                if g.away_score is not None: samples.append(float(g.away_score))
                # player points
                for lineup in (g.home_lineup, g.away_lineup):
                    for bp in lineup:
                        pts = getattr(bp, "points", None)
                        if pts is not None:
                            samples.append(float(pts))
        except Exception:
            continue

    # Fallback if we couldn't sample anything
    if not samples:
        _PRECISION_CACHE[league_id] = 2
        return 2

    # Check which precision cleanly represents all samples
    for p in (0, 1, 2):
        mult = 10 ** p
        if all(abs(round(v * mult) - v * mult) < 1e-6 for v in samples):
            _PRECISION_CACHE[league_id] = p
            return p

    _PRECISION_CACHE[league_id] = 2
    return 2

async def build_position_top_embeds(league: League, end_week: int, position: str, starters_only: bool = False) -> discord.Embed:
    """Single embed with Top-5 for each position through end_week."""
    embeds: list[discord.Embed] = []
    precision = await detect_scoring_precision(league)
    positions = [position] if position else DESIRED_POSITIONS

    season_points: dict[str, object] = { }
    for wk in range(1, end_week + 1):
        week_boxes = await espn_call(league.box_scores, week=wk)
        for game in week_boxes:
            for lineup, fteam in ((game.home_lineup, game.home_team), (game.away_lineup, game.away_team)):
                for bp in lineup:
                    pts = getattr(bp, "points", None)
                    pos = getattr(bp, "position", None)
                    slot = getattr(bp, "slot_position", None)

                    if pts is None or pos is None or pos not in positions:
                        continue
                    if starters_only and slot == "BE":
                        continue
                    pos = "D/ST" if pos in ("DST", "DEF", "Def") else pos

                    if bp.name in season_points:
                        season_points[bp.name]['points'] += float(pts)
                    else:
                        season_points[bp.name] = {
                        "name": bp.name,
                        "pos": pos,
                        "points": float(pts),
                        "id": getattr(bp, "playerId", None),
                        "team": getattr(fteam, "team_name", "Unknown"),
                        "proTeam": getattr(bp, "proTeam", None),
                    }

    for pos in positions:
        top5 = sorted(season_points.items(), key=lambda item: item[1]['points'], reverse=True)[:5]     
        for player in top5:
            top = player[1]
            if top['pos'] == "D/ST":
                team_key = top["name"].replace(" D/ST", "").strip()
                code = TEAM_LOGO.get(team_key)
                image_url = TEAM_IMG.format(code=code) if code else None
            else:
                image_url = PLAYER_IMG.format(player_id=top["id"]) if top["id"] else None

            e = Embed(
                description=(
                    f"**{top['name']}** ({top['proTeam']} {top['pos']})\n"
                    f"Fantasy Points: **{_fmt_points(top['points'], precision)}**\n"
                    f"Fantasy Team: *{top['team']}*"
                ),
                color=0x9b59b6
            )
            if image_url:
                e.set_thumbnail(url=image_url)
            embeds.append(e)

    normalize_weekly_embed_heights(embeds)
    title = f"Top 5 {position}s" if position else "Top 5 Scorers"
    embeds.insert(0, Embed(
        title=title + f" through Week {end_week}",
        color=0x9b59b6
    )) 
    embeds.extend(embeds)
    return embeds[:6]

async def build_team_top_embeds(league: League, end_week: int, team: object, starters_only: bool = False) -> discord.Embed:
    """Single embed with Top-5 for each position through end_week."""
    embeds: list[discord.Embed] = []
    precision = await detect_scoring_precision(league)

    season_points: dict[str, object] = { }
    for wk in range(1, end_week + 1):
        week_boxes = await espn_call(league.box_scores, week=wk)
        for game in week_boxes:
            for lineup, fteam in ((game.home_lineup, game.home_team), (game.away_lineup, game.away_team)):
                for bp in lineup:
                    pts = getattr(bp, "points", None)
                    pos = getattr(bp, "position", None)
                    slot = getattr(bp, "slot_position", None)
                    pteam = getattr(fteam, "team_abbrev")

                    if pts is None or pos is None or pteam != team.team_abbrev:
                        continue
                    if starters_only and slot == "BE":
                        continue
                    pos = "D/ST" if pos in ("DST", "DEF", "Def") else pos

                    if bp.name in season_points:
                        season_points[bp.name]['points'] += float(pts)
                    else:
                        season_points[bp.name] = {
                        "name": bp.name,
                        "points": float(pts),
                        "pos": pos,
                        "id": getattr(bp, "playerId", None),
                        "proTeam": getattr(bp, "proTeam", None),
                    }

    top5 = sorted(season_points.items(), key=lambda item: item[1]['points'], reverse=True)[:5]     
    for player in top5:
        top = player[1]
        if top['pos'] == "D/ST":
            team_key = top["name"].replace(" D/ST", "").strip()
            code = TEAM_LOGO.get(team_key)
            image_url = TEAM_IMG.format(code=code) if code else None
        else:
            image_url = PLAYER_IMG.format(player_id=top["id"]) if top["id"] else None

        e = Embed(
            description=(
                f"**{top['name']}** ({top['proTeam']} {top['pos']})\n"
                f"Fantasy Points: **{_fmt_points(top['points'], precision)}**\n"
            ),
            color=0x9b59b6
        )
        if image_url:
            e.set_thumbnail(url=image_url)
        embeds.append(e)

    normalize_weekly_embed_heights(embeds)
    embeds.insert(0, Embed(
        title=f"Season Top 5 on {team.team_name}",
        description=f"(through Week {end_week})",
        color=0x9b59b6
    )) 
    embeds.extend(embeds)
    return embeds[:6]

async def build_weekly_top_embeds(league: League, week: int, position: str, starters_only: bool = False) -> list[discord.Embed]:
    """Top player per position for a given week using box scores."""
    embeds: list[discord.Embed] = []
    precision = await detect_scoring_precision(league)
    positions = [position] if position else DESIRED_POSITIONS

    best = { } if position else {p: None for p in positions} 
    week_boxes = await espn_call(league.box_scores, week=week)

    for game in week_boxes:
        for lineup, fteam in ((game.home_lineup, game.home_team), (game.away_lineup, game.away_team)):
            for bp in lineup:
                pts = getattr(bp, "points", None)
                base_pos = getattr(bp, "position", None)
                slot_pos = getattr(bp, "slot_position", None)
                if pts is None or base_pos is None or base_pos not in positions:
                    continue
                if starters_only and slot_pos == "BE":
                    continue

                pos = "D/ST" if base_pos in ("DST", "DEF", "Def") else base_pos
                if pos not in DESIRED_POSITIONS:
                    if base_pos in DESIRED_POSITIONS:
                        pos = base_pos
                    else:
                        continue
                
                if position:
                    best[bp.name] =  {
                        "name": bp.name,
                        "points": float(pts),
                        "pos": pos,
                        "id": getattr(bp, "playerId", None),
                        "team": getattr(fteam, "team_name", "Unknown"),
                        "proTeam": getattr(bp, "proTeam", None),
                    }

                else:
                    current = best.get(pos)
                    if current is None or float(pts) > current["points"]:
                        best[pos] = {
                            "name": bp.name,
                            "points": float(pts),
                            "pos": pos,
                            "id": getattr(bp, "playerId", None),
                            "team": getattr(fteam, "team_name", "Unknown"),
                            "proTeam": getattr(bp, "proTeam", None),
                        }

    embeds: list[discord.Embed] = []

    if position:
        top5 = sorted(best.items(), key=lambda item: item[1]['points'], reverse=True)[:5]     
        for player in top5:
            top = player[1]
            pos = top['pos']
            if pos == "D/ST":
                team_key = top["name"].replace(" D/ST", "").strip()
                code = TEAM_LOGO.get(team_key)
                image_url = TEAM_IMG.format(code=code) if code else None
            else:
                image_url = PLAYER_IMG.format(player_id=top["id"]) if top.get("id") else None

            e = Embed(
                description=(
                    f"**{top['name']}** ({top['proTeam']} {pos})\n"
                    f"Fantasy Points: **{_fmt_points(top['points'], precision)}**\n"
                    f"Fantasy Team: *{top['team']}*"
                ),
                color=0x1abc9c
            )
            if image_url:
                e.set_thumbnail(url=image_url)
            embeds.append(e)

        normalize_weekly_embed_heights(embeds)
        embeds.insert(0, Embed(
        title=f"Top {position}s for Week {week}",
        color=0x1abc9c
        )) 

    else:
        for pos in DESIRED_POSITIONS:
            top = best.get(pos)
            if not top:
                continue

            if pos == "D/ST":
                team_key = top["name"].replace(" D/ST", "").strip()
                code = TEAM_LOGO.get(team_key)
                image_url = TEAM_IMG.format(code=code) if code else None
            else:
                image_url = PLAYER_IMG.format(player_id=top["id"]) if top.get("id") else None

            e = Embed(
                title=f"Week {week} Top {pos}",
                description=(
                    f"**{top['name']}** ({top['proTeam']} {pos})\n"
                    f"Fantasy Points: **{_fmt_points(top['points'], precision)}**\n"
                    f"Fantasy Team: *{top['team']}*"
                ),
                color=0x1abc9c
            )
            if image_url:
                e.set_thumbnail(url=image_url)
            embeds.append(e)
        normalize_weekly_embed_heights(embeds)
    
    embeds.extend(embeds)
    count = 6 if position else len(DESIRED_POSITIONS)
    return embeds[:count]

def normalize_weekly_embed_heights(embeds: list[discord.Embed]) -> None:
    """Pad weekly-top embeds so they share the same visual height."""
    if not embeds:
        return
    def line_count(e: discord.Embed) -> int:
        desc = e.description or ""
        return desc.count("\n") + (1 if desc else 0)
    max_lines = max(line_count(e) for e in embeds)
    for e in embeds:
        missing = max_lines - line_count(e)
        if missing > 0:
            # zero-width space keeps a visible blank line in Discord
            e.description = (e.description or "") + ("\n\u200b" * missing)
