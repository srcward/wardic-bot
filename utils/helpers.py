import discord, re, aiohttp, time, logging
from discord.ext import commands
from io import BytesIO
from PIL import Image
from datetime import timedelta
from typing import Optional, Union, Dict, Any, List
from collections import Counter
from utils import exceptions

log = logging.getLogger("Helpers")


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


async def promise_role(
    bot: commands.Bot, guild: discord.Guild, role_id: int
) -> Optional[discord.Role]:
    role = guild.get_role(role_id)
    if not role:
        try:
            role = await guild.fetch_role(role_id)
        except (discord.Forbidden, discord.HTTPException):
            role = None
    return role


async def promise_ban_entry(
    guild: discord.Guild, user: discord.User
) -> Optional[discord.BanEntry]:
    try:
        ban_entry = await guild.fetch_ban(user)
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        ban_entry = None
    return ban_entry


async def promise_channel(
    guild: discord.Guild, channel_id: int
) -> Optional[discord.Guild]:
    channel = guild.get_channel(channel_id)
    if not channel:
        try:
            channel = await guild.fetch_channel(channel_id)
        except (discord.Forbidden, discord.HTTPException):
            channel = None
    return channel


async def promise_category(guild: discord.Guild, category_id: int):
    category = None
    for cat in guild.categories:
        if cat.id == category_id:
            category = cat
            break
    return category


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


def parse_flags(
    args: str, flags: Dict[str, Dict[str, Any]]
) -> Dict[str, Union[str, int, bool, List[str]]]:
    if not args:
        args = ""

    alias_map = {}
    for flag_name, flag_config in flags.items():
        alias_map[f"--{flag_name}"] = flag_name
        if "aliases" in flag_config:
            for alias in flag_config["aliases"]:
                if len(alias) == 1:
                    alias_map[f"-{alias}"] = flag_name
                else:
                    alias_map[f"--{alias}"] = flag_name

    result = {}
    for flag_name, flag_config in flags.items():
        if "default" in flag_config:
            result[flag_name] = flag_config["default"]
        elif flag_config.get("multiple", False):
            result[flag_name] = []
        else:
            result[flag_name] = None

    parts = args.split()
    i = 0

    while i < len(parts):
        part = parts[i]

        if part.startswith("-"):
            if part not in alias_map:
                i += 1
                continue

            flag_name = alias_map[part]
            flag_config = flags[flag_name]
            flag_type = flag_config["type"]

            if flag_type == bool:
                result[flag_name] = True
                i += 1
                continue

            if i + 1 < len(parts) and not parts[i + 1].startswith("-"):
                value_str = parts[i + 1]

                try:
                    if flag_type == int:
                        value = int(value_str)
                    elif flag_type == str:
                        value = value_str
                    else:
                        value = value_str

                    if flag_config.get("multiple", False):
                        result[flag_name].append(value)
                    else:
                        result[flag_name] = value

                    i += 2
                except (ValueError, TypeError):
                    i += 1
            else:
                i += 1
        else:
            i += 1

    missing = []
    for flag_name, flag_config in flags.items():
        if flag_config.get("required", False) and result.get(flag_name) is None:
            missing.append(flag_name)

    if missing:
        raise ValueError(f"Missing required flags: {', '.join(missing)}")

    return result


async def image_primary_colour(url: str) -> discord.Colour:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise ValueError("Failed to fetch image from URL")
            data = BytesIO(await resp.read())

    img = Image.open(data).convert("RGB")
    img = img.resize((150, 150))

    pixels = list(img.getdata())

    pixel_counts = Counter(pixels)
    top_colors = pixel_counts.most_common(10)

    def calculate_vibrancy(rgb):
        r, g, b = rgb
        max_val = max(r, g, b)
        min_val = min(r, g, b)

        brightness = sum(rgb) / 3
        if brightness < 30 or brightness > 230:
            return 0

        if max_val == 0:
            return 0
        return (max_val - min_val) / max_val

    most_vibrant = max(top_colors, key=lambda x: calculate_vibrancy(x[0]))

    return discord.Colour.from_rgb(*most_vibrant[0])


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


async def role_cache_entry(self, guild: discord.Guild, member: discord.Member):
    try:
        role_ids = [role.id for role in member.roles if role != guild.default_role]

        if role_ids:
            cache_key = f"{guild.id}:{member.id}"
            await self.bot.cache.roles.set(
                cache_key,
                role_ids,
                ttl=int(timedelta(hours=2).total_seconds()),
            )
    except Exception as e:
        log.error(f"Error caching roles: {e}")


async def role_delete_entry(self, guild: discord.Guild, member: discord.Member):
    cache_key = f"{guild.id}:{member.id}"

    if await self.bot.cache.roles.get(cache_key):
        await self.bot.cache.roles.delete(cache_key)
