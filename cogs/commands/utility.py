import discord, re, roblox, random, asyncio
from discord.ext import commands
from discord.utils import utcnow

from datetime import timedelta, datetime
from typing import Optional, Union, List

from utils import helpers, views, checks
from utils.messages import Embeds, Emojis, Colours

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
        msg = await ctx.send(
            embed=Embeds.loading(
                author=ctx.author,
                description=f"Getting the profile of **[`{username}`](https://www.roblox.com/{username})**.",
            )
        )

        cookies = await self.dbf.get_roblox_cookies()
        cookies = cookies["Cookies"]
        cookie = None

        if len(cookies) >= 1:
            cookie = random.choice(cookies)
        else:
            return await ctx.send(
                embed=Embeds.issue(
                    author=ctx.author,
                    description=f"The client to view Roblox profiles is currently down. Try again later.",
                )
            )

        client = roblox.Client(token=cookie)
        cache = self.bot.cache.roblox
        profile = await cache.get(username, None)

        if not profile:
            try:
                user = await client.get_user_by_username(username=username)

                profile = {
                    "id": user.id,
                    "name": user.name,
                    "display_name": user.display_name,
                    "description": user.description,
                    "is_banned": user.is_banned,
                    "friends_count": await user.get_friend_count(),
                    "follower_count": await user.get_follower_count(),
                    "following_count": await user.get_following_count(),
                    "created_timestamp": int(user.created.timestamp()),
                }

                user_thumbnails = await client.thumbnails.get_user_avatar_thumbnails(
                    users=[user],
                    type=roblox.AvatarThumbnailType.full_body,
                    size=(420, 420),
                )

                if len(user_thumbnails) > 0:
                    profile["thumbnail"] = user_thumbnails[0].image_url

                await cache.set(key=username, value=profile)
            except roblox.TooManyRequests:
                return await ctx.send(
                    embed=Embeds.issue(
                        author=ctx.author,
                        description=f"I'm being rate-limited by Roblox. Try again later.",
                    )
                )
            except roblox.UserNotFound:
                return await ctx.send(
                    embed=Embeds.embed(
                        author=ctx.author,
                        description=f"I couldn't find a user by (`{username}`)[https://www.roblox.com/{username}]",
                        emoji=":mag:",
                    )
                )

        embed = discord.Embed()
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.description = (
            profile["description"][:600] if profile["description"] else None
        )

        embed.title = f"@{profile["name"]} {f"({profile["display_name"]})" if profile["display_name"] else ""}"
        embed.url = f"https://www.roblox.com/users/{profile["id"]}/profile"

        if profile["is_banned"]:
            embed.title = f"@{profile["name"]} (Banned)"

        if profile.get("thumbnail", None):
            embed.set_thumbnail(url=profile["thumbnail"])
            embed.colour = await helpers.image_primary_colour(url=profile["thumbnail"])

        embed.add_field(
            name="Dates",
            value=f"**Created**: <t:{profile["created_timestamp"]}:f> (<t:{profile["created_timestamp"]}:R>)",
            inline=False,
        )

        embed.add_field(name="Friends", value=profile["friends_count"])
        embed.add_field(name="Followers", value=profile["follower_count"])
        embed.add_field(name="Following", value=profile["following_count"])

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Profile",
                url=f"https://www.roblox.com/users/{profile["id"]}/profile",
            )
        )
        view.add_item(
            discord.ui.Button(
                label="Rolimons",
                url=f"https://www.rolimons.com/player/{profile["id"]}",
            )
        )

        await asyncio.sleep(1)

        await msg.edit(embed=embed, view=view)

    @commands.command(
        name="steal",
        help="Get the full-size version of an emoji or sticker",
        usage="(emoji) | :pout:",
    )
    async def steal_command(self, ctx: commands.Context, *, query: str = None):
        msg = await ctx.send(
            embed=Embeds.loading(
                author=ctx.author,
                description="Stealing **emoji/sticker**...",
            )
        )

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

            return await msg.edit(embed=embed, view=view)

        if not query:
            return await msg.edit(
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

            return await msg.edit(embed=embed, view=view)

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

                return await msg.edit(embed=embed, view=view)

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

                return await msg.edit(embed=embed, view=view)

        return await msg.edit(
            embed=Embeds.embed(
                author=ctx.author,
                description=f"I couldn't find that emoji or sticker.",
                emoji=":mag:",
            )
        )


async def setup(bot):
    await bot.add_cog(Utility(bot))
