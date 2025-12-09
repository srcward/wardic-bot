import discord, re, aiohttp, time
from discord.ext import commands
from io import BytesIO
from PIL import Image
from typing import Optional, Union
from utils import exceptions


async def promise_member(
    guild: discord.Guild, user_id: int
) -> Optional[discord.Member]:
    member = guild.get_member(user_id)
    if not member:
        try:
            member = await guild.fetch_member(user_id)
        except (discord.Forbidden, discord.HTTPException):
            member = None
    return member


async def promise_user(bot: commands.Bot, user_id: int) -> Optional[discord.User]:
    user = bot.get_user(user_id)
    if not user:
        try:
            user = await bot.fetch_user(user_id)
        except (discord.Forbidden, discord.HTTPException):
            user = None
    return user


async def promise_guild(bot: commands.Bot, guild_id: int) -> Optional[discord.Guild]:
    guild = bot.get_guild(guild_id)
    if not guild:
        try:
            guild = await bot.fetch_guild(guild_id)
        except (discord.Forbidden, discord.HTTPException):
            guild = None
    return guild


async def promise_ban_entry(
    guild: discord.Guild, user: discord.User
) -> Optional[discord.BanEntry]:
    try:
        ban_entry = await guild.fetch_ban(user)
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        ban_entry = None
    return ban_entry


def parse_duration(value, *, default_unit="s", max_time=None) -> int:
    UNITS = {
        "s": 1,
        "sec": 1,
        "secs": 1,
        "second": 1,
        "seconds": 1,
        "m": 60,
        "min": 60,
        "mins": 60,
        "minute": 60,
        "minutes": 60,
        "h": 3600,
        "hr": 3600,
        "hrs": 3600,
        "hour": 3600,
        "hours": 3600,
        "d": 86400,
        "day": 86400,
        "days": 86400,
        "w": 604800,
        "week": 604800,
        "weeks": 604800,
        "mo": 2629800,
        "y": 31557600,
    }

    if isinstance(value, int):
        total = value * UNITS[default_unit]
    else:
        value = str(value).strip().lower()

        if value.isdigit():
            total = int(value) * UNITS[default_unit]
        else:
            pattern = r"(\d+)([a-zA-Z]+)"
            matches = re.findall(pattern, value)

            if not matches:
                raise ValueError(f"Invalid duration format: '{value}'")

            total = 0
            for amount, unit in matches:
                if unit not in UNITS:
                    raise ValueError(f"Invalid unit '{unit}' in '{value}'")
                total += int(amount) * UNITS[unit]

    if max_time is not None:
        if isinstance(max_time, int):
            max_seconds = max_time
        else:
            max_seconds = parse_duration(max_time, default_unit=default_unit)

        if total > max_seconds:
            raise exceptions.MaxDurationExceeded(value, max_time)

    return total


async def image_primary_colour(url: str) -> discord.Colour:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise ValueError("Failed to fetch image from URL")
            data = BytesIO(await resp.read())

        img = Image.open(data).convert("RGB")
        img = img.resize((50, 50))

        pixels = list(img.getdata())
        r = sum(p[0] for p in pixels) // len(pixels)
        g = sum(p[1] for p in pixels) // len(pixels)
        b = sum(p[2] for p in pixels) // len(pixels)

        return discord.Colour.from_rgb(r, g, b)


def build_duration(timestamp: int | float, max_length: int = None) -> str:
    now = time.time()
    diff = max(0, int(now - timestamp))

    units = [
        ("y", 60 * 60 * 24 * 365),
        ("mo", 60 * 60 * 24 * 30),
        ("w", 60 * 60 * 24 * 7),
        ("d", 60 * 60 * 24),
        ("h", 60 * 60),
        ("m", 60),
        ("s", 1),
    ]

    parts = []
    for suffix, seconds in units:
        if diff >= seconds:
            value = diff // seconds
            diff -= value * seconds
            parts.append(f"{value}{suffix}")

    if not parts:
        return "just now"

    if max_length is not None:
        parts = parts[:max_length]

    return " ".join(parts)
