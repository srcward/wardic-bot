import discord
from discord.ext import commands
from typing import List, Callable, Optional
from utils.messages import Embeds


class ConfirmOrDecline(discord.ui.View):
    def __init__(self, owner: discord.User | discord.Member, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.owner = owner
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.owner.id:
            return await interaction.response.send_message(
                embed=Embeds.warning(
                    author=interaction.user,
                    description=f"You **aren't the owner** of this embed.",
                ),
                ephemeral=True,
            )

        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.owner.id:
            return await interaction.response.send_message(
                embed=Embeds.warning(
                    author=interaction.user,
                    description=f"You **aren't the owner** of this embed.",
                ),
                ephemeral=True,
            )

        self.value = False
        self.stop()
        await interaction.response.defer()

    async def on_timeout(self):
        self.value = None
        for item in self.children:
            item.disabled = True


class Paginator(discord.ui.View):
    def __init__(
        self,
        bot: commands.Bot,
        ctx: commands.Context,
        items: List,
        *,
        items_per_page: int = 10,
        embed_title: str = None,
        embed_description: str = None,
        embed_colour: discord.Colour = None,
        format_item: Optional[Callable[[any], str]] = None,
        timeout: int = 120,
        owner: Optional[discord.User] = None,
        owner_can_delete: bool = False,
    ):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.items = items
        self.items_per_page = items_per_page
        self.embed_title = embed_title
        self.embed_description = embed_description
        self.embed_colour = embed_colour
        self.format_item = format_item or (lambda x: str(x))
        self.owner = owner or ctx.author
        self.owner_can_delete = owner_can_delete

        self.current_page = 0
        self.total_pages = max(1, (len(items) + items_per_page - 1) // items_per_page)
        self.message: Optional[discord.Message] = None

        if owner_can_delete:
            self.add_item(self.DeleteButton(self))

        self.update_buttons()

    def get_page_items(self):
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        return self.items[start:end]

    def make_embed(self) -> discord.Embed:
        page_items = self.get_page_items()
        desc = "\n".join(self.format_item(i) for i in page_items)
        embed = discord.Embed(
            title=self.embed_title,
            description=desc or self.embed_description,
            color=self.embed_colour,
        )

        if self.owner:
            embed.set_author(
                name=(
                    self.owner.display_name
                    if isinstance(self.owner, discord.Member)
                    else self.owner.name
                ),
                icon_url=self.owner.display_avatar.url,
            )

        total_entries = len(self.items)
        embed.set_footer(
            text=f"Page {self.current_page + 1}/{self.total_pages} ({total_entries} Entries)"
        )

        return embed

    def update_buttons(self):
        self.clear_items()
        self.add_item(self.LeftButton(self))
        self.add_item(self.RightButton(self))
        if self.owner_can_delete:
            self.add_item(self.DeleteButton(self))

    async def start(self):
        """Send the first embed"""
        self.update_buttons()
        self.message = await self.ctx.send(embed=self.make_embed(), view=self)

    class LeftButton(discord.ui.Button):
        def __init__(self, paginator):
            super().__init__(
                style=discord.ButtonStyle.secondary,
                emoji="<:left:1446331574328230041>",
                row=0,
            )
            self.paginator = paginator

        async def callback(self, interaction: discord.Interaction):
            if interaction.user != self.paginator.owner:
                return await interaction.response.send_message(
                    embed=Embeds.warning(
                        author=interaction.user,
                        description=f"You **aren't the owner** of this embed.",
                    ),
                    ephemeral=True,
                )

            if self.paginator.current_page > 0:
                self.paginator.current_page -= 1
                self.paginator.update_buttons()
                await interaction.response.edit_message(
                    embed=self.paginator.make_embed(), view=self.paginator
                )
            else:
                await interaction.response.defer()

    class RightButton(discord.ui.Button):
        def __init__(self, paginator):
            super().__init__(
                style=discord.ButtonStyle.secondary,
                emoji="<:right:1446331601737748553>",
                row=0,
            )
            self.paginator = paginator

        async def callback(self, interaction: discord.Interaction):
            if interaction.user != self.paginator.owner:
                return await interaction.response.send_message(
                    embed=Embeds.warning(
                        author=interaction.user,
                        description=f"You **aren't the owner** of this embed.",
                    ),
                    ephemeral=True,
                )

            if self.paginator.current_page < self.paginator.total_pages - 1:
                self.paginator.current_page += 1
                self.paginator.update_buttons()
                await interaction.response.edit_message(
                    embed=self.paginator.make_embed(), view=self.paginator
                )
            else:
                await interaction.response.defer()

    class DeleteButton(discord.ui.Button):
        def __init__(self, paginator):
            super().__init__(
                style=discord.ButtonStyle.danger,
                emoji="<:cancel:1446331629722402910>",
                row=0,
            )
            self.paginator = paginator

        async def callback(self, interaction: discord.Interaction):
            if interaction.user != self.paginator.owner:
                return await interaction.response.send_message(
                    embed=Embeds.warning(
                        author=interaction.user,
                        description=f"You **aren't the owner** of this embed.",
                    ),
                    ephemeral=True,
                )

            try:
                await self.paginator.message.delete()
            except Exception:
                pass
            self.paginator.stop()
