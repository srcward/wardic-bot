import discord
from discord.ext import commands

from typing import Optional, Union
from datetime import datetime

from utils import views, helpers
from utils.messages import Embeds

from main import Bot


class Server(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.dbf = bot.dbf
        self.snipes = bot.cache.snipes
        self.img_extensions = (".png", ".jpg", ".jpeg", ".gif", ".webp")

    @staticmethod
    def parse_keyword_list(text: str) -> list[str]:
        parts = [p.strip() for p in text.split(",")]
        return [p for p in parts if p]

    async def get_or_create_automod_rule(self, guild: discord.Guild):
        rules = await guild.fetch_automod_rules()

        for rule in rules:
            if rule.name == "Keyword Filter":
                alert_action = next(
                    (
                        a
                        for a in rule.actions
                        if a.type == discord.AutoModRuleActionType.send_alert_message
                    ),
                    None,
                )

                if alert_action and alert_action.channel_id is None:
                    channel = guild.system_channel or next(
                        (
                            c
                            for c in guild.text_channels
                            if c.permissions_for(guild.me).send_messages
                        ),
                        None,
                    )
                    if channel:
                        await rule.edit(
                            actions=[
                                discord.AutoModRuleAction(
                                    type=discord.AutoModRuleActionType.send_alert_message,
                                    channel_id=channel.id,
                                ),
                                discord.AutoModRuleAction(
                                    type=discord.AutoModRuleActionType.block_message
                                ),
                            ],
                            reason="Auto-fixed missing alert channel",
                        )
                return rule

        return None

    async def create_filter_rule(
        self, guild: discord.Guild, keywords: list[str], author: discord.Member
    ):
        channel = guild.system_channel or next(
            (
                c
                for c in guild.text_channels
                if c.permissions_for(guild.me).send_messages
            ),
            None,
        )

        if channel is None:
            raise ValueError("No valid channel for AutoMod alert messages.")

        return await guild.create_automod_rule(
            name="Keyword Filter",
            enabled=True,
            event_type=discord.AutoModRuleEventType.message_send,
            trigger=discord.AutoModTrigger(
                type=discord.AutoModRuleTriggerType.keyword,
                keyword_filter=keywords,
            ),
            actions=[
                discord.AutoModRuleAction(
                    type=discord.AutoModRuleActionType.send_alert_message,
                    channel_id=channel.id,
                ),
                discord.AutoModRuleAction(
                    type=discord.AutoModRuleActionType.block_message,
                ),
            ],
            reason=f"Created by {author.name}",
        )

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
    @commands.has_permissions(manage_guild=True)
    async def alias_group(self, ctx: commands.Context, command: Optional[str] = None):
        if not ctx.invoked_subcommand:
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
    @commands.has_permissions(manage_guild=True)
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
    @commands.has_permissions(manage_guild=True)
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

    @alias_group.command(
        name="list",
        help="List all aliases in the server",
    )
    @commands.has_permissions(manage_guild=True)
    async def view_alias_command(self, ctx: commands.Context):
        guild_data: dict = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config: dict = guild_data.setdefault("Configuration", {})
        guild_aliases: dict = guild_config.setdefault("Command_Aliases", {})

        if not guild_aliases:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"There **aren't any aliases** for **{ctx.guild.name}**.",
                )
            )

        items = [
            f"`{index+1}` {alias} → {guild_aliases[alias]}"
            for index, alias in enumerate(guild_aliases)
        ]

        paginator = views.Paginator(
            bot=self.bot,
            ctx=ctx,
            items=items,
            items_per_page=10,
            embed_title=f"Aliases in {ctx.guild.name}",
            owner=ctx.author,
            owner_can_delete=True,
        )
        await paginator.start()

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

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        cache_key = f"{message.guild.id}:{message.channel.id}"
        snipes = await self.snipes.get(cache_key, [])

        attachment_url = None

        if message.attachments:
            for a in message.attachments:
                if a.filename.lower().endswith(self.img_extensions):
                    attachment_url = a.url
                    break

        data = {
            "content": message.content or "",
            "author_id": message.author.id,
            "timestamp": datetime.now().timestamp(),
            "attachment_url": attachment_url,
        }

        snipes.insert(0, data)
        snipes = snipes[:500]

        await self.snipes.set(cache_key, snipes)

    @commands.command(
        name="snipe",
        help="Snipe a deleted message",
        usage="[index] [member]",
        aliases=["s"],
    )
    @commands.guild_only()
    async def snipe_command(
        self,
        ctx: commands.Context,
        index: int = 1,
        member: Optional[discord.Member] = None,
    ):
        r_index = max(0, index - 1)

        cache_key = f"{ctx.guild.id}:{ctx.channel.id}"
        snipes = await self.snipes.get(cache_key, [])

        if member:
            snipes = [s for s in snipes if s["author_id"] == member.id]

        if not snipes:
            return await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description="There hasn't been any snipes within the last **2 hours**",
                    emoji=":mag:",
                )
            )

        if r_index >= len(snipes):
            r_index = len(snipes) - 1

        data = snipes[r_index]
        author = await helpers.promise_user(self.bot, data["author_id"])

        timestamp = float(data["timestamp"])
        attachment_url = data.get("attachment_url")

        if attachment_url:
            try:
                colour = await helpers.image_primary_colour(attachment_url)
            except:
                colour = await helpers.image_primary_colour(author.display_avatar.url)
        else:
            colour = await helpers.image_primary_colour(author.display_avatar.url)

        embed = discord.Embed(
            description=data["content"],
            colour=colour,
        )

        built_timestamp = helpers.build_duration(timestamp, 2)
        embed.set_footer(
            text=f"Deleted {built_timestamp} ago • Snipe {index}/{len(snipes)}"
        )
        embed.set_author(name=author.name, icon_url=author.display_avatar.url)

        if attachment_url:
            embed.set_image(url=attachment_url)

        await ctx.send(embed=embed)

    @commands.command(
        name="clearsnipes",
        help="Clear all snipes from the server",
        aliases=["cs", "clearsnipe"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def clear_snipes_command(self, ctx: commands.Context):
        deleted = await self.snipes.delete_pattern(f"{ctx.guild.id}:")
        await ctx.message.add_reaction("✅")

    @commands.group(
        name="configure",
        help="A group of configuration related commands",
        usage="(subcommand) (arguments) | ban block wardic",
        aliases=["settings", "config", "configuration"],
        invoke_without_command=True,
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def configure_group(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

    @configure_group.group(
        name="ban",
        help="Configure the ban command",
        usage="(subcommand) (arguments) | block wardic",
    )
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def configure_ban_group(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

    @configure_ban_group.command(
        name="block",
        help="Block a member from being banned via the wardic commands",
        usage="(user) | wardic",
        aliases=["whitelist", "noban"],
    )
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def configure_block_ban_command(self, ctx: commands.Context, *, users: str):
        raw_parts = [p.strip() for p in users.replace(",", " ").split()]
        user_ids = []
        invalid = []

        for part in raw_parts:
            try:
                ch = await commands.UserConverter().convert(ctx, part)
                user_ids.append(ch.id)
            except Exception:
                invalid.append(part)

        if not user_ids and invalid:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"Invalid users: " + f"{self.bot.bp} ".join(invalid),
                )
            )

        guild_data = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config = guild_data.setdefault("Configuration", {})
        guild_ban_config = guild_config.setdefault("Ban", {})
        blocked_users = guild_ban_config.setdefault("Blocked_Users", [])

        added = []
        removed = []

        for uid in user_ids:
            if str(uid) in blocked_users:
                blocked_users.remove(str(uid))
                removed.append(uid)
            else:
                blocked_users.append(str(uid))
                added.append(uid)

        await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)

        lines = []

        if added:
            added_users = []
            for uid in added:
                user = await helpers.promise_user(bot=self.bot, user_id=uid)
                added_users.append(user)
            added_mentions = f", ".join(u.mention for u in added_users)
            lines.append(f"**Added**: {added_mentions}")

        if removed:
            removed_users = []
            for uid in removed:
                user = await helpers.promise_user(bot=self.bot, user_id=uid)
                removed_users.append(user)
            removed_mentions = f", ".join(u.mention for u in removed_users)
            lines.append(f"**Removed**: {removed_mentions}")

        if invalid:
            invalid_list = f", ".join(invalid)
            lines.append(f"**Invalid**: {invalid_list}")

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author, description=f"{self.bot.bp} ".join(lines)
            )
        )

    @configure_group.group(
        name="purge",
        help="Configure the purge command",
        usage="(subcommand) (arguments) | block #archive",
        aliases=["clear", "c"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def configure_purge_group(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

    @configure_purge_group.command(
        name="block",
        help="Block the purge command from being ran in a channel",
        usage="(channel) | #archive #archive2",
        aliases=["disallow"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def configure_block_purge_command(
        self, ctx: commands.Context, *, channels: str
    ):
        raw_parts = [p.strip() for p in channels.replace(",", " ").split()]
        channel_ids = []
        invalid = []

        for part in raw_parts:
            try:
                ch = await commands.TextChannelConverter().convert(ctx, part)
                channel_ids.append(ch.id)
            except Exception:
                invalid.append(part)

        if not channel_ids and invalid:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"Invalid channels: " + f"{self.bot.bp} ".join(invalid),
                )
            )

        guild_data = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config = guild_data.setdefault("Configuration", {})
        guild_purge_config = guild_config.setdefault("Purge", {})
        blocked_channels = guild_purge_config.setdefault("Blocked_Channels", [])

        added = []
        removed = []

        for cid in channel_ids:
            if cid in blocked_channels:
                blocked_channels.remove(str(cid))
                removed.append(cid)
            else:
                blocked_channels.append(str(cid))
                added.append(cid)

        await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)

        lines = []

        if added:
            added_mentions = f", ".join(
                ctx.guild.get_channel(cid).mention for cid in added
            )
            lines.append(f"**Added**: {added_mentions}")

        if removed:
            removed_mentions = f", ".join(
                ctx.guild.get_channel(cid).mention for cid in removed
            )
            lines.append(f"**Removed**: {removed_mentions}")

        if invalid:
            invalid_list = f", ".join(invalid)
            lines.append(f"**Invalid**: {invalid_list}")

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author, description=f"{self.bot.bp} ".join(lines)
            )
        )

    @configure_purge_group.command(
        name="deletepinned",
        help="Allow the purge command to delete pinned messages",
        usage="(mode) | false",
        aliases=["pinned"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def configure_purge_deletepinned_command(
        self, ctx: commands.Context, type: str
    ):
        guild_data = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config = guild_data.setdefault("Configuration", {})
        guild_purge_config = guild_config.setdefault("Purge", {})
        purge_config_pinned = guild_purge_config.setdefault("Delete_Pinned", False)

        type_lower = type.lower()
        action = True

        if type_lower in ("false", "off", "no"):
            if purge_config_pinned == False:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description=f"The **delete pinned setting** is already **set to false**.",
                    )
                )
            guild_purge_config["Delete_Pinned"] = False
            action = False
        else:
            if purge_config_pinned == True:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description=f"The **delete pinned setting** is already **set to true**.",
                    )
                )
            guild_purge_config["Delete_Pinned"] = True

        await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"The purge command will **{'now' if action == True else 'no longer'} delete** pinned messages.",
            )
        )

    @commands.group(
        name="reactionrole",
        help="A group of reaction role related commands",
        usage="(subcommand) (arguments) | add 1448024306876416051 👍 @Verified",
        aliases=["rr"],
        invoke_without_command=True,
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def reactionrole_group(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

    @reactionrole_group.command(
        name="add",
        help="Create a reaction role",
        usage="[message_id] (emoji) (roles)  | 1448024306876416051 👍 @Verified",
        aliases=["new", "create"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def add_reactionrole_commands(
        self,
        ctx: commands.Context,
        message_id: Optional[int] = None,
        emoji: str = None,
        *roles: discord.Role,
    ):
        if ctx.message.reference:
            target_msg = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )

            if message_id:
                actual_emoji = str(message_id)
                actual_roles = (emoji,) + roles if emoji else roles
                emoji = actual_emoji
                roles = [
                    discord.utils.get(ctx.guild.roles, mention=r)
                    or discord.utils.get(ctx.guild.roles, name=r)
                    for r in actual_roles
                ]
                roles = [r for r in roles if r]
        else:
            if not message_id:
                return await ctx.send(
                    embed=Embeds.command(
                        command=ctx.command, author=ctx.author, prefix=ctx.prefix
                    )
                )

            try:
                target_msg = await ctx.channel.fetch_message(message_id)
            except discord.NotFound:
                raise commands.MessageNotFound(argument=message_id)
            except discord.HTTPException:
                raise commands.MessageNotFound(argument=message_id)

        if not emoji:
            return await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

        if not roles:
            return await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

        try:
            await target_msg.add_reaction(emoji)
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't add a reaction** to that message. Try again later.",
                )
            )

        guild_data = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config = guild_data.setdefault("Configuration", {})
        reaction_roles_data = guild_config.setdefault("Reaction_Roles", {})

        message_reactions = reaction_roles_data.setdefault(str(target_msg.id), {})
        message_reactions[str(emoji)] = {
            "channel_id": target_msg.channel.id,
            "role_ids": [r.id for r in roles],
        }

        await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)

        role_mentions = ", ".join([r.mention for r in roles])
        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Set `{emoji}` as a reaction role to [message]({target_msg.jump_url}) for {role_mentions}",
            )
        )

    @reactionrole_group.command(
        name="remove",
        help="Create a reaction role",
        usage="[message_id] (emoji) (roles)  | 1448024306876416051 👍 @Verified",
        aliases=["delete", "rem", "del"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def remove_reactionrole_commands(
        self,
        ctx: commands.Context,
        message_id: Optional[int] = None,
        emoji: str = None,
    ):
        if ctx.message.reference:
            target_msg_id = ctx.message.reference.message_id

            if message_id:
                emoji = str(message_id)
        else:
            if not message_id:
                return await ctx.send(
                    embed=Embeds.command(
                        command=ctx.command, author=ctx.author, prefix=ctx.prefix
                    )
                )

            target_msg_id = message_id

        if not emoji:
            return await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

        guild_data: dict = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config: dict = guild_data.setdefault("Configuration", {})
        reaction_roles_data: dict = guild_config.setdefault("Reaction_Roles", {})

        if str(target_msg_id) not in reaction_roles_data:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"There are **no reaction roles** set for that message.",
                )
            )

        message_reactions = reaction_roles_data[str(target_msg_id)]

        if str(emoji) not in message_reactions:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"There is **no reaction role** set for {emoji} on that message.",
                )
            )

        message_reactions.pop(str(emoji))

        if not message_reactions:
            reaction_roles_data.pop(str(target_msg_id))

        await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"**Removed** the reaction roles from {emoji}.",
            )
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id or payload.guild_id is None:
            return

        guild_data = await self.dbf.get_guild_data(guild_id=payload.guild_id)
        guild_config = guild_data.get("Configuration", {})
        reaction_roles_data = guild_config.get("Reaction_Roles", {})

        message_reactions = reaction_roles_data.get(str(payload.message_id), {})
        emoji_str = str(payload.emoji)

        if emoji_str in message_reactions:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)

            role_ids = message_reactions[emoji_str]["role_ids"]

            for role_id in role_ids:
                role = guild.get_role(role_id)
                if role and role not in member.roles:
                    try:
                        await member.add_roles(
                            role, reason=f"Reaction role ({payload.message_id})"
                        )
                    except discord.Forbidden:
                        pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id or not payload.guild_id:
            return

        guild_data = await self.dbf.get_guild_data(guild_id=payload.guild_id)
        guild_config = guild_data.get("Configuration", {})
        reaction_roles_data = guild_config.get("Reaction_Roles", {})

        message_reactions = reaction_roles_data.get(str(payload.message_id), {})
        emoji_str = str(payload.emoji)

        if emoji_str in message_reactions:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)

            role_ids = message_reactions[emoji_str]["role_ids"]
            for role_id in role_ids:
                role = guild.get_role(role_id)
                if role and role in member.roles:
                    try:
                        await member.remove_roles(
                            role, reason=f"Reaction role removed ({payload.message_id})"
                        )
                    except discord.Forbidden:
                        pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild_data = await self.dbf.get_guild_data(guild_id=message.guild.id)
        guild_config = guild_data.get("Configuration", {})
        autoresponder_config = guild_config.get("Auto_Responders", {})
        autoresponder_settings = autoresponder_config.get("Settings", {})
        autoresponder_list = autoresponder_config.get("List", {})
        strict_config = autoresponder_settings.get("Strict", False)

        response = None

        if strict_config:
            response = autoresponder_list.get(message.content)
        else:
            for trigger, trigger_response in autoresponder_list.items():
                if trigger.lower() in message.content.lower():
                    response = trigger_response
                    break

        if not response:
            return

        await message.channel.send(response)

    @commands.group(
        name="autoresponder",
        help="A group of auto-responder related commands",
        usage="(subcommand) (arguments) | add wardic, The king of all",
        aliases=["ars"],
        invoke_without_command=True,
    )
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def autoresponder_group(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

    @autoresponder_group.command(
        name="add",
        help="Add an auto-responder",
        usage="(trigger) (response) | wardic, The king of all",
        aliases=["create"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def add_autoresponder_command(self, ctx: commands.Context, *, args: str):
        joint = args.split(", ", 1)

        if len(joint) < 2:
            return await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

        keyword = joint[0].strip()
        response = joint[1].strip()

        if not keyword or not response:
            return await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

        guild_data = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config = guild_data.setdefault("Configuration", {})
        autoresponder_config = guild_config.setdefault("Auto_Responders", {})
        autoresponder_list = autoresponder_config.setdefault("List", {})

        if autoresponder_list.get(str(keyword)):
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"An auto-response for `{keyword}` **already exists**.",
                )
            )

        autoresponder_list[keyword] = response
        await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"**Created** an auto-response for `{keyword}`.",
            )
        )

    @autoresponder_group.command(
        name="remove",
        help="Delete an auto-responder",
        usage="(trigger) | wardic",
        aliases=["delete"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def remove_autoresponder_command(
        self, ctx: commands.Context, *, trigger: str
    ):
        guild_data = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config = guild_data.get("Configuration", {})
        autoresponder_config = guild_config.get("Auto_Responders", {})
        autoresponder_list = autoresponder_config.get("List", {})

        if not autoresponder_list.get(str(trigger)):
            return await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description=f"I **couldn't find** an auto-response for `{trigger}`.",
                    emoji=":mag:",
                )
            )

        autoresponder_list.pop(trigger)
        await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"**Removed** the auto-response for `{trigger}`.",
            )
        )

    @autoresponder_group.command(
        name="strict",
        help="Toggle the strict filter for auto-responder",
        usage="(mode) | True",
        aliases=["include"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def strict_autoresponder_command(
        self,
        ctx: commands.Context,
        mode: str = "True",
    ):
        guild_data = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
        guild_config = guild_data.setdefault("Configuration", {})
        autoresponder_config = guild_config.setdefault("Auto_Responders", {})
        autoresponder_settings = autoresponder_config.setdefault("Settings", {})

        action = False
        if mode.lower() in ("on", "yes", "y", "true", "1"):
            action = True

        autoresponder_settings["Strict"] = action
        await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Turned **{'on' if action == True else 'off'} strict mode** for auto-responder.",
            )
        )

    @commands.group(
        name="filter",
        help="A group of message filter related commands",
        usage="(subcommand) (arguments) | add Wardic Is Bad",
        invoke_without_command=True,
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def filter_group(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

    @filter_group.command(
        name="add",
        help="Add word(s) to the message filter",
        usage="(words) | Wardic Is Bad",
        aliases=["new", "cr"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_guild=True)
    async def add_filter_command(self, ctx: commands.Context, *, keywords: str):
        words = self.parse_keyword_list(text=keywords)

        if not words:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description="You must provide at least **one keyword**.",
                )
            )

        if any(len(w) < 2 for w in words):
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description="Each keyword must be **at least 2 characters**.",
                )
            )

        try:
            rule = await self.get_or_create_automod_rule(ctx.guild)

            if not rule:
                rule = await self.create_filter_rule(ctx.guild, words, ctx.author)
                return await ctx.send(
                    embed=Embeds.checkmark(
                        author=ctx.author,
                        description=f"Created filter and added **{len(words)}** {'keyword' if len(words) == 1 else "keywords"}.",
                    )
                )

            current = list(rule.trigger.keyword_filter)
            added = []

            for w in words:
                if not any(existing.lower() == w.lower() for existing in current):
                    current.append(w)
                    added.append(w)

            if not added:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description="Those keywords are already in the filter.",
                    )
                )

            await rule.edit(
                trigger=discord.AutoModTrigger(
                    type=discord.AutoModRuleTriggerType.keyword, keyword_filter=current
                ),
                reason=f"Added by {ctx.author.name}",
            )

            await ctx.send(
                embed=Embeds.checkmark(
                    author=ctx.author,
                    description=f"Added: {', '.join(f'`{w}`' for w in added)} to the filter",
                )
            )

        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to manage **Auto-Mod**.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't manange Auto-Mod**. Try again later.",
                )
            )

    @filter_group.command(
        name="remove",
        help="Remove a word from the message filter",
        usage="(words) | Wardic Is Bad",
        aliases=["delete", "rm"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_guild=True)
    async def remove_filter_command(self, ctx: commands.Context, *, keywords: str):
        words = self.parse_keyword_list(text=keywords)

        if not words:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description="You must provide at least **one keyword**.",
                )
            )

        try:
            rule = await self.get_or_create_automod_rule(ctx.guild)

            if not rule:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author, description="No filter rule exists."
                    )
                )

            current = list(rule.trigger.keyword_filter)
            removed = []

            for w in words:
                for existing in current:
                    if existing.lower() == w.lower():
                        removed.append(existing)
                        current.remove(existing)
                        break

            if not removed:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description="None of those keywords were found.",
                    )
                )

            if not current:
                await rule.delete(reason=f"Removed final word by {ctx.author.name}")
                return await ctx.send(
                    embed=Embeds.checkmark(
                        author=ctx.author,
                        description=f"Removed `{', '.join(removed)}` and deleted the rule.",
                    )
                )

            await rule.edit(
                trigger=discord.AutoModTrigger(
                    type=discord.AutoModRuleTriggerType.keyword,
                    keyword_filter=current,
                ),
                reason=f"Removed by {ctx.author.name}",
            )

            await ctx.send(
                embed=Embeds.checkmark(
                    author=ctx.author,
                    description=f"Removed: {', '.join(f'`{w}`' for w in removed)}",
                )
            )

        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description="I lack permissions to manage automod rules.",
                )
            )

    @filter_group.command(name="list", aliases=["show", "view"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_guild=True)
    async def list_filter_command(self, ctx: commands.Context):
        try:
            rule = await self.get_or_create_automod_rule(ctx.guild)

            if not rule or not rule.trigger.keyword_filter:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description="There are **no keywords** in the filter.",
                    )
                )

            keywords = [
                f"`{i+1}` {kw}" for i, kw in enumerate(rule.trigger.keyword_filter)
            ]

            paginator = views.Paginator(
                bot=self.bot,
                ctx=ctx,
                items=keywords,
                items_per_page=10,
                embed_title="Filtered Keywords",
                owner=ctx.author,
                owner_can_delete=True,
            )

            await paginator.start()

        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description="I lack permissions to manage automod rules.",
                )
            )

    @filter_group.command(name="on")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_guild=True)
    async def on_filter_command(self, ctx: commands.Context):
        try:
            rule = await self.get_or_create_automod_rule(ctx.guild)

            if not rule:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description="No filter rule exists. Add keywords first.",
                    )
                )

            if rule.enabled:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author, description="The filter is **already on**."
                    )
                )

            await rule.edit(enabled=True, reason=f"Issued by {ctx.author.name}")
            await ctx.send(
                embed=Embeds.checkmark(
                    author=ctx.author, description="The filter is now **on**."
                )
            )

        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description="I lack permissions to manage automod rules.",
                )
            )

    @filter_group.command(name="off")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_guild=True)
    async def off_filter_command(self, ctx: commands.Context):
        try:
            rule = await self.get_or_create_automod_rule(ctx.guild)

            if not rule:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description="No filter rule exists. Add keywords first.",
                    )
                )

            if not rule.enabled:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author, description="The filter is **already off**."
                    )
                )

            await rule.edit(enabled=False, reason=f"Issued by {ctx.author.name}")
            await ctx.send(
                embed=Embeds.checkmark(
                    author=ctx.author, description="The filter is now **off**."
                )
            )

        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description="I lack permissions to manage automod rules.",
                )
            )


async def setup(bot):
    await bot.add_cog(Server(bot))
