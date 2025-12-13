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
        items: list,
        *,
        items_per_page: int = 10,
        embed_title: Optional[str] = None,
        embed_description: Optional[str] = None,
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

        embed.set_author(
            name=(
                self.owner.display_name
                if isinstance(self.owner, discord.Member)
                else self.owner.name
            ),
            icon_url=self.owner.display_avatar.url,
        )

        embed.set_footer(
            text=f"Page {self.current_page + 1}/{self.total_pages} ({len(self.items)} Entries)"
        )

        return embed

    def update_buttons(self):
        self.clear_items()

        # No buttons if only one page
        if self.total_pages <= 1:
            return

        left = self.LeftButton(self)
        right = self.RightButton(self)

        left.disabled = self.current_page == 0
        right.disabled = self.current_page >= self.total_pages - 1

        self.add_item(left)
        self.add_item(right)
        self.add_item(self.JumpButton(self))

        if self.owner_can_delete:
            self.add_item(self.DeleteButton(self))

    async def start(self):
        self.message = await self.ctx.send(
            embed=self.make_embed(),
            view=self if self.total_pages > 1 else None,
        )

    # Buttons
    class LeftButton(discord.ui.Button):
        def __init__(self, paginator):
            super().__init__(
                style=discord.ButtonStyle.secondary,
                emoji="<:left:1449458849462358037>",
                row=0,
            )
            self.paginator = paginator

        async def callback(self, interaction: discord.Interaction):
            if interaction.user != self.paginator.owner:
                return await interaction.response.send_message(
                    embed=Embeds.warning(
                        author=interaction.user,
                        description="You **aren't the owner** of this embed.",
                    ),
                    ephemeral=True,
                )

            self.paginator.current_page -= 1
            self.paginator.update_buttons()
            await interaction.response.edit_message(
                embed=self.paginator.make_embed(), view=self.paginator
            )

    class RightButton(discord.ui.Button):
        def __init__(self, paginator):
            super().__init__(
                style=discord.ButtonStyle.secondary,
                emoji="<:right:1449458848304992549>",
                row=0,
            )
            self.paginator = paginator

        async def callback(self, interaction: discord.Interaction):
            if interaction.user != self.paginator.owner:
                return await interaction.response.send_message(
                    embed=Embeds.warning(
                        author=interaction.user,
                        description="You **aren't the owner** of this embed.",
                    ),
                    ephemeral=True,
                )

            self.paginator.current_page += 1
            self.paginator.update_buttons()
            await interaction.response.edit_message(
                embed=self.paginator.make_embed(), view=self.paginator
            )

    class JumpButton(discord.ui.Button):
        def __init__(self, paginator):
            super().__init__(
                style=discord.ButtonStyle.secondary,
                emoji="<:filter:1449458847063478455>",
                row=0,
            )
            self.paginator = paginator

        async def callback(self, interaction: discord.Interaction):
            if interaction.user != self.paginator.owner:
                return await interaction.response.send_message(
                    embed=Embeds.warning(
                        author=interaction.user,
                        description="You **aren't the owner** of this embed.",
                    ),
                    ephemeral=True,
                )

            await interaction.response.send_modal(
                self.paginator.JumpModal(self.paginator)
            )

    class JumpModal(discord.ui.Modal, title="Jump to page"):
        page = discord.ui.TextInput(
            label="Page number",
            placeholder="Enter a page number",
            required=True,
        )

        def __init__(self, paginator):
            super().__init__()
            self.paginator = paginator

        async def on_submit(self, interaction: discord.Interaction):
            try:
                page = int(self.page.value) - 1
            except ValueError:
                page = self.paginator.total_pages - 1

            page = max(0, min(page, self.paginator.total_pages - 1))
            self.paginator.current_page = page
            self.paginator.update_buttons()

            await interaction.response.edit_message(
                embed=self.paginator.make_embed(), view=self.paginator
            )

    class DeleteButton(discord.ui.Button):
        def __init__(self, paginator):
            super().__init__(
                style=discord.ButtonStyle.danger,
                emoji="<:cancel:1449459161510187119>",
                row=0,
            )
            self.paginator = paginator

        async def callback(self, interaction: discord.Interaction):
            if interaction.user != self.paginator.owner:
                return await interaction.response.send_message(
                    embed=Embeds.warning(
                        author=interaction.user,
                        description="You **aren't the owner** of this embed.",
                    ),
                    ephemeral=True,
                )

            try:
                await self.paginator.message.delete()
            finally:
                self.paginator.stop()
