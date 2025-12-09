import re
from typing import List
from discord.ext import commands
import discord
from rapidfuzz import fuzz, process


ROLE_MENTION_RE = re.compile(r"^<@&(?P<id>\d+)>$")
ID_RE = re.compile(r"^\d{17,20}$")


class PartialRole(commands.Converter):
    def __init__(self, threshold: int = 70):
        self.threshold = threshold

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        guild = ctx.guild
        if guild is None:
            raise commands.BadArgument("No guild context.")

        m = ROLE_MENTION_RE.match(argument)
        if m:
            role_id = int(m.group("id"))
            role = guild.get_role(role_id)
            if role:
                return role
            raise commands.BadArgument(f"No role found with ID {role_id}.")

        if ID_RE.match(argument):
            try:
                role_id = int(argument)
                role = guild.get_role(role_id)
                if role:
                    return role
            except Exception:
                pass

        roles: List[discord.Role] = [r for r in guild.roles if r.name != "@everyone"]
        role_names = [r.name for r in roles]

        arg_lower = argument.lower()
        for role in roles:
            if role.name.lower() == arg_lower:
                return role

        substring_matches = []
        for role in roles:
            if arg_lower in role.name.lower():
                substring_matches.append(role)
        if substring_matches:
            substring_matches.sort(key=lambda r: len(r.name))
            return substring_matches[0]

        match = process.extractOne(argument, role_names, scorer=fuzz.WRatio)
        if match and match[1] >= self.threshold:
            matched_name = match[0]
            for role in roles:
                if role.name == matched_name:
                    return role

        raise commands.BadArgument(f"No role found matching '{argument}'.")
