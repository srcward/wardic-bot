import discord, logging
from discord.ext import commands

from utils import helpers

from main import Bot

log = logging.getLogger("Main")


class MemberEvents(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.dbf = bot.dbf

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick:
            try:
                member_data = await self.dbf.get_member_data(
                    guild_id=after.guild.id, member_id=after.id
                )
                config = member_data.get("Configuration", {})
                forced = config.get("Forced_Nickname")

                if forced and after.nick != forced:
                    try:
                        await after.edit(
                            nick=forced, reason="Re-applying forced nickname"
                        )
                        log.info(
                            f"Re-applied forced nickname to {after} in {after.guild.name}"
                        )
                    except (discord.Forbidden, discord.HTTPException) as e:
                        log.warning(
                            f"Failed to re-apply forced nickname to {after}: {e}"
                        )
            except Exception as e:
                log.error(f"Error in forced nickname check: {e}")

        if before.roles != after.roles:
            try:
                role_ids = [
                    role.id for role in after.roles if role != after.guild.default_role
                ]

                cache_key = f"{after.guild.id}:{after.id}"
                await self.bot.cache.roles.set(cache_key, role_ids)

                log.debug(f"Updated role cache for {after} in {after.guild.name}")
            except Exception as e:
                log.error(f"Error updating role cache: {e}")

            removed_roles = set(before.roles) - set(after.roles)

            if removed_roles:
                try:
                    member_data = await self.dbf.get_member_data(
                        guild_id=after.guild.id, member_id=after.id
                    )
                    sticky_role_ids = member_data.get("Sticky_Roles", [])

                    if sticky_role_ids:
                        sticky_ids = set(
                            int(rid) if isinstance(rid, str) else rid
                            for rid in sticky_role_ids
                        )

                        roles_to_readd = []
                        for role in removed_roles:
                            if role.id in sticky_ids:
                                if role < after.guild.me.top_role and not role.managed:
                                    roles_to_readd.append(role)

                        if roles_to_readd:
                            try:
                                await after.add_roles(
                                    *roles_to_readd,
                                    reason="Sticky role - automatically re-added",
                                    atomic=False,
                                )
                                log.info(
                                    f"Re-added {len(roles_to_readd)} sticky role(s) to {after} in {after.guild.name}"
                                )
                            except (discord.Forbidden, discord.HTTPException) as e:
                                log.warning(
                                    f"Failed to re-add sticky roles to {after}: {e}"
                                )

                except Exception as e:
                    log.error(f"Error in sticky role check: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild

        try:
            guild_data = await self.dbf.get_guild_data(guild_id=guild.id)
            moderation_data = guild_data.get("Moderation", {})
            hard_banned_users = moderation_data.get("HardBanned_Users", [])

            if member.id in hard_banned_users or str(member.id) in hard_banned_users:
                try:
                    await guild.ban(
                        user=member,
                        reason="Re-applying hardban",
                        delete_message_seconds=86400,
                    )
                    log.info(f"Re-banned hard-banned user {member} in {guild.name}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    log.warning(f"Failed to re-ban hard-banned user {member}: {e}")
        except Exception as e:
            log.error(f"Error in hardban check: {e}")

        member_data = {}
        try:
            member_data = await self.dbf.get_member_data(
                guild_id=member.guild.id, member_id=member.id
            )
        except Exception as e:
            log.error(f"Error fetching member data for {member}: {e}")

        try:
            config = member_data.get("Configuration", {})
            forced_nickname = config.get("Forced_Nickname")

            if forced_nickname:
                try:
                    await member.edit(
                        nick=forced_nickname,
                        reason="Re-applying forced nickname",
                    )
                    log.info(f"Applied forced nickname to {member} in {guild.name}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    log.warning(f"Failed to apply forced nickname to {member}: {e}")
        except Exception as e:
            log.error(f"Error in forced nickname application: {e}")

        try:
            sticky_role_ids = member_data.get("Sticky_Roles", [])

            if sticky_role_ids:
                roles_to_add = []
                for role_id in sticky_role_ids:
                    role_id_int = int(role_id) if isinstance(role_id, str) else role_id
                    role = guild.get_role(role_id_int)

                    if role:
                        if role < guild.me.top_role and not role.managed:
                            roles_to_add.append(role)
                    else:
                        log.debug(
                            f"Sticky role {role_id} no longer exists in {guild.name}"
                        )

                if roles_to_add:
                    try:
                        await member.add_roles(
                            *roles_to_add,
                            reason="Re-applying sticky roles",
                            atomic=False,
                        )
                        log.info(
                            f"Restored {len(roles_to_add)} sticky role(s) to {member} in {guild.name}"
                        )
                    except (discord.Forbidden, discord.HTTPException) as e:
                        log.warning(f"Failed to restore sticky roles to {member}: {e}")
        except Exception as e:
            log.error(f"Error in sticky role restoration: {e}")


async def setup(bot):
    await bot.add_cog(MemberEvents(bot))
