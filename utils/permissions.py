import discord
from discord.ext import commands
from utils import exceptions, helpers
from utils.messages import Embeds


async def higher_permissions(
    should_be_higher: discord.Member,
    should_be_lower: discord.Member,
    action: str = "do that to",
    can_inflict_self: bool = False,
    can_inflict_bot: bool = False,
    can_inflict_owner: bool = False,
):
    if should_be_higher.id == should_be_higher.guild.owner_id:
        if should_be_lower.id == should_be_higher.guild.me.id and not can_inflict_bot:
            raise exceptions.HierarchyCheckError(
                Embeds.warning(
                    author=should_be_higher,
                    description=f"You **can't {action}** me. Try doing it without my own commands.",
                )
            )
        return

    if should_be_lower.id == should_be_higher.id and not can_inflict_self:
        raise exceptions.HierarchyCheckError(
            Embeds.warning(
                author=should_be_higher,
                description=f"You **can't {action}** yourself.",
            )
        )

    if should_be_lower.id == should_be_higher.guild.me.id and not can_inflict_bot:
        raise exceptions.HierarchyCheckError(
            Embeds.warning(
                author=should_be_higher,
                description=f"You **can't {action}** me. Try doing it without my own commands.",
            )
        )

    if (
        should_be_lower.id == should_be_lower.guild.owner_id
        and not can_inflict_owner
        and not should_be_higher.id == should_be_lower.id
    ):
        raise exceptions.HierarchyCheckError(
            Embeds.warning(
                author=should_be_higher,
                description=f"You **can't {action}** the server owner.",
            )
        )

    if not isinstance(should_be_lower, discord.Member):
        return

    if should_be_higher.top_role.position < should_be_lower.top_role.position:
        raise exceptions.HierarchyCheckError(
            Embeds.warning(
                author=should_be_higher,
                description=f"You **can't {action}** someone who is **higher than you**.",
            )
        )
    elif should_be_higher.top_role.position == should_be_lower.top_role.position:
        raise exceptions.HierarchyCheckError(
            Embeds.warning(
                author=should_be_higher,
                description=f"You **can't {action}** someone who is **equal to you**.",
            )
        )

    bot_member = should_be_higher.guild.me
    if bot_member.top_role.position < should_be_lower.top_role.position:
        raise exceptions.HierarchyCheckError(
            Embeds.warning(
                author=should_be_higher,
                description=f"I **can't {action}** someone who is **higher than me**.",
            )
        )
    elif bot_member.top_role.position == should_be_lower.top_role.position:
        raise exceptions.HierarchyCheckError(
            Embeds.warning(
                author=should_be_higher,
                description=f"I **can't {action}** someone who is **equal to me**.",
            )
        )


async def is_antinuke_administrator(
    bot: commands.Bot, guild: discord.Guild, user: discord.User
):
    owner_id = guild.owner_id
    guild_data = await bot.dbf.get_guild_data(guild_id=guild.id)
    antinuke_data = guild_data.get("AntiNuke", {})
    antinuke_administrators = antinuke_data.get("Administrators", [])

    if user.id in antinuke_administrators or user.id == owner_id:
        return True
    return False


async def is_antiraid_administrator(
    bot: commands.Bot, guild: discord.Guild, user: discord.User
):
    owner_id = guild.owner_id
    guild_data = await bot.dbf.get_guild_data(guild_id=guild.id)
    antiraid_data = guild_data.get("AntiRaid", {})
    antiraid_administrators = antiraid_data.get("Administrators", [])

    if user.id in antiraid_administrators or user.id == owner_id:
        return True
    return False
