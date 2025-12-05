from discord.ext import commands
from utils import permissions, exceptions


def is_antinuke_admin():
    async def predicate(ctx: commands.Context):
        is_admin = await permissions.is_antinuke_administrator(
            bot=ctx.bot, guild=ctx.guild, user=ctx.author
        )

        if not is_admin:
            raise exceptions.NotAntiNukeAdmin(executor=ctx.author)

        return True

    return commands.check(predicate)


def is_antiraid_admin():
    async def predicate(ctx: commands.Context):
        is_admin = await permissions.is_antiraid_administrator(
            bot=ctx.bot, guild=ctx.guild, user=ctx.author
        )

        if not is_admin:
            raise exceptions.NotAntiNukeAdmin(executor=ctx.author)

        return True

    return commands.check(predicate)
