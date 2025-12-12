import discord
from discord.ext import commands

from utils import helpers
from utils.messages import Embeds

from main import Bot


class Information(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.dbf = bot.dbf

    @commands.command(
        name="avatar",
        help="View a users avatar",
        usage="(user) | wardic",
        aliases=["av", "pfp"],
    )
    async def avatar_command(self, ctx: commands.Context, user: discord.User = None):
        user = user or ctx.author

        embed = discord.Embed(title=f"{user.name}'s Avatar")
        embed.set_image(url=user.display_avatar.url)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        embed.colour = colour = await helpers.image_primary_colour(
            user.display_avatar.url
        )

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Avatar",
                url=user.display_avatar.url,
                style=discord.ButtonStyle.link,
            )
        )

        await ctx.send(embed=embed, view=view)

    @commands.command(
        name="serveravatar",
        help="View a members server avatar",
        usage="(member) | wardic",
        aliases=["sav", "spfp"],
    )
    @commands.guild_only()
    async def server_avatar_command(
        self, ctx: commands.Context, member: discord.Member = None
    ):
        member = member or ctx.author

        if not member.guild_avatar:
            return await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description=f"**{member.name}** doesn't have a server avatar.",
                    emoji=":mag:",
                )
            )

        embed = discord.Embed(title=f"{member.name}'s Server Avatar")
        embed.set_image(url=member.guild_avatar.url)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        embed.colour = await helpers.image_primary_colour(member.guild_avatar.url)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Server Avatar",
                url=member.guild_avatar.url,
                style=discord.ButtonStyle.link,
            )
        )

        await ctx.send(embed=embed, view=view)

    @commands.command(
        name="banner",
        help="View a users banner",
        usage="(user) | wardic",
        aliases=["bnr"],
    )
    async def banner_command(self, ctx: commands.Context, user: discord.User = None):
        user = user or ctx.author

        user = await helpers.promise_user(bot=self.bot, user_id=user.id)
        if not user.banner:
            return await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description=f"**{user.name}** doesn't have a banner.",
                    emoji=":mag:",
                )
            )

        embed = discord.Embed(title=f"{user.name}'s Banner")
        embed.set_image(url=user.banner.url)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        embed.colour = await helpers.image_primary_colour(user.banner.url)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Banner",
                url=user.banner.url,
                style=discord.ButtonStyle.link,
            )
        )

        await ctx.send(embed=embed, view=view)

    @commands.command(
        name="serverbanner",
        help="View a members server banner",
        usage="(member) | wardic",
        aliases=["sbnr"],
    )
    @commands.guild_only()
    async def server_banner_command(
        self, ctx: commands.Context, member: discord.Member = None
    ):
        member = member or ctx.author

        member = await helpers.promise_member(guild=ctx.guild, user_id=member.id)
        if not member.guild_banner:
            return await ctx.send(
                embed=Embeds.embed(
                    author=ctx.author,
                    description=f"**{member.name}** doesn't have a server banner.",
                    emoji=":mag:",
                )
            )

        embed = discord.Embed(title=f"{member.name}'s Server Banner")
        embed.set_image(url=member.guild_banner.url)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        embed.colour = await helpers.image_primary_colour(member.guild_banner.url)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Server Banner",
                url=member.guild_banner.url,
                style=discord.ButtonStyle.link,
            )
        )

        await ctx.send(embed=embed, view=view)

    @commands.command(
        name="whois",
        help="View a users profile",
        usage="(user) | wardic",
        aliases=["userid", "uid", "wi", "ui"],
    )
    async def whois_command(self, ctx: commands.Context, user: discord.User = None):
        user = user or ctx.author
        user = await helpers.promise_user(bot=self.bot, user_id=user.id)

        member = None
        roles = []
        role_len = 0

        dates = []

        dates.append(
            f"**Created**: <t:{int(user.created_at.timestamp())}:f> (<t:{int(user.created_at.timestamp())}:R>)"
        )

        embed = discord.Embed(title=f"@{user.name} ({user.id})")
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(url=user.display_avatar.url)

        if ctx.guild:
            member = await helpers.promise_member(guild=ctx.guild, user_id=user.id)
            if member:
                roles = [
                    r.mention for r in member.roles if r != ctx.guild.default_role
                ][:13]
                role_len = len(member.roles) - 1
                dates.append(
                    f"**Joined**: <t:{int(member.joined_at.timestamp())}:f> (<t:{int(member.joined_at.timestamp())}:R>)"
                )
                if member.premium_since:
                    dates.append(
                        f"**Boosted**: <t:{int(member.premium_since.timestamp())}:f> (<t:{int(member.premium_since.timestamp())}:R>)"
                    )

        user_data = await self.dbf.get_user_data(user_id=user.id)
        badges_data = user_data.get("Badges", [])

        badges = None
        if badges_data and isinstance(badges_data, list):
            badge_list = []
            for badge in badges_data:
                if isinstance(badge, dict):
                    emoji = badge.get("emoji", "")
                    name = badge.get("name", "Unknown")
                    badge_list.append(f"{emoji} `{name}`")

            if badge_list:
                badges = ", ".join(badge_list)

        if badges:
            embed.description = badges

        embed.add_field(name="Dates", value="\n".join(dates), inline=False)

        if member:
            embed.add_field(
                name=f"Roles ({role_len})",
                value=f"{", ".join(reversed(list(roles)))}{"..." if role_len > 13 else ""}",
                inline=False,
            )

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Avatar",
                url=user.display_avatar.url,
                style=discord.ButtonStyle.link,
            )
        )

        if user.banner:
            view.add_item(
                discord.ui.Button(
                    label="Banner",
                    url=user.banner.url,
                    style=discord.ButtonStyle.link,
                )
            )

        view.add_item(
            discord.ui.Button(
                label="Profile",
                url=f"https://discord.com/users/{user.id}",
                style=discord.ButtonStyle.link,
            )
        )

        embed.colour = await helpers.image_primary_colour(user.display_avatar.url)

        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Information(bot))
