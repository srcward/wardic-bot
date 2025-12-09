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


def is_owner():
    async def predicate(ctx: commands.Context):
        config = await ctx.bot.dbf.get_configuration()
        developers = config.setdefault("Developers", [])

        isowner = ctx.author.id in ctx.bot.owner_ids
        isdev = ctx.author.id in developers

        if not isowner and not isdev:
            raise commands.MissingPermissions("bot_owner")
        return True

    return commands.check(predicate)
