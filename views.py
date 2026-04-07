import traceback
import discord


class EditModal(discord.ui.Modal):
    def __init__(
        self, latex_content: str, original_message: discord.Message, on_submit_callback
    ):
        super().__init__(title="Edit LaTeX Notes")
        self.original_message = original_message
        self.on_submit_callback = on_submit_callback

        self.textarea = discord.ui.TextInput(
            label="LaTeX Content",
            default=latex_content,
            style=discord.TextStyle.long,
            required=True,
        )
        self.add_item(self.textarea)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.on_submit_callback(
            interaction, self.original_message, self.textarea.value
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        traceback.print_exc()


class ConfirmView(discord.ui.View):
    def __init__(
        self, latex_content: str, date_str: str, edit_callback, confirm_callback
    ):
        super().__init__(timeout=300)
        self.latex_content = latex_content
        self.date_str = date_str
        self.edit_callback = edit_callback
        self.confirm_callback = confirm_callback

    @discord.ui.button(label="Confirm & Merge", style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        await self.confirm_callback(interaction)

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.secondary)
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditModal(self.latex_content, interaction.message, self.edit_callback)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.message.edit(content="Cancelled.", view=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        traceback.print_exc()
        await self.on_submit_callback(
            interaction, self.original_message, self.textarea.value
        )


class ConfirmView(discord.ui.View):
    def __init__(
        self, latex_content: str, date_str: str, edit_callback, confirm_callback
    ):
        super().__init__(timeout=300)
        self.latex_content = latex_content
        self.date_str = date_str
        self.edit_callback = edit_callback
        self.confirm_callback = confirm_callback

    @discord.ui.button(label="Confirm & Merge", style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        await self.confirm_callback(interaction)

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.secondary)
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditModal(self.latex_content, interaction.message, self.edit_callback)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(content="Cancelled.", view=None)
        await interaction.response.defer()
