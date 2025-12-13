import discord
from discord.ext import commands


class HierarchyCheckError(Exception):
    def __init__(self, embed: discord.Embed):
        self.embed = embed
        super().__init__("Hierarchy check failed.")


class MaxDurationExceeded(Exception):
    def __init__(self, value, max):
        self.value = value
        self.max = max
        super().__init__(f"{self.value} is too much time, the max is {self.max}.")


class NotAntiNukeAdmin(commands.CheckFailure):
    def __init__(self, executor: discord.User):
        self.executor = executor
        super().__init__(f"{executor.name} isn't an AntiNuke Administrator")


class RaiseWithEmbed(commands.CheckFailure):
    def __init__(self, embed: discord.Embed):
        self.embed = embed
