import discord, random, aiohttp
from discord.ext import commands
from main import Bot


class RolePlay(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.dbf = bot.dbf
        self.bite_gif = [
            "https://c.tenor.com/5mVQ3ffWUTgAAAAd/tenor.gif",
            "https://c.tenor.com/ECCpi63jZlUAAAAd/tenor.gif",
            "https://c.tenor.com/n__KGrZPlQEAAAAd/tenor.gif",
            "https://c.tenor.com/0neaBmDilHsAAAAd/tenor.gif",
            "https://c.tenor.com/L8GrZ1X6ThsAAAAd/tenor.gif",
            "https://c.tenor.com/2Q5mG_lvFI0AAAAd/tenor.gif",
        ]
        self.hug_gif = [
            "https://c.tenor.com/kCZjTqCKiggAAAAd/tenor.gif",
            "https://c.tenor.com/V8f3qPS23LgAAAAd/tenor.gif",
            "https://c.tenor.com/6vsKGktTOj0AAAAd/tenor.gif",
            "https://c.tenor.com/nwxXREHNog0AAAAd/tenor.gif",
            "https://c.tenor.com/WCzysUenO_UAAAAd/tenor.gif",
            "https://c.tenor.com/iyztKN68avcAAAAd/tenor.gif",
        ]
        self.kiss_gif = [
            "https://c.tenor.com/kmxEaVuW8AoAAAAd/tenor.gif",
            "https://c.tenor.com/OByUsNZJyWcAAAAd/tenor.gif",
            "https://c.tenor.com/OByUsNZJyWcAAAAd/tenor.gif",
            "https://c.tenor.com/b7DWF8ecBkIAAAAd/tenor.gif",
            "https://c.tenor.com/LrKmxrDxJN0AAAAd/tenor.gif",
            "https://c.tenor.com/cQzRWAWrN6kAAAAd/tenor.gif",
        ]

    @commands.command(
        name="bite", help="Bite another user", usage="(username) | wardic"
    )
    @commands.guild_only()
    async def bite_command(self, ctx: commands.Context, member: discord.Member):
        user_data = await self.dbf.get_user_data(user_id=ctx.author.id)
        rp_data = user_data.setdefault("RolePlay", {})
        bite_data = rp_data.setdefault("Bite", {})

        bite_data[str(member.id)] = bite_data.get(str(member.id), 0)
        bite_data[str(member.id)] += 1

        gif = random.choice(self.bite_gif)
        embed = discord.Embed(title=f"{ctx.author.name} bites {member.display_name}")
        embed.set_image(url=gif)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(
            text=f"{ctx.author.name} has bit {member.name} {bite_data[str(member.id)]} {'time' if bite_data[str(member.id)] == 1 else 'times'}"
        )

        await self.dbf.set_user_data(user_id=ctx.author.id, data=user_data)
        await ctx.send(embed=embed)

    @commands.command(name="hug", help="Hug another user", usage="(username) | wardic")
    @commands.guild_only()
    async def hug_command(self, ctx: commands.Context, member: discord.Member):
        user_data = await self.dbf.get_user_data(user_id=ctx.author.id)
        rp_data = user_data.setdefault("RolePlay", {})
        hug_data = rp_data.setdefault("Hug", {})

        hug_data[str(member.id)] = hug_data.get(str(member.id), 0)
        hug_data[str(member.id)] += 1

        gif = random.choice(self.hug_gif)
        embed = discord.Embed(title=f"{ctx.author.name} hugs {member.display_name}")
        embed.set_image(url=gif)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(
            text=f"{ctx.author.name} has hugged {member.name} {hug_data[str(member.id)]} {'time' if hug_data[str(member.id)] == 1 else 'times'}"
        )

        await self.dbf.set_user_data(user_id=ctx.author.id, data=user_data)
        await ctx.send(embed=embed)

    @commands.command(
        name="kiss", help="Kiss another user", usage="(username) | wardic"
    )
    @commands.guild_only()
    async def kiss_command(self, ctx: commands.Context, member: discord.Member):
        user_data = await self.dbf.get_user_data(user_id=ctx.author.id)
        rp_data = user_data.setdefault("RolePlay", {})
        kiss_data = rp_data.setdefault("Kiss", {})

        kiss_data[str(member.id)] = kiss_data.get(str(member.id), 0)
        kiss_data[str(member.id)] += 1

        gif = random.choice(self.kiss_gif)
        embed = discord.Embed(title=f"{ctx.author.name} kisses {member.display_name}")
        embed.set_image(url=gif)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(
            text=f"{ctx.author.name} has kissed {member.name} {kiss_data[str(member.id)]} {'time' if kiss_data[str(member.id)] == 1 else 'times'}"
        )

        await self.dbf.set_user_data(user_id=ctx.author.id, data=user_data)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(RolePlay(bot))
