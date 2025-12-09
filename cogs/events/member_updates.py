import discord
from discord.ext import commands
from main import Bot


class MemberUpdates(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.dbf = bot.dbf

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick == after.nick:
            return

        member_data = await self.dbf.get_member_data(
            guild_id=after.guild.id, member_id=after.id
        )
        config = member_data.get("Configuration", {})
        forced = config.get("Forced_Nickname")

        if not forced:
            return

        if after.nick == forced:
            return

        try:
            await after.edit(nick=forced, reason="Re-applying forced nickname")
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild

        guild_data = await self.dbf.get_guild_data(guild_id=guild.id)
        moderation_data = guild_data.setdefault("Moderation", {})
        hard_banned_users = moderation_data.setdefault("HardBanned_Users", [])

        if member.id in hard_banned_users:
            try:
                await guild.ban(
                    user=member,
                    reason=f"Re-Applying Hardban",
                    delete_message_seconds=86400,
                )
            except (discord.Forbidden, discord.HTTPException):
                pass


async def setup(bot):
    await bot.add_cog(MemberUpdates(bot))
