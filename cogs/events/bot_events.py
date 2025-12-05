import discord, asyncio
from discord.ext import commands
from main import Bot


class BotEvents(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.dbf = bot.dbf

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        config = await self.dbf.get_configuration()
        whitelisted_guilds = config.setdefault("Whitelisted_Guilds", [])

        channel = None

        if (
            guild.system_channel
            and guild.system_channel.permissions_for(guild.me).send_messages
        ):
            channel = guild.system_channel
        else:
            for c in guild.text_channels:
                if c.permissions_for(guild.me).send_messages:
                    channel = c
                    break

        if guild.id not in whitelisted_guilds:
            if channel:
                description = """
                This server isn't whitelisted, you can
                get a whitelist by asking <@988623277326991440> (@wardrealm)
                """
                embed = discord.Embed()
                embed.set_author(
                    name="Wardic is... not here.", icon_url=guild.me.display_avatar.url
                )
                embed.description = description
                await channel.send(embed=embed)

            try:
                await guild.leave()
            except discord.HTTPException:
                pass
            return

        if channel:
            description = """
            **Wardic's default prefix is `,`**
            To change the prefix, use `,prefix (prefix)`.
            Double check that the bot's role is within the
            guild's top 5 roles for it to function correctly.
            """
            embed = discord.Embed()
            embed.set_author(
                name="Wardic is here!", icon_url=guild.me.display_avatar.url
            )
            embed.description = description
            embed.set_footer(text="Thank you for choosing Wardic")
            await channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(BotEvents(bot))
