import discord, os
from discord.ext import commands
from typing import Optional

_fallback_prefix = os.getenv("FALLBACK_PREFIX")


class Colours:
    @staticmethod
    def main():
        return discord.Colour(0x71709D)

    @staticmethod
    def green():
        return discord.Colour(0x9AD170)

    @staticmethod
    def orange():
        return discord.Colour(0xFDA926)

    @staticmethod
    def red():
        return discord.Colour(0xFF6464)


class Emojis:
    @staticmethod
    def checkmark():
        return "<:new_approve:1448062471012094063>"

    @staticmethod
    def warning():
        return "<:warning:1444853246442078353>"

    @staticmethod
    def issue():
        return "<:new_issue:1447843542419636337>"

    @staticmethod
    def loading():
        return "<a:new_loading:1449189345813729350>"


class Embeds:
    @staticmethod
    def checkmark(
        author: Optional[discord.User] = None,
        description: str = "Enter a description...",
    ):
        return discord.Embed(
            description=f"{Emojis.checkmark()} {f"{author.mention}: " if author else ""}{description}",
            colour=Colours.main(),
        )

    @staticmethod
    def warning(
        author: Optional[discord.User] = None,
        description: str = "Enter a description...",
    ):
        return discord.Embed(
            description=f"{Emojis.warning()} {f"{author.mention}: " if author else ""}{description}",
            colour=Colours.orange(),
        )

    @staticmethod
    def issue(
        author: Optional[discord.User] = None,
        description: str = "Enter a description...",
    ):
        return discord.Embed(
            description=f"{Emojis.issue()} {f"{author.mention}: " if author else ""}{description}",
            colour=Colours.red(),
        )

    @staticmethod
    def loading(
        author: Optional[discord.User] = None,
        description: str = "Enter a description...",
    ):
        return discord.Embed(
            description=f"{Emojis.loading()} {f"{author.mention}: " if author else ""}{description}",
            colour=Colours.main(),
        )

    @staticmethod
    def embed(
        author: Optional[discord.User] = None,
        description: str = "Enter a description...",
        emoji: Optional[str] = "",
        colour: Optional[discord.Colour] = None,
    ):
        return discord.Embed(
            description=f"{emoji} {f"{author.mention}: " if author else ""}{description}",
            colour=colour,
        )

    @staticmethod
    def command(
        command: commands.Command,
        author: Optional[discord.User] = None,
        prefix: str = _fallback_prefix,
    ):
        name = command.qualified_name
        embed = discord.Embed(title=f"Command: {name}", colour=Colours.main())
        raw_usage = None
        if command.usage:
            raw_usage = (
                command.usage.split(" | ") if "|" in command.usage else ["(none)", ""]
            )

        if raw_usage:
            syntax = raw_usage[0] or "(none)"
            example = raw_usage[1] or ""
        else:
            syntax = "(none)"
            example = ""

        embed.description = f"""{command.help}\n```Syntax: {prefix}{name} {syntax}\nExample: {prefix}{name} {example}```"""

        if author:
            embed.set_author(name=author.name, icon_url=author.display_avatar.url)

        return embed
