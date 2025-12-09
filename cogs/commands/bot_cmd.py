import discord
from discord.ext import commands

from typing import Optional, Union

from utils import views, checks
from utils.messages import Embeds

from main import Bot


class BotCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = bot.db
        self.dbf = bot.dbf

    @commands.group(
        name="ownercmds",
        help="A group of owner related commands",
        usage="(subcommand) (arguments) | status add i listen to esdeekid and fakemink",
        aliases=["ownc"],
        invoke_without_command=True
    )
    @checks.is_owner()
    async def ownercmds(self, ctx: commands.Context):
        if ctx.invoked_subcommand:
            return
        
        await ctx.send(embed=Embeds.command(command=ctx.command, author=ctx.author, prefix=ctx.prefix))

    @ownercmds.command(
        name="whitelist",
        help="Add or remove a whitelist from a guild",
        usage="(guild) [type] | add 1444846443104964660"
    )
    @checks.is_owner()
    async def whitelist(self, ctx: commands.Context, type: str, guild_id: int):
        config = await self.dbf.get_configuration()
        whitelisted_guilds = config.setdefault("Whitelisted_Guilds", [])
        action = True
        lower_type = type.lower()

        if lower_type in ("add", "a", "1", "yes"):
            if guild_id in whitelisted_guilds:
                return await ctx.send(embed=Embeds.warning(
                    author=ctx.author,
                    description=f"That guild is **already whitelisted**."
                ))
            whitelisted_guilds.append(guild_id)
            action = True
        else:
            if guild_id not in whitelisted_guilds:
                return await ctx.send(embed=Embeds.warning(
                    author=ctx.author,
                    description=f"That guild **isn't whitelisted**."
                ))
            whitelisted_guilds.remove(guild_id)
            action = False

        await self.dbf.set_configuration(data=config)

        await ctx.send(embed=Embeds.checkmark(
            author=ctx.author,
            description=f"`{guild_id}` has been **{'added to the whitelist' if action == True else 'removed from the whitelist'}.**"
        ))

    @ownercmds.group(
        name="status",
        help="A group of status related commands",
        usage="[subcommand] [arguments] | add i listen to esdeekid and fakemink",
        invoke_without_command=True,
    )
    @checks.is_owner()
    async def status_command(self, ctx: commands.Context):
        config = await self.dbf.get_configuration()
        status_data = config.setdefault("Statuses", {})
        statuses = status_data.setdefault("List", ["i listen to esdeekid and fakemink"])

        items = [f"`{index+1}` {s}" for index, s in enumerate(statuses)]

        paginator = views.Paginator(
            bot=self.bot,
            ctx=ctx,
            items=items,
            items_per_page=10,
            embed_title=f"Auto-rotating statuses for wardic",
            owner=ctx.author,
            owner_can_delete=True,
        )
        await paginator.start()

    @status_command.command(
        name="add",
        help="Add a status to the auto-rotating status list",
        usage="(status) | i listen to esdeekid and fakemink",
    )
    @checks.is_owner()
    async def add_status_command(self, ctx: commands.Context, *, status: str):
        config = await self.dbf.get_configuration()
        status_data = config.setdefault("Statuses", {})
        statuses = status_data.setdefault("List", ["i listen to esdeekid and fakemink"])

        if status in statuses:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author, description="That status **already exists**."
                )
            )

        statuses.append(status)
        await self.dbf.set_configuration(data=config)

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Added `{status}` to the rotating statuses.",
            )
        )

    @status_command.command(
        name="set",
        help="Set the bots status",
        usage="(status) | i listen to esdeekid and fakemink",
    )
    @checks.is_owner()
    async def set_status_command(self, ctx: commands.Context, *, status: str):
        config = await self.dbf.get_configuration()
        status_data = config.setdefault("Statuses", {})
        main_status_data = status_data.setdefault("Status", None)

        await self.bot.change_presence(activity=discord.CustomActivity(name=status))
        status_data["Status"] = status

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Set the bot's status to `{status}`.",
            )
        )

    @status_command.command(
        name="remove",
        help="Remove a status from the auto-rotating status list",
        usage="(status) | i listen to esdeekid and fakemink",
    )
    @checks.is_owner()
    async def remove_status_command(self, ctx: commands.Context, *, status: str):
        config = await self.dbf.get_configuration()
        status_data = config.setdefault("Statuses", {})
        statuses = status_data.setdefault("List", ["i listen to esdeekid and fakemink"])

        if status not in statuses:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"That status **doesn't exist**. Use `{ctx.prefix}status` to view all statuses.",
                )
            )

        statuses.remove(status)
        await self.dbf.set_configuration(data=config)

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Removed `{status}` from the rotating statuses.",
            )
        )

    @status_command.command(
        name="randomize",
        help="Toggle the looping status list to randomly pick a status",
        usage="(toggle) | true",
        aliases=["random", "randomise"],
    )
    @checks.is_owner()
    async def randomize_status_command(self, ctx: commands.Context, toggle: str):
        config = await self.dbf.get_configuration()
        status_data = config.setdefault("Statuses", {})
        settings = status_data.setdefault("Configuration", {})

        enable = toggle.lower() in ("true", "on", "yes", "y", "t")
        settings["Randomized"] = enable

        await self.dbf.set_configuration(data=config)

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"**{'Enabled' if enable else 'Disabled'}** randomized status looping.",
            )
        )

    @status_command.command(
        name="loop",
        help="Toggle the looping status",
        usage="(toggle) | true",
    )
    @checks.is_owner()
    async def loop_status_command(self, ctx: commands.Context, toggle: str):
        config = await self.dbf.get_configuration()
        status_data = config.setdefault("Statuses", {})
        settings = status_data.setdefault("Configuration", {})

        enable = toggle.lower() in ("true", "on", "yes", "y", "t")
        settings["LoopingEnabled"] = enable

        await self.dbf.set_configuration(data=config)

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"**{'Enabled' if enable else 'Disabled'}** status looping.",
            )
        )

async def setup(bot):
    await bot.add_cog(BotCog(bot))
