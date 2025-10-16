import discord
from discord.ui import Button, View, Select


# ---------- Week Navigator ----------
class WeekNavigator(View):
    def __init__(self, week_embeds: list[list[discord.Embed]]):
        super().__init__(timeout=None)
        self.week_embeds = week_embeds
        self.index = len(week_embeds) - 1  # start at most recent week

        # Dropdown
        options = [
            discord.SelectOption(label=f"Week {i+1}", value=str(i))
            for i in range(len(week_embeds))
        ]
        self.select = Select(placeholder="Jump to week…", min_values=1, max_values=1, options=options)
        self.select.callback = self.jump_to_week
        self.add_item(self.select)

        # Set initial disabled state
        # (button attributes exist thanks to the decorators below)
        self._update_button_states()

    def _update_button_states(self):
        # These attributes are created by the decorators (@discord.ui.button)
        self.previous.disabled = (self.index == 0)
        self.next.disabled = (self.index == len(self.week_embeds) - 1)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary)
    async def previous(self, interaction: discord.Interaction, button: Button):
        if self.index > 0:
            self.index -= 1
        self._update_button_states()
        await interaction.response.edit_message(embeds=self.week_embeds[self.index], view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: Button):
        if self.index < len(self.week_embeds) - 1:
            self.index += 1
        self._update_button_states()
        await interaction.response.edit_message(embeds=self.week_embeds[self.index], view=self)

    @discord.ui.button(label="⏹ Reset", style=discord.ButtonStyle.danger)
    async def reset(self, interaction: discord.Interaction, button: Button):
        self.index = len(self.week_embeds) - 1
        self._update_button_states()
        await interaction.response.edit_message(embeds=self.week_embeds[self.index], view=self)

    async def jump_to_week(self, interaction: discord.Interaction):
        # value comes in as a string index from the Select
        self.index = int(self.select.values[0])
        self._update_button_states()
        await interaction.response.edit_message(embeds=self.week_embeds[self.index], view=self)