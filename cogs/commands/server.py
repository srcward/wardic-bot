import discord
from discord.ext import commands

from typing import Optional, Union

from utils import views
from utils.messages import Embeds

from main import Bot


class Server(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.dbf = bot.dbf

    @commands.group(
        name="prefix",
        help="A group of prefix related commands",
        usage="[subcommand] [arguments] | w?",
        invoke_without_command=True,
    )
    @commands.guild_only()
    async def prefix_group(
        self, ctx: commands.Context, *, prefix: Optional[str] = None
    ):
        if ctx.invoked_subcommand:
            return

        guild_data = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config = guild_data.setdefault("Configuration", {})
        prefix_data = guild_config.setdefault("Prefix", self.bot._fallback_prefix)

        if not prefix:
            return await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description=f"The current server prefix is: `{prefix_data}`.",
                    emoji="<:information:1446210296913068164>",
                )
            )

        if prefix:
            if not ctx.author.guild_permissions.administrator:
                raise commands.MissingPermissions(["administrator"])

            if await self.bot.get_prefix(ctx.message) == prefix:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description=f"The server prefix is already `{prefix}`.",
                    )
                )

            if len(prefix) > 6:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description=f"The server prefix can only be **1-6 characters long**.",
                    )
                )

            guild_config["Prefix"] = prefix
            await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)
            return await ctx.send(
                embed=Embeds.checkmark(
                    author=ctx.author,
                    description=f"Set the server prefix to: `{guild_config["Prefix"]}`.",
                )
            )

    @prefix_group.command(
        name="set", help="Set the server prefix", usage="(prefix) | w?"
    )
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def set_prefix_command(self, ctx: commands.Context, prefix: str):
        if await self.bot.get_prefix(ctx.message) == prefix:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"The server prefix is already `{prefix}`.",
                )
            )

        guild_data = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config = guild_data.setdefault("Configuration", {})
        prefix_data = guild_config.setdefault("Prefix", self.bot._fallback_prefix)

        if prefix == prefix_data:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"The server prefix is **already** `{prefix_data}`.",
                )
            )

        if len(prefix) > 6:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"The server prefix can only be **1-6 characters long**.",
                )
            )

        guild_config["Prefix"] = prefix
        await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)
        return await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Set the **server prefix** to `{guild_config["Prefix"]}`.",
            )
        )

    @prefix_group.command(name="reset", help="reset the server prefix")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def reset_prefix_command(self, ctx: commands.Context):
        guild_data = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config = guild_data.setdefault("Configuration", {})
        prefix_data = guild_config.setdefault("Prefix", self.bot._fallback_prefix)

        if guild_config["Prefix"] == self.bot._fallback_prefix:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"The server prefix is **already the default one**.",
                )
            )

        guild_config["Prefix"] = self.bot._fallback_prefix
        await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)
        return await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Reset the **server prefix** to `{guild_config["Prefix"]}`.",
            )
        )

    @commands.group(
        name="alias",
        help="A group of prefix related commands",
        usage="(subcommand) (arguments) | add ban deport",
        invoke_without_command=True,
    )
    @commands.has_permissions(administrator=True)
    async def alias_group(self, ctx: commands.Context, command: Optional[str] = None):
        if ctx.invoked_subcommand:
            return

        if not command:
            await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

    @alias_group.command(
        name="add",
        help="Add an alias to a command",
        usage="(command) (alias) | ban deport",
    )
    @commands.has_permissions(administrator=True)
    async def add_alias_command(self, ctx: commands.Context, command: str, alias: str):
        command = command.lower()
        alias = alias.lower()

        if not self.bot.get_command(command):
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"The command `{command}` **doesn't exist**.",
                )
            )

        guild_data: dict = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config: dict = guild_data.setdefault("Configuration", {})
        guild_aliases: dict = guild_config.setdefault("Command_Aliases", {})

        if guild_aliases.get(alias):
            real_command = guild_aliases[alias]
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"The alias `{alias}` **already exists** for `{real_command}`.",
                )
            )

        guild_aliases[alias] = command

        await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)
        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author, description=f"Added alias `{alias}` to `{command}`."
            )
        )

    @alias_group.command(
        name="remove",
        help="Remove an alias from a command",
        usage="(command) (alias) | ban deport",
    )
    @commands.has_permissions(administrator=True)
    async def remove_alias_command(self, ctx: commands.Context, alias: str):
        alias = alias.lower()

        guild_data = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config = guild_data.setdefault("Configuration", {})
        guild_aliases = guild_config.setdefault("Command_Aliases", {})

        if alias not in guild_aliases:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"The alias `{alias}` **doesn't exist**.",
                )
            )

        guild_aliases.pop(alias)

        await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)
        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Removed the alias `{alias}`.",
            )
        )

    @commands.command(name="roles", help="View all of the server roles")
    @commands.guild_only()
    async def roles_command(self, ctx: commands.Context):
        items = [
            f"`{index+1}` {r.mention}"
            for index, r in enumerate(reversed(list(ctx.guild.roles)))
            if r != ctx.guild.default_role
        ]

        paginator = views.Paginator(
            bot=self.bot,
            ctx=ctx,
            items=items,
            items_per_page=10,
            embed_title=f"Roles in {ctx.guild.name}",
            owner=ctx.author,
            owner_can_delete=True,
        )
        await paginator.start()

    @commands.command(name="inrole", help="View what members are in a role")
    @commands.guild_only()
    async def inrole_command(
        self,
        ctx: commands.Context,
        argument: Optional[Union[discord.Member, discord.Role]] = None,
    ):
        if not argument:
            argument = (
                ctx.author.top_role
                if ctx.author.top_role != ctx.guild.default_role
                else reversed(list(ctx.guild.roles))[0]
            )

        if isinstance(argument, discord.Role):
            title = f"Members in {argument.name[:12]}{"..." if len(argument.name) > 12 else ""}"
            items = [
                f"`{index+1}` **{m.name}**"
                for index, m in enumerate(reversed(list(argument.members)))
            ]
        elif isinstance(argument, discord.Member):
            title = f"{argument.name[:12]}'s Roles"
            items = [
                f"`{index+1}` {r.mention}"
                for index, r in enumerate(reversed(list(argument.roles)))
                if r != r.guild.default_role
            ]

        paginator = views.Paginator(
            bot=self.bot,
            ctx=ctx,
            items=items,
            items_per_page=10,
            embed_title=title,
            owner=ctx.author,
            owner_can_delete=True,
        )
        await paginator.start()


async def setup(bot):
    await bot.add_cog(Server(bot))
