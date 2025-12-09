import discord
from discord.ext import commands
from discord.utils import utcnow

from datetime import timedelta, datetime
from typing import Optional, Union, List

from utils import exceptions, permissions, helpers, views, checks
from utils.messages import Embeds
from utils.converters import PartialRole

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
            try:
                await permissions.higher_permissions(
                    should_be_higher=ctx.author, should_be_lower=user, action="ban"
                )
            except exceptions.HierarchyCheckError as err:
                return await ctx.send(embed=err.embed)

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
            try:
                await permissions.higher_permissions(
                    should_be_higher=ctx.author, should_be_lower=user, action="hardban"
                )
            except exceptions.HierarchyCheckError as err:
                return await ctx.send(embed=err.embed)

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
            try:
                await permissions.higher_permissions(
                    should_be_higher=ctx.author, should_be_lower=user, action="softban"
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
            await permissions.higher_permissions(
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
        name="timeout",
        help="Timeout a member",
        usage="(member) [duration] [reason] | wardic 5m",
        aliases=["to"]
    )
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def timeout_command(self, ctx: commands.Context, member: discord.Member, *args):
        timeout_seconds = None
        raw_duration = None
        raw_reason = []

        await permissions.higher_permissions(
            should_be_higher=ctx.author, should_be_lower=member, action="timeout"
        )

        for arg in args:
            try:
                if not timeout_seconds:
                    parsed = helpers.parse_duration(value=arg, default_unit="s", max_time=None)
                    timeout_seconds = parsed
                    raw_duration = arg
                continue
            except ValueError:
                raw_reason.append(arg)
        
        if timeout_seconds is None:
            raw_duration = "5m"
            timeout_seconds = helpers.parse_duration(value="5m", default_unit="s", max_time=None)

        reason = " ".join(raw_reason) if raw_reason else "No reason provided." 

        MAX_TIMEOUT_SECONDS = 28 * 24 * 60 * 60 - 60
        if timeout_seconds > MAX_TIMEOUT_SECONDS:
            timeout_seconds = MAX_TIMEOUT_SECONDS
            raw_duration = "28d"

        timeout_duration = timedelta(seconds=timeout_seconds)

        try:
            await member.timeout(timeout_duration, reason=f"Issued by {ctx.author.name} / {reason}")
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to timeout **{member.name}**.",
                )
            )
        except discord.HTTPException as e:
            print(f"HTTPException occurred: {str(e)}")

            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't timeout {member.name}**. Try again later. Error: {str(e)}",
                )
            )

        await ctx.send(embed=Embeds.checkmark(
            author=ctx.author,
            description=f"**{member.name}** has been timed out for **{raw_duration}**"
        ))

    @commands.command(
        name="untimeout",
        help="Remove a timeout from a member",
        usage="(member) [reason] | wardic",
        aliases=["unto"]
    )
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def untimeout_command(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
        await permissions.higher_permissions(
            should_be_higher=ctx.author, should_be_lower=member, action="timeout"
        )
            
        try:
            if not member.is_timed_out():
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description=f"**{member.name}** isn't timedout.",
                    )
                )

            await member.timeout(None, reason=f"Issued by {ctx.author.name} / {reason}")
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to remove the timeout for **{member.name}**.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't remove the timeout from {member.name}**. Try again later.",
                )
            )
        
        await ctx.send(embed=Embeds.checkmark(
            author=ctx.author,
            description=f"**{member.name}**'s timeout has been removed."
        ))


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

        if member and not amount:
            amount = 50

        if not amount:
            return await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

        amount = max(5, min(int(amount), 500))

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
                    description=f"I **couldn't nickname {member.name}**. Try again later.",
                )
            )

        if not nickname:
            return await ctx.send(
                embed=Embeds.checkmark(
                    author=ctx.author,
                    description=f"Removed nickname from **{member.name}**.",
                )
            )

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Updated **{member.name}**'s nickname to `{nickname}`.",
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
                    description=f"I **couldn't force nickname {member.name}**. Try again later.",
                )
            )

        if not nickname:
            return await ctx.send(
                embed=Embeds.checkmark(
                    author=ctx.author,
                    description=f"Removed **forced nickname** from **{member.name}**.",
                )
            )

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Now **forcing nickname** for **{member.name}** to `{nickname}`.",
            )
        )

    @commands.group(
        name="role",
        help="Add or remove roles from a member",
        usage="(member) (roles) | wardic Administrator",
        aliases=["r"],
        invoke_without_command=True,
    )
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_command(
        self, ctx: commands.Context, member: discord.Member, *args: str
    ):
        if ctx.invoked_subcommand:
            return

        if not args:
            return await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

        add: List[discord.Role] = []
        remove: List[discord.Role] = []
        skipped: List[str] = []

        roles_list = list(args)
        i = 0

        while i < len(roles_list):
            matched_role: Optional[discord.Role] = None
            matched_span = 0

            for j in range(len(roles_list), i, -1):
                phrase = " ".join(roles_list[i:j]).strip()
                if not phrase:
                    continue
                try:
                    matched_role = await PartialRole().convert(ctx, phrase)
                    matched_span = j - i
                    break
                except commands.BadArgument:
                    continue

            if matched_role is None:
                skipped.append(roles_list[i])
                i += 1
                continue

            bot_top = ctx.guild.me.top_role
            author_top = ctx.author.top_role

            if matched_role.position >= bot_top.position:
                skipped.append(matched_role.name)
            elif (
                matched_role.position >= author_top.position
                and ctx.guild.owner_id != ctx.author.id
            ):
                skipped.append(matched_role.name)
            else:
                if matched_role in member.roles:
                    remove.append(matched_role)
                else:
                    add.append(matched_role)

            i += matched_span

        if not add and not remove:
            if skipped:
                description = "Skipped: " + ", ".join(skipped)
            else:
                description = "I couldn't **add or remove** any roles."

            return await ctx.send(
                embed=Embeds.warning(author=ctx.author, description=description)
            )

        try:
            if add:
                await member.add_roles(
                    *add, reason=f"Issued by {ctx.author}", atomic=False
                )
            if remove:
                await member.remove_roles(
                    *remove, reason=f"Issued by {ctx.author}", atomic=False
                )
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing permissions** to manage roles for **{member}**.",
                )
            )
        except discord.HTTPException as e:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't manage roles for {member}**. Error: {str(e)}",
                )
            )

        msg = []

        if add:
            msg.append("**Added**: " + ", ".join(r.mention for r in add))
        if remove:
            msg.append("**Removed**: " + ", ".join(r.mention for r in remove))
        if skipped:
            msg.append("**Skipped**: " + ", ".join(skipped))

        await ctx.send(
            embed=Embeds.checkmark(author=ctx.author, description=" ".join(msg))
        )

    @role_command.command(
        name="create",
        help="Create a role",
        usage='[name] [color] [hoist] | "Administrator" True',
    )
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def create_role_command(self, ctx: commands.Context, *args):
        if not args:
            return await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

        if len(ctx.guild.roles) == 250:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"This server has the **max amount of roles** (250).",
                )
            )

        colour = None
        hoist = False
        name_parts = []

        HOIST_TRUE = {"true", "yes", "y", "hoist"}
        HOIST_FALSE = {"false", "no", "n"}

        named_colours = {
            "black": discord.Colour(0x000001),
            "white": discord.Colour(0xFFFFFF),
            "red": discord.Colour.red(),
            "blue": discord.Colour.blue(),
            "green": discord.Colour.green(),
            "purple": discord.Colour.purple(),
            "gold": discord.Colour.gold(),
            "orange": discord.Colour.orange(),
            "teal": discord.Colour.teal(),
            "darkblue": discord.Colour.dark_blue(),
            "darkgreen": discord.Colour.dark_green(),
            "darkpurple": discord.Colour.dark_purple(),
            "lightgray": discord.Colour.light_gray(),
            "darkgray": discord.Colour.dark_gray(),
            "lightgrey": discord.Colour.light_gray(),
            "darkgrey": discord.Colour.dark_gray(),
        }

        for arg in args:
            if " " in arg:
                name_parts.append(arg)
                continue

            lower = arg.lower()

            if lower in HOIST_TRUE:
                hoist = True
                continue
            if lower in HOIST_FALSE:
                hoist = False
                continue

            if lower in named_colours:
                colour = named_colours[lower]
                continue

            if (
                lower.startswith("#")
                or lower.startswith("0x")
                or all(c in "0123456789abcdef" for c in lower)
            ):
                try:
                    cleaned = lower.replace("#", "")
                    if cleaned.startswith("0x"):
                        cleaned = cleaned[2:]
                    colour = discord.Color(int(cleaned, 16))
                    continue
                except Exception:
                    pass

            name_parts.append(arg)

        name = " ".join(name_parts).strip()

        if not name:
            name = "New Role"
        if not colour:
            colour = discord.Color.default()

        new_role = await ctx.guild.create_role(
            name=name,
            colour=colour,
            hoist=hoist,
            reason=f"Created by {ctx.author.name}",
        )

        parts = [f"Created a new role {new_role.mention}"]
        if colour != discord.Color.default():
            parts.append(f"Color: `{str(colour)}`")
        if hoist:
            parts.append("Hoisted: `True`")

        description = f" {self.bot.bp} ".join(parts) + "."

        await ctx.send(
            embed=Embeds.checkmark(author=ctx.author, description=description)
        )

    @role_command.command(
        name="delete",
        help="Delete a role",
        usage="(role) | Administrator",
    )
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def delete_role_command(self, ctx: commands.Context, role: discord.Role):
        try:
            await permissions.higher_role_permissions(
                actor=ctx.author, target_role=role, action="delete"
            )
        except exceptions.HierarchyCheckError as err:
            return await ctx.send(embed=err.embed)

        view = views.ConfirmOrDecline(owner=ctx.author, timeout=60)
        msg = await ctx.send(
            embed=Embeds.warning(
                author=ctx.author,
                description=f"Are you sure you want to delete {role.mention}? Every member that has this role **will lose it**.",
            ),
            view=view,
        )

        await view.wait()
        view.clear_items()
        await msg.delete()

        if not view.value:
            return

        try:
            await role.delete(reason=f"Issued by {ctx.author.name}")
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to delete **{role.name}**.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't delete {role.name}**. Try again later.",
                )
            )

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author, description=f"Deleted the role **{role.name}**."
            )
        )

    @commands.command(
        name="lock",
        help="Lock a channel",
        usage='[channel] | #main',
    )
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock_channel_command(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        channel = channel or ctx.channel

        overwrites = {}
        for target, overwrite in channel.overwrites.items():
            new_overwrite = discord.PermissionOverwrite(**overwrite._values)
            overwrites[target] = new_overwrite
        
        everyone_role = ctx.guild.default_role
        if everyone_role not in overwrites:
            overwrites[everyone_role] = discord.PermissionOverwrite()
        
        overwrites[everyone_role].send_messages = False

        try:
            await channel.edit(overwrites=overwrites, reason=f"Locked by {ctx.author}")
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to lock **{channel.mention}**.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't lock {channel.mention}**. Try again later.",
                )
            )
        
        await ctx.send(embed=Embeds.embed(
            author=ctx.author,
            description=f"Successfully locked {channel.mention}.",
            emoji=":lock:",
            colour=0xffac33
        ))

    @commands.command(
        name="unlock",
        help="Unlock a channel",
        usage='[channel] | #main',
    )
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock_channel_command(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        channel = channel or ctx.channel

        overwrites = {}
        for target, overwrite in channel.overwrites.items():
            new_overwrite = discord.PermissionOverwrite(**overwrite._values)
            overwrites[target] = new_overwrite
        
        everyone_role = ctx.guild.default_role
        if everyone_role not in overwrites:
            overwrites[everyone_role] = discord.PermissionOverwrite()
        
        overwrites[everyone_role].send_messages = None

        try:
            await channel.edit(overwrites=overwrites, reason=f"Unlocked by {ctx.author}")
        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description=f"I'm **missing** permissions to unlock **{channel.mention}**.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"I **couldn't unlock {channel.mention}**. Try again later.",
                )
            )
        
        await ctx.send(embed=Embeds.embed(
            author=ctx.author,
            description=f"Successfully unlocked {channel.mention}.",
            emoji=":lock:",
            colour=0xffac33
        ))

async def setup(bot):
    await bot.add_cog(Mod(bot))
