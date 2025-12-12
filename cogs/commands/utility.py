import discord, re, roblox, random
from discord.ext import commands
from discord.utils import utcnow

from datetime import timedelta, datetime
from typing import Optional, Union, List

from utils import helpers, views, checks
from utils.messages import Embeds

from main import Bot


EMOJI_REGEX = re.compile(r"<(a?):(\w+):(\d+)>")


class Utility(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.dbf = bot.dbf

    @commands.command(
        name="roblox",
        help="View a Roblox profile",
        usage="(username) | roblox",
    )
    async def roblox_command(self, ctx: commands.Context, *, username: str = "Roblox"):
        cookies = await self.dbf.get_roblox_cookies()["Cookies"]
        cookie = None
        if len(cookies) >= 0:
            cookie = random.choice(cookies)

        client = roblox.Client(token=cookie)

    @commands.command(
        name="steal",
        help="Get the full-size version of an emoji or sticker",
        usage="(emoji) | :pout:",
    )
    async def steal_command(self, ctx: commands.Context, *, query: str = None):
        if ctx.message.stickers:
            sticker = ctx.message.stickers[0]
            url = sticker.url

            embed = discord.Embed(title=f"{sticker.name}")
            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.display_avatar.url
            )
            embed.colour = await helpers.image_primary_colour(url=url)
            embed.set_image(url=url)

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Sticker", url=url))

            return await ctx.send(embed=embed, view=view)

        if not query:
            return await ctx.send(
                embed=Embeds.command(
                    command=ctx.command, author=ctx.author, prefix=ctx.prefix
                )
            )

        match = EMOJI_REGEX.match(query)
        if match:
            is_animated, name, emoji_id = match.groups()
            ext = "gif" if is_animated else "png"
            url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?quality=lossless"

            embed = discord.Embed(title=f"{name}")
            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.display_avatar.url
            )
            embed.colour = await helpers.image_primary_colour(url=url)
            embed.set_image(url=url)

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Emoji", url=url))

            return await ctx.send(embed=embed, view=view)

        normalized = query.strip(":").replace(" ", "_")

        for emoji in ctx.guild.emojis:
            if emoji.name.lower() == normalized.lower():
                embed = discord.Embed(title=f"{emoji.name}")
                embed.set_author(
                    name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                )
                embed.colour = await helpers.image_primary_colour(url=emoji.url)
                embed.set_image(url=emoji.url)

                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Emoji", url=str(emoji.url)))

                return await ctx.send(embed=embed, view=view)

        for sticker in ctx.guild.stickers:
            if sticker.name.lower() == normalized.lower():
                embed = discord.Embed(title=f"{sticker.name}")
                embed.set_author(
                    name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                )
                embed.colour = await helpers.image_primary_colour(url=url)
                embed.set_image(url=sticker.url)

                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Sticker", url=sticker.url))

                return await ctx.send(embed=embed, view=view)

        return await ctx.send(
            embed=Embeds.embed(
                author=ctx.author,
                description=f"I couldn't find that emoji or sticker.",
                emoji=":mag:",
            )
        )


async def setup(bot):
    await bot.add_cog(Utility(bot))
