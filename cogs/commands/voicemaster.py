import discord
from discord.ext import commands
from datetime import timedelta
from utils import views, helpers, permissions
from utils.messages import Embeds
from main import Bot


class Voicemaster(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.dbf = bot.dbf

    class VoicemasterView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(
            label="Lock",
            style=discord.ButtonStyle.gray,
            custom_id="persistent_lock_button",
        )
        async def lock(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
            channel = await self.cog.owns_voicemaster(member=interaction.user)

            if channel is False:
                return await interaction.response.send_message(
                    embed=Embeds.warning(
                        author=interaction.user,
                        description="You **don't own** a voice-channel.",
                    ),
                    ephemeral=True,
                )
            if channel is None:
                return await interaction.response.send_message(
                    embed=Embeds.warning(
                        author=interaction.user,
                        description="You **aren't in** a voice-channel.",
                    ),
                    ephemeral=True,
                )

            overwrites = await permissions.merge_overwrites(
                self, channel, {"connect": False}
            )

            await channel.edit(
                overwrites=overwrites,
                reason=f"Issued by {interaction.user.name} (VoiceMaster Lock)",
            )

            await interaction.response.send_message(
                embed=Embeds.embed(
                    author=interaction.user,
                    description="Locked your **voice-channel**.",
                    emoji="🔒",
                ),
                ephemeral=True,
            )

        @discord.ui.button(
            label="Unlock",
            style=discord.ButtonStyle.gray,
            custom_id="persistent_unlock_button",
        )
        async def unlock(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
            channel = await self.cog.owns_voicemaster(member=interaction.user)

            if channel is False:
                return await interaction.response.send_message(
                    embed=Embeds.warning(
                        author=interaction.user,
                        description="You **don't own** a voice-channel.",
                    ),
                    ephemeral=True,
                )
            if channel is None:
                return await interaction.response.send_message(
                    embed=Embeds.warning(
                        author=interaction.user,
                        description="You **aren't in** a voice-channel.",
                    ),
                    ephemeral=True,
                )

            overwrites = await permissions.merge_overwrites(
                self, channel, {"connect": None}
            )

            await channel.edit(
                overwrites=overwrites,
                reason=f"Issued by {interaction.user.name} (VoiceMaster Unlock)",
            )

            await interaction.response.send_message(
                embed=Embeds.embed(
                    author=interaction.user,
                    description="Unlocked your **voice-channel**.",
                    emoji="🔓",
                ),
                ephemeral=True,
            )

    async def cog_load(self):
        self.bot.add_view(self.VoicemasterView(self))

    async def owns_voicemaster(self, member: discord.Member):
        guild = member.guild
        if not member.voice:
            return None

        guild_data = await self.dbf.get_guild_data(guild_id=guild.id)
        voicemaster_data = guild_data.get("VoiceMaster", {})
        voicemaster_channels = voicemaster_data.get("Channels", {})

        data = voicemaster_channels.get(str(member.voice.channel.id), None)
        if not data:
            return False

        if data.get("Owner") != str(member.id):
            return False

        return await helpers.promise_channel(
            guild=guild, channel_id=int(member.voice.channel.id)
        )

    @commands.group(
        name="voicemaster",
        help="A group of voicemaster related commands",
        usage="(subcommand) (arguments) | lock",
        aliases=["vc", "vm", "voice"],
        invoke_without_command=True,
    )
    @commands.guild_only()
    async def voicemaster_group(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        guild = member.guild

        if before.channel == after.channel:
            return

        guild_data = await self.dbf.get_guild_data(guild_id=guild.id)
        if not guild_data:
            return

        voicemaster_data = guild_data.get("VoiceMaster", {})
        if not voicemaster_data:
            return

        settings = voicemaster_data.get("Settings", {})
        creation_channel_id = settings.get("Creation_Channel")
        channels = voicemaster_data.get("Channels", {})

        if after.channel and creation_channel_id:
            cid = int(creation_channel_id)
            if after.channel.id == cid:
                category = after.channel.category
                overwrites = {
                    member: discord.PermissionOverwrite(
                        connect=True, manage_channels=True
                    )
                }

                new_channel = await guild.create_voice_channel(
                    name=f"{member.name}'s Channel",
                    overwrites=overwrites,
                    category=category,
                    reason=f"VoiceMaster: Created for {member}",
                )

                await member.move_to(new_channel)

                channels[str(new_channel.id)] = {
                    "Owner": str(member.id),
                }

        to_remove = []
        for ch_id, ch_data in channels.items():
            ch = guild.get_channel(int(ch_id))
            if not ch:
                to_remove.append(ch_id)
            elif len(ch.members) == 0:
                try:
                    await ch.delete(reason="VoiceMaster: Channel empty")
                except discord.Forbidden:
                    continue
                to_remove.append(ch_id)

        for ch_id in to_remove:
            channels.pop(ch_id, None)

        voicemaster_data["Channels"] = channels
        guild_data["VoiceMaster"] = voicemaster_data
        await self.dbf.set_guild_data(guild_id=guild.id, data=guild_data)

    @voicemaster_group.command(name="setup", help="Set up the voicemaster feature")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def setup_voicemaster(self, ctx: commands.Context):
        guild = ctx.guild
        guild_data = await self.dbf.get_guild_data(guild_id=guild.id)

        voicemaster_data = guild_data.get("VoiceMaster", {})
        settings = voicemaster_data.get("Settings", {})
        channels = voicemaster_data.get("Channels", {})

        created_channels = 0
        created_categories = 0

        deny_text = {
            guild.default_role: discord.PermissionOverwrite(
                send_messages=False,
                send_messages_in_threads=False,
                create_public_threads=False,
                create_private_threads=False,
                add_reactions=False,
            )
        }

        try:
            category = (
                guild.get_channel(int(settings.get("Category", 0)))
                if settings.get("Category")
                else None
            )

            if not category or not isinstance(category, discord.CategoryChannel):
                category = await guild.create_category(
                    name="VoiceMaster",
                    reason=f"Issued by {ctx.author.name} (VoiceMaster Setup)",
                )
                settings["Category"] = str(category.id)
                created_categories += 1

            creation = (
                guild.get_channel(int(settings.get("Creation_Channel", 0)))
                if settings.get("Creation_Channel")
                else None
            )

            if not creation or not isinstance(creation, discord.VoiceChannel):
                creation = await guild.create_voice_channel(
                    name="Join to Create",
                    position=1,
                    category=category,
                    overwrites=deny_text,
                    reason=f"Issued by {ctx.author.name} (VoiceMaster Setup)",
                )
                settings["Creation_Channel"] = str(creation.id)
                created_channels += 1

            interface = (
                guild.get_channel(int(settings.get("Interface_Channel", 0)))
                if settings.get("Interface_Channel")
                else None
            )

            if not interface or not isinstance(interface, discord.TextChannel):
                interface = await guild.create_text_channel(
                    name="interface",
                    position=2,
                    category=category,
                    overwrites=deny_text,
                    reason=f"Issued by {ctx.author.name} (VoiceMaster Setup)",
                )
                settings["Interface_Channel"] = str(interface.id)
                created_channels += 1

                view = self.VoicemasterView(self)
                embed = discord.Embed(title="VoiceMaster Controls")
                embed.set_author(
                    name=ctx.guild.me.name, icon_url=ctx.guild.me.display_avatar.url
                )
                await interface.send(embed=discord.Embed(), view=view)

        except discord.Forbidden:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description="I'm **missing permissions** to create channels or categories.",
                )
            )
        except discord.HTTPException:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description="I **couldn't create channels or categories**. Try again later.",
                )
            )

        voicemaster_data["Settings"] = settings
        voicemaster_data["Channels"] = channels
        guild_data["VoiceMaster"] = voicemaster_data
        await self.dbf.set_guild_data(guild_id=guild.id, data=guild_data)

        if created_channels == 0 and created_categories == 0:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description="The **VoiceMaster** module is **already setup**.",
                )
            )

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=(
                    f"Successfully set up VoiceMaster. I created {created_channels} "
                    f"{'channel' if created_channels == 1 else 'channels'} "
                    f"{f'and {created_categories} category' if created_categories >= 1 else ''}. "
                    "You can manage them however you want."
                ),
            )
        )

    @voicemaster_group.command(
        name="rename",
        help="Rename your voice channel",
        usage="(name) | Watching a Movie",
        aliases=["name"],
    )
    @commands.guild_only()
    @commands.cooldown(
        rate=1,
        per=timedelta(minutes=5).total_seconds(),
        type=commands.BucketType.member,
    )
    async def rename_voicemaster_command(self, ctx, *, name: str):
        channel = await self.owns_voicemaster(member=ctx.author)
        if channel is False:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author, description="You **don't own** a voice-channel."
                )
            )
        if channel is None:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author, description="You **aren't in** a voice-channel."
                )
            )

        name = name[:100]

        await channel.edit(
            name=name, reason=f"Issued by {ctx.author.name} (VoiceMaster Rename)"
        )

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author,
                description=f"Renamed your **voice-channel** to `{name}`.",
            )
        )

    @voicemaster_group.command(
        name="lock",
        help="Lock your voice channel",
        aliases=["l"],
    )
    @commands.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.member)
    async def lock_voicemaster_command(self, ctx):
        channel = await self.owns_voicemaster(member=ctx.author)
        if channel is False:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author, description="You **don't own** a voice-channel."
                )
            )
        if channel is None:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author, description="You **aren't in** a voice-channel."
                )
            )

        overwrites = await permissions.merge_overwrites(
            self, channel, {"connect": False}
        )

        await channel.edit(
            overwrites=overwrites,
            reason=f"Issued by {ctx.author.name} (VoiceMaster Lock)",
        )

        await ctx.send(
            embed=Embeds.embed(
                author=ctx.author,
                description="Locked your **voice-channel**.",
                emoji="🔒",
            )
        )

    @voicemaster_group.command(
        name="unlock",
        help="Unlock your voice channel",
        aliases=["ul"],
    )
    @commands.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.member)
    async def unlock_voicemaster_command(self, ctx):
        channel = await self.owns_voicemaster(member=ctx.author)
        if channel is False:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author, description="You **don't own** a voice-channel."
                )
            )
        if channel is None:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author, description="You **aren't in** a voice-channel."
                )
            )

        overwrites = await permissions.merge_overwrites(
            self, channel, {"connect": None}
        )

        await channel.edit(
            overwrites=overwrites,
            reason=f"Issued by {ctx.author.name} (VoiceMaster Unlock)",
        )

        await ctx.send(
            embed=Embeds.embed(
                author=ctx.author,
                description="Unlocked your **voice-channel**.",
                emoji="🔓",
            )
        )

    @voicemaster_group.command(
        name="hide",
        help="Hide your voice channel",
        aliases=["h"],
    )
    @commands.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.member)
    async def hide_voicemaster_command(self, ctx):
        channel = await self.owns_voicemaster(member=ctx.author)
        if channel is False:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author, description="You **don't own** a voice-channel."
                )
            )
        if channel is None:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author, description="You **aren't in** a voice-channel."
                )
            )

        overwrites = await permissions.merge_overwrites(
            self, channel, {"view_channel": False}
        )

        await channel.edit(
            overwrites=overwrites,
            reason=f"Issued by {ctx.author.name} (VoiceMaster Hide)",
        )

        await ctx.send(
            embed=Embeds.embed(
                author=ctx.author,
                description="Hidden your **voice-channel**.",
                emoji="👻",
            )
        )

    @voicemaster_group.command(
        name="reveal",
        help="Reveal your voice channel",
        aliases=["show", "unhide"],
    )
    @commands.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.member)
    async def reveal_voicemaster_command(self, ctx):
        channel = await self.owns_voicemaster(member=ctx.author)
        if channel is False:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author, description="You **don't own** a voice-channel."
                )
            )
        if channel is None:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author, description="You **aren't in** a voice-channel."
                )
            )

        overwrites = await permissions.merge_overwrites(
            self, channel, {"view_channel": None}
        )

        await channel.edit(
            overwrites=overwrites,
            reason=f"Issued by {ctx.author.name} (VoiceMaster Reveal)",
        )

        await ctx.send(
            embed=Embeds.embed(
                author=ctx.author,
                description="Revealed your **voice-channel**.",
                emoji="👁️",
            )
        )

    @voicemaster_group.command(
        name="claim", help="Claim a voice channel", aliases=["c"]
    )
    @commands.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.member)
    async def claim_voicemaster_command(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author, description="You **aren't in** a voice-channel."
                )
            )

        channel = ctx.author.voice.channel
        guild = ctx.guild

        guild_data = await self.dbf.get_guild_data(guild_id=guild.id)
        voicemaster_data = guild_data.get("VoiceMaster", {})
        voicemaster_channels = voicemaster_data.get("Channels", {})

        channel_data = voicemaster_channels.get(str(channel.id))
        if not channel_data:
            return await ctx.send(
                embed=Embeds.warning(
                    author=ctx.author,
                    description="This **isn't a VoiceMaster channel**.",
                )
            )

        current_owner_id = channel_data.get("Owner")

        if current_owner_id:
            current_owner_id_int = (
                int(current_owner_id)
                if isinstance(current_owner_id, str)
                else current_owner_id
            )

            if current_owner_id_int == ctx.author.id:
                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description="You **already own** this voice-channel.",
                    )
                )

            owner_in_channel = any(
                member.id == current_owner_id_int for member in channel.members
            )

            if owner_in_channel:
                owner = guild.get_member(current_owner_id_int)
                owner_name = owner.name if owner else "the current owner"

                return await ctx.send(
                    embed=Embeds.warning(
                        author=ctx.author,
                        description=f"You **can't claim** this channel. **{owner_name}** is still in the voice-channel.",
                    )
                )

        channel_data["Owner"] = str(ctx.author.id)
        voicemaster_channels[str(channel.id)] = channel_data
        voicemaster_data["Channels"] = voicemaster_channels
        guild_data["VoiceMaster"] = voicemaster_data

        await self.dbf.set_guild_data(guild_id=guild.id, data=guild_data)

        try:
            overwrites = channel.overwrites
            overwrites[ctx.author] = discord.PermissionOverwrite(
                connect=True, manage_channels=True
            )

            await channel.edit(
                overwrites=overwrites,
                reason=f"VoiceMaster: Claimed by {ctx.author.name}",
            )
        except discord.Forbidden:
            pass

        await ctx.send(
            embed=Embeds.checkmark(
                author=ctx.author, description="You've **claimed** this voice-channel."
            )
        )


async def setup(bot):
    await bot.add_cog(Voicemaster(bot))
