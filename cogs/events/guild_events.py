import discord, logging
from discord.ext import commands

from utils import helpers

from main import Bot

log = logging.getLogger("Main")


class GuildEvents(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        try:
            all_cached = await self.bot.cache.roles.get_all()
            guild_prefix = f"{role.guild.id}:"

            cleaned_count = 0

            for cache_key, role_ids in all_cached.items():
                if not cache_key.startswith(guild_prefix):
                    continue

                if role.id in role_ids:
                    updated_roles = [rid for rid in role_ids if rid != role.id]

                    if updated_roles:
                        await self.bot.cache.roles.set(cache_key, updated_roles)
                    else:
                        await self.bot.cache.roles.delete(cache_key)

                    cleaned_count += 1

            try:
                pass
            except Exception as e:
                log.error(f"Error cleaning role from database: {e}")

        except Exception as e:
            log.error(f"Error handling role deletion cleanup: {e}")


async def setup(bot):
    await bot.add_cog(GuildEvents(bot))
