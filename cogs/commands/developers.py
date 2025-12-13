import discord, os, logging, asyncio, random
from discord.ext import commands

from typing import Optional, Union
from rapidfuzz import process, fuzz

from utils import views, checks
from utils.messages import Embeds, Emojis, Colours

from main import Bot

cog_log = logging.getLogger("Cogs")


class Developers(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = bot.db
        self.dbf = bot.dbf
        self.badges = {
            "Owner": {
                "name": "Owner",
                "emoji": "<a:snorlax:1448192709507420201>",
            },
            "Coco's Parent": {
                "name": "Coco's Parent",
                "emoji": "<:coco:1448186422879326391>",
            },
            "Angel": {"name": "Angel", "emoji": "<:wing:1444852907974594671>"},
            "Music Enjoyer": {
                "name": "Music Enjoyer",
                "emoji": "<:true_music_enjoyer:1448193961998024745>",
            },
            "Cute": {"name": "Cute", "emoji": "<:cute:1448409695235870871>"},
        }

    @commands.group(
        name="ownercmds",
        help="A group of owner related commands",
        usage="(subcommand) (arguments) | status add If I were a bird",
        aliases=["ownc", "own"],
        invoke_without_command=True,
    )
    @checks.is_owner()
    async def ownercmds_group(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

    @ownercmds_group.group(
        name="status",
        help="A group of status related commands",
        usage="[subcommand] [arguments] | add If I were a bird",
        invoke_without_command=True,
    )
    @checks.is_owner()
    async def status_command(self, ctx: commands.Context):
        config = await self.dbf.get_configuration()
        status_data = config.setdefault("Statuses", {})
        statuses = status_data.setdefault("List", ["If I were a bird"])

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
        usage="(status) | If I were a bird",
    )
    @checks.is_owner()
    async def add_status_command(self, ctx: commands.Context, *, status: str):
        config = await self.dbf.get_configuration()
        status_data = config.setdefault("Statuses", {})
        statuses = status_data.setdefault("List", ["If I were a bird"])

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
        name="remove",
        help="Remove a status from the auto-rotating status list",
        usage="(status) | If I were a bird",
    )
    @checks.is_owner()
    async def remove_status_command(self, ctx: commands.Context, *, status: str):
        config = await self.dbf.get_configuration()
        status_data = config.setdefault("Statuses", {})
        statuses = status_data.setdefault("List", ["If I were a bird"])

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
        name="set",
        help="Set the bots status",
        usage="(status) | If I were a bird",
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

        await self.dbf.set_configuration(data=config)

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
        settings = status_data.setdefault("Settings", {})

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
        settings = status_data.setdefault("Settings", {})

        enable = toggle.lower() in ("true", "on", "yes", "y", "t")
        settings["LoopingEnabled"] = enable

        await self.dbf.set_configuration(data=config)

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"**{'Enabled' if enable else 'Disabled'}** status looping.",
            )
        )

    @ownercmds_group.command(
        name="whitelist",
        help="Add or remove a guild from the whitelist",
        usage="(mode) (guild) | Add 1444846443104964660",
    )
    @commands.is_owner()
    async def whitelist_command(self, ctx: commands.Context, mode: str, guild_id: int):
        config = await self.dbf.get_configuration()
        whitelisted_guilds = config.setdefault("Whitelisted_Guilds", [])

        if mode.lower() in ("add", "new", "plus", "1"):
            if str(guild_id) in whitelisted_guilds:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description=f"`{guild_id}` is **already whitelisted**.",
                    )
                )
            whitelisted_guilds.append(str(guild_id))
            mode = True
        else:
            if not str(guild_id) in whitelisted_guilds:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description=f"`{guild_id}` **isn't whitelisted**.",
                    )
                )
            mode = False

        await self.dbf.set_configuration(data=config)

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"`{guild_id}` has been **{"added to" if mode else "removed from"}** the whitelist.",
            )
        )

    @ownercmds_group.group(
        name="badge",
        help="A group of badge related commands",
        usage="(subcommand) (arguments) | add Owner",
    )
    @checks.is_owner()
    async def badge_group(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

    @badge_group.command(
        name="add",
        help="Add a badge to a user",
        usage="(user) (badge name) | @ward Owner",
    )
    @checks.is_owner()
    async def badge_add(
        self, ctx: commands.Context, user: discord.User, *, badge_name: str
    ):
        badge_names = list(self.badges.keys())
        result = process.extractOne(
            badge_name,
            badge_names,
            scorer=fuzz.ratio,
            score_cutoff=60,
        )

        if not result:
            available_badges = "\n".join([f"• `{name}`" for name in badge_names])
            return await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description=f"I couldn't find the badge `{badge_name}`.",
                    emoji=":mag:",
                )
            )

        matched_badge_name = result[0]
        matched_score = result[1]
        badge = self.badges[matched_badge_name]

        user_data = await self.dbf.get_user_data(user_id=user.id)
        badges_list = user_data.get("Badges", [])

        if any(b.get("name") == badge["name"] for b in badges_list):
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"**{user.name}** already has that badge.",
                )
            )

        badges_list.append(badge)
        user_data["Badges"] = badges_list
        await self.dbf.set_user_data(user_id=user.id, data=user_data)
        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Added {badge['emoji']} `{badge['name']}` badge to **{user.name}**.",
            )
        )

    @badge_group.command(
        name="remove",
        help="Remove a badge from a user",
        usage="(user) (badge name) | @ward Owner",
        aliases=["delete", "rm"],
    )
    @checks.is_owner()
    async def badge_remove(
        self, ctx: commands.Context, user: discord.User, *, badge_name: str
    ):
        user_data = await self.dbf.get_user_data(user_id=user.id)
        badges_list = user_data.get("Badges", [])

        if not badges_list:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"**{user.name}** doesn't have any badges.",
                )
            )

        user_badge_names = [b.get("name", "") for b in badges_list]

        result = process.extractOne(
            badge_name, user_badge_names, scorer=fuzz.ratio, score_cutoff=60
        )

        if not result:
            current_badges = "\n".join(
                [
                    f"• {b.get('emoji', '')} `{b.get('name', 'Unknown')}`"
                    for b in badges_list
                ]
            )
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"**{user.name}** doesn't have that badge.",
                )
            )

        matched_badge_name = result[0]
        matched_score = result[1]

        removed_badge = None
        badges_list = [b for b in badges_list if b.get("name") != matched_badge_name]

        for b in user_data.get("Badges", []):
            if b.get("name") == matched_badge_name:
                removed_badge = b
                break

        user_data["Badges"] = badges_list
        await self.dbf.set_user_data(user_id=user.id, data=user_data)

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Removed {removed_badge.get('emoji', '')} `{matched_badge_name}` badge from **{user.name}**.",
            )
        )

    @commands.command(name="reload", help="Reload all commands and events")
    @checks.is_owner()
    async def reload(self, ctx: commands.Context):
        msg = await ctx.send(
            embed=Embeds.loading(
                author=ctx.author,
                description="Reloading **all commands and events**...",
            )
        )

        loaded = []
        reloaded = []
        failed = []
        final_msg = []

        cog_modules = []
        for root, _, files in os.walk("cogs"):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    rel_path = os.path.relpath(os.path.join(root, file), ".")
                    module = rel_path.replace(os.sep, ".")[:-3]
                    cog_modules.append(module)

        loaded_extensions = list(self.bot.extensions.keys())

        print()
        for module in loaded_extensions:
            try:
                await self.bot.reload_extension(module)
                reloaded.append(module)
                cog_log.info(f"Reloaded {module}")
            except Exception as err:
                failed.append(f"{module}: {err}")
                cog_log.error(f"Failed to reload {module}: {err}")

        for module in cog_modules:
            if module not in loaded_extensions:
                try:
                    await self.bot.load_extension(module)
                    loaded.append(module)
                    cog_log.info(f"Loaded new cog {module}")
                except Exception as err:
                    failed.append(f"{module}: {err}")
                    cog_log.error(f"Failed to load {module}: {err}")

        if loaded:
            final_msg.append(f"Loaded {len(loaded)} new files")
        if reloaded:
            final_msg.append(f"Reloaded {len(reloaded)} files")
        if failed:
            final_msg.append(f"Failed to load {len(failed)} files")

        print()

        await asyncio.sleep(1)

        await msg.edit(
            embed=Embeds.checkmark(
                author=ctx.author, description=f"{f" {self.bot.bp} ".join(final_msg)}."
            )
        )


async def setup(bot):
    await bot.add_cog(Developers(bot))
