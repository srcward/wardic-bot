import discord, logging
from discord.ext import commands

from utils import exceptions
from utils.messages import Embeds

from main import Bot

log = logging.getLogger("Command Error")


class OnCommandError(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            permissions = ", ".join(error.missing_permissions)
            await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"You're **missing** permissions: `{permissions}`.",
                )
            )
        elif isinstance(error, exceptions.HierarchyCheckError):
            return
        elif isinstance(error, exceptions.MaxDurationExceeded):
            return
        elif isinstance(error, commands.CheckFailure):
            return
        elif isinstance(error, commands.CommandOnCooldown):
            cooldown = error.retry_after
            formatted = f"{cooldown:.1f}s"
            await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description=f"**{ctx.command.name}** is on cooldown. Try again in **{formatted}**.",
                    emoji="<:cooldown:1446603946474078299>",
                    colour=0x53C6EF,
                )
            )
        elif isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, exceptions.NotAntiNukeAdmin):
            await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"You need to be an **AntiNuke Administrator** to **{ctx.command.name}**.",
                )
            )
        elif isinstance(error, commands.BotMissingPermissions):
            permissions = ", ".join(error.missing_permissions)
            await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions: `{permissions}`.",
                )
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )
        elif isinstance(error, commands.UserNotFound):
            await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description=f"I couldn't find the user: `{error.argument}`. Use their **ID instead**.",
                    emoji=":mag:",
                )
            )
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description=f"I couldn't find the member: `{error.argument}`. Use their **ID instead**.",
                    emoji=":mag:",
                )
            )
        elif isinstance(error, commands.RoleNotFound):
            await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description=f"I couldn't find the role: `{error.argument}`. Use its **ID instead**.",
                    emoji=":mag:",
                )
            )
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description=f"I couldn't find the channel: `{error.argument}`. Use its **ID instead**.",
                    emoji=":mag:",
                )
            )
        elif isinstance(error, commands.GuildNotFound):
            await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description=f"I couldn't find the guild: `{error.argument}`. Use its **ID instead**.",
                    emoji=":mag:",
                )
            )
        else:
            log.error(error)


async def setup(bot):
    await bot.add_cog(OnCommandError(bot))
