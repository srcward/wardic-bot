import discord
from discord.ext import commands

from typing import Optional, Union

from utils import exceptions, permissions, helpers, views, checks
from utils.messages import Embeds

from main import Bot


class Mod(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = bot.db
        self.dbf = bot.dbf

    @commands.command(
        name="ban",
        help="Ban someone from the server",
        usage="(user) [history] [reason] | wardic 1d Harassing members",
    )
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.member)
    async def ban_command(
        self, ctx: commands.Context, user: Union[discord.User, discord.Member], *args
    ):
        raw_reason = []
        delete_message_seconds = 86400

        if isinstance(user, discord.Member):
            # If `user` is a member, check if ctx.author is higher than them
            try:
                permissions.higher_permissions(
                    should_be_higher=ctx.author, should_be_lower=user, action="ban"
                )
            except exceptions.HierarchyCheckError as err:
                return await ctx.send(embed=err.embed)

        # Parsing arguments
        for arg in args:
            try:
                delete_message_seconds = helpers.parse_duration(
                    value=arg, default_unit="s", max_time="7d"
                )
                continue
            except exceptions.ParseDuration_MaxDuration as err:
                delete_message_seconds = helpers.parse_duration(
                    value="7d", default_unit="s", max_time="7d"
                )
                continue
            except ValueError:
                pass
            raw_reason.append(arg)
        reason = " ".join(raw_reason) if raw_reason else "No reason provided."

        try:
            if isinstance(user, discord.Member):
                if user.premium_since:
                    view = views.ConfirmOrDecline(owner=ctx.author, timeout=60)
                    msg = await ctx.send(
                        embed=Embeds.warning(
                            author=ctx.author,
                            description=f"Are you sure you want to **ban {user.name}**? They are **boosting the server**.",
                        ),
                        view=view,
                    )

                    await view.wait()
                    view.clear_items()
                    await msg.delete()

                    if not view.value:
                        return

            # Seeing if the user is already banned from the guild
            if await helpers.promise_ban_entry(guild=ctx.guild, user=user):
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description=f"**{user.name}** is already banned.",
                    )
                )

            await ctx.guild.ban(
                user=user,
                reason=f"Issued by {ctx.author.name} / {reason}",
                delete_message_seconds=delete_message_seconds,
            )
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to ban **{user.name}**.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't ban {user.name}**. Try again later.",
                )
            )

        await ctx.send("👍")

    @commands.command(
        name="hardban",
        help="Hardban someone from the server",
        usage="(user) [history] [reason] | wardic 1d Harassing members",
    )
    @commands.guild_only()
    @checks.is_antinuke_admin()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.member)
    async def hardban_command(
        self, ctx: commands.Context, user: Union[discord.User, discord.Member], *args
    ):
        raw_reason = []
        delete_message_seconds = 86400

        if isinstance(user, discord.Member):
            # If `user` is a member, check if ctx.author is higher than them
            try:
                permissions.higher_permissions(
                    should_be_higher=ctx.author, should_be_lower=user, action="ban"
                )
            except exceptions.HierarchyCheckError as err:
                return await ctx.send(embed=err.embed)

        # Parsing arguments
        for arg in args:
            try:
                delete_message_seconds = helpers.parse_duration(
                    value=arg, default_unit="s", max_time="7d"
                )
                continue
            except exceptions.ParseDuration_MaxDuration as err:
                delete_message_seconds = helpers.parse_duration(
                    value="7d", default_unit="s", max_time="7d"
                )
                continue
            except ValueError:
                pass
            raw_reason.append(arg)
        reason = " ".join(raw_reason) if raw_reason else "No reason provided."

        try:
            if isinstance(user, discord.Member):
                if user.premium_since:
                    view = views.ConfirmOrDecline(owner=ctx.author, timeout=60)
                    msg = await ctx.send(
                        embed=Embeds.warning(
                            author=ctx.author,
                            description=f"Are you sure you want to **hard-ban {user.name}**? They are **boosting the server**.",
                        ),
                        view=view,
                    )

                    await view.wait()
                    view.clear_items()
                    await msg.delete()

                    if not view.value:
                        return

            # Seeing if the user is already banned from the guild
            if not await helpers.promise_ban_entry(guild=ctx.guild, user=user):
                await ctx.guild.ban(
                    user=user,
                    reason=f"Issued by {ctx.author.name} / {reason}",
                    delete_message_seconds=delete_message_seconds,
                )

            guild_data = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
            moderation_data = guild_data.setdefault("Moderation", {})
            hard_banned_users = moderation_data.setdefault("HardBanned_Users", [])

            if user.id in hard_banned_users:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description=f"**{user.name}** is already hard-banned.",
                    )
                )

            hard_banned_users.append(user.id)
            await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to ban **{user.name}**.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't ban {user.name}**. Try again later.",
                )
            )

        await ctx.send("👍")

    @commands.command(
        name="softban",
        help="Ban someone from the server and instantly unban them",
        usage="(user) [reason] | wardic Harassing members",
    )
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.member)
    async def softban_command(
        self,
        ctx: commands.Context,
        user: Union[discord.User, discord.Member],
        *,
        reason: str = "No reason provided.",
    ):
        delete_message_seconds = 604800

        if isinstance(user, discord.Member):
            # If `user` is a member, check if ctx.author is higher than them
            try:
                permissions.higher_permissions(
                    should_be_higher=ctx.author, should_be_lower=user, action="ban"
                )
            except exceptions.HierarchyCheckError as err:
                return await ctx.send(embed=err.embed)

        try:
            if isinstance(user, discord.Member):
                if user.premium_since:
                    view = views.ConfirmOrDecline(owner=ctx.author, timeout=60)
                    msg = await ctx.send(
                        embed=Embeds.warning(
                            author=ctx.author,
                            description=f"Are you sure you want to **softban {user.name}**? They are **boosting the server**.",
                        ),
                        view=view,
                    )

                    await view.wait()
                    view.clear_items()
                    await msg.delete()

                    if not view.value:
                        return

            # Seeing if the user is already banned from the guild
            if await helpers.promise_ban_entry(guild=ctx.guild, user=user):
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description=f"**{user.name}** is already banned.",
                    )
                )

            await ctx.guild.ban(
                user=user,
                reason=f"Issued by {ctx.author.name} (Soft) / {reason}",
                delete_message_seconds=delete_message_seconds,
            )
            await ctx.guild.unban(
                user=user,
                reason=f"Issued by {ctx.author.name} (Soft) / {reason}",
            )
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to soft-ban **{user.name}**.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't soft-ban {user.name}**. Try again later.",
                )
            )

        await ctx.send("👍")

    @commands.command(
        name="unban",
        help="Unban someone from the server",
        usage="(user) [reason] | wardic",
    )
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.member)
    async def unban_command(
        self,
        ctx: commands.Context,
        user: discord.User,
        *,
        reason: str = "No reason provided.",
    ):
        try:
            guild_data = await self.dbf.get_guild_data(guild_id=ctx.guild.id)
            moderation_data = guild_data.setdefault("Moderation", {})
            hard_banned_users = moderation_data.setdefault("HardBanned_Users", [])

            if user.id in hard_banned_users:
                if not await permissions.is_antinuke_administrator(
                    bot=self.bot, guild=ctx.guild, user=ctx.author
                ):
                    raise exceptions.NotAntiNukeAdmin(executor=ctx.author)

                view = views.ConfirmOrDecline(owner=ctx.author, timeout=60)
                msg = await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description=f"Are you sure you want to **unban {user.name}**? They are **hard-banned**.",
                    ),
                    view=view,
                )

                await view.wait()
                view.clear_items()
                await msg.delete()

                if not view.value:
                    return

            if not await helpers.promise_ban_entry(guild=ctx.guild, user=user):
                return await ctx.send(
                    embed=Embeds.embed(
                        author=ctx.author,
                        description=f"I couldn't find a ban for **{user.name}**.",
                        emoji=":mag:",
                    )
                )

            hard_banned_users.remove(user.id)
            await self.dbf.set_guild_data(guild_id=ctx.guild.id, data=guild_data)

            await ctx.guild.unban(
                user=user,
                reason=f"Issued by {ctx.author.name} / {reason}",
            )
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to unban **{user.name}**.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't unban {user.name}**. Try again later.",
                )
            )

        await ctx.send("👍")

    @commands.command(
        name="kick",
        help="Kick someone from the server",
        usage="(member) [reason] | wardic Harassing members",
    )
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.member)
    async def kick_command(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str = "No reason provided.",
    ):
        try:
            permissions.higher_permissions(
                should_be_higher=ctx.author, should_be_lower=member, action="kick"
            )
        except exceptions.HierarchyCheckError as err:
            return await ctx.send(embed=err.embed)

        try:
            await ctx.guild.kick(
                user=member, reason=f"Issued by {ctx.author.name} / {reason}"
            )
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to kick **{member.name}**.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't kick {member.name}**. Try again later.",
                )
            )

        await ctx.send("👍")

    @commands.command(
        name="purge",
        help="Delete a large amount of messages",
        usage="(amount) [member] [reason] | 30",
        aliases=["clear", "c"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge_command(self, ctx: commands.Context, *args):
        amount = None
        member = None
        raw_reason = []

        # Parsing arguments
        for arg in args:
            if arg.isdigit() and not amount:
                amount = arg
                continue

            try:
                member = await commands.MemberConverter().convert(ctx=ctx, argument=arg)
            except commands.BadArgument:
                pass

            raw_reason.append(arg)
        reason = " ".join(raw_reason) if raw_reason else "No reason provided."

        # If the member is provided but `amount` isn't, set `amount` to 50 (easier for user)
        if member and not amount:
            amount = 50

        if not amount:
            return await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

        amount = max(5, min(int(amount), 500))  # Clamp `amount` to a max of 500

        def check(msg: discord.Message):
            if msg.pinned:
                return False
            if member:
                return msg.author.id == member.id
            return True

        try:
            await ctx.message.delete()
            await ctx.channel.purge(
                limit=amount,
                check=check,
                reason=f"Purged by {ctx.author.name} / {reason}",
                bulk=True,
            )
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to purge messages in **{ctx.channel.mention}**.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description=f"I couldn't find any messages (try a bigger search).",
                    emoji=":mag:",
                )
            )

    @commands.command(
        name="nuke",
        help="Nuke a channel",
        usage="[channel] [reason] | ",
        aliases=["boom"],
    )
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(administrator=True)
    async def nuke(self, ctx: commands.Context, *args):
        raw_reason = []
        channel = None

        for arg in args:
            try:
                channel = await commands.TextChannelConverter().convert(
                    ctx=ctx, argument=arg
                )
                continue
            except (commands.BadArgument, commands.CommandError):
                pass

            raw_reason.append(arg)

        reason = " ".join(raw_reason) if raw_reason else "No reason provided."
        channel = channel or ctx.channel

        view = views.ConfirmOrDecline(owner=ctx.author, timeout=60)
        msg = await ctx.send(
            embed=Embeds.warning(
                author=ctx.author,
                description=f"Are you sure you want to **nuke {channel.mention}**? This will **delete the channel**.",
            ),
            view=view,
        )

        await view.wait()
        view.clear_items()
        await msg.delete()

        if not view.value:
            return

        try:
            cloned = await channel.clone(
                name=channel.name,
                reason=f"Issued by {ctx.author} (Nuke) / {reason}",
                category=channel.category,
            )
            await channel.delete(
                reason=f"Issued by {ctx.author.name} (Nuke) / {reason}"
            )
            await cloned.edit(position=channel.position)
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to nuke **{ctx.channel.mention}**.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't nuke {channel.mention}**. Try again later.",
                )
            )

        await cloned.send("first")

    @commands.command(
        name="nickname",
        help="Manage a members nickname",
        usage="(member) [nickname] | wardic Wardic",
        aliases=["nick", "n"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    async def nickname(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        nickname: Optional[str] = None,
    ):
        if nickname:
            nickname = nickname[:32]

        try:
            await member.edit(nick=nickname, reason=f"Issued by {ctx.author.name}")
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to nickname **{member.name}**.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't nickname {member.mention}**. Try again later.",
                )
            )

        if nickname:
            return await ctx.send(
                embed=Embeds.checkmark(
                    author=ctx.author,
                    description=f"Updated **{member.name}**'s nickname to `{nickname}`.",
                )
            )

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Removed nickname from **{member.name}**.",
            )
        )

    @commands.command(
        name="forcenickname",
        help="Force a member's nickname",
        usage="(member) [nickname] | wardic Wardic",
        aliases=["fnick", "fn", "fnickname"],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    async def forcenickname_command(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        nickname: Optional[str] = None,
    ):
        if nickname:
            nickname = nickname[:32]

        member_data: dict = await self.dbf.get_member_data(
            guild_id=ctx.guild.id,
            member_id=member.id,
        )
        member_config: dict = member_data.setdefault("Configuration", {})
        forced = member_config.get("Forced_Nickname")

        try:
            if nickname:
                member_config["Forced_Nickname"] = nickname
            else:
                member_config.pop("Forced_Nickname", None)

            await self.dbf.set_member_data(
                guild_id=ctx.guild.id,
                member_id=member.id,
                data=member_data,
            )

            await member.edit(nick=nickname, reason=f"Issued by {ctx.author.name}")

        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing permissions** to force the nickname of **{member.name}**.",
                )
            )

        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't force nickname {member.mention}**. Try again later.",
                )
            )

        if nickname:
            return await ctx.send(
                embed=Embeds.checkmark(
                    author=ctx.author,
                    description=f"Now **forcing nickname** for **{member.name}** to `{nickname}`.",
                )
            )

        return await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Removed **forced nickname** from **{member.name}**.",
            )
        )


async def setup(bot):
    await bot.add_cog(Mod(bot))
