import discord, itertools, random
from discord.ext import commands, tasks
from main import Bot


class RotatingStatus(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.dbf = bot.dbf
        self.status_cycle = None
        self.last_statuses = None

    async def cog_load(self):
        self.rotate_status.start()

    async def cog_unload(self):
        self.rotate_status.cancel()

    @tasks.loop(minutes=5)
    async def rotate_status(self):
        config: dict = await self.dbf.get_configuration()
        status_data: dict = config.setdefault("Statuses", {})

        statuses: list = status_data.setdefault(
            "List", ["i listen to esdeekid and fakemink"]
        )

        settings: dict = status_data.get("Configuration", {})
        randomized: bool = settings.get("Randomized", False)
        loop_enabled: bool = settings.get("LoopingEnabled", True)

        if not loop_enabled:
            if status_data.get("Status", None):
                await self.bot.change_presence(
                    activity=discord.CustomActivity(name=status_data["Status"])
                )
            return

        if not statuses:
            return

        if randomized:
            activity_objects = [discord.CustomActivity(name=s) for s in statuses]

            if hasattr(self, "current_status") and self.current_status:
                filtered = [
                    a for a in activity_objects if a.name != self.current_status.name
                ]
            else:
                filtered = activity_objects

            if not filtered:
                filtered = activity_objects

            next_status = random.choice(filtered)
            self.current_status = next_status

            await self.bot.change_presence(activity=next_status)
            return

        if statuses != self.last_statuses:
            self.status_cycle = itertools.cycle(
                [discord.CustomActivity(name=s) for s in statuses]
            )
            self.last_statuses = list(statuses)

        next_status = next(self.status_cycle)
        self.current_status = next_status

        await self.bot.change_presence(activity=next_status)

    @rotate_status.before_loop
    async def before_rotate(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(RotatingStatus(bot))
