import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

TICKET_CATEGORY_ID = 1516575212559142994
STAFF_ROLE_NAME = "tickets"

RECRUTEMENT_ENABLED = True
AFFILIE_ENABLED = True


# ==================== FERMER TICKET ====================
class CloseTicketView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel):
        super().__init__(timeout=None)
        self.channel = channel

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fermeture dans 5 secondes...", ephemeral=False)
        await asyncio.sleep(5)
        try:
            await self.channel.delete()
        except:
            pass


# ==================== MENU JOUEURS (DYNAMIQUE) ====================
# ==================== MENU JOUEURS ====================
class TicketSelect(discord.ui.Select):
    def __init__(self, recrutement: bool, affilie: bool):
        self.recrutement = recrutement
        self.affilie = affilie
        
        options = []
        if self.recrutement:
        if recrutement:
            options.append(discord.SelectOption(label="Recrutement", value="recrutement", emoji="👤"))
        if self.affilie:
        if affilie:
            options.append(discord.SelectOption(label="Affilié", value="affilie", emoji="🤝"))
        options.append(discord.SelectOption(label="Autre demande", value="autre", emoji="❓"))

@@ -106,31 +103,39 @@
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect(RECRUTEMENT_ENABLED, AFFILIE_ENABLED))
        self.refresh()

    def refresh_select(self):
        """Recrée le menu avec les bons états"""
    def refresh(self):
        """Recrée tout le panneau"""
        self.clear_items()
        self.add_item(TicketSelect(RECRUTEMENT_ENABLED, AFFILIE_ENABLED))

    @discord.ui.button(label="Recrutement", style=discord.ButtonStyle.green, emoji="👤", row=1)
    async def toggle_recrutement(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.name == STAFF_ROLE_NAME for role in interaction.user.roles):
            return await interaction.response.send_message("❌ Seul le staff peut utiliser ces boutons.", ephemeral=True)

        # Boutons de contrôle Staff (toujours présents)
        self.add_item(discord.ui.Button(
            label="Recrutement", 
            style=discord.ButtonStyle.green if RECRUTEMENT_ENABLED else discord.ButtonStyle.red,
            emoji="👤",
            row=1,
            custom_id="toggle_rec"
        ))
        self.add_item(discord.ui.Button(
            label="Affilié", 
            style=discord.ButtonStyle.green if AFFILIE_ENABLED else discord.ButtonStyle.red,
            emoji="🤝",
            row=1,
            custom_id="toggle_aff"
        ))

    async def toggle_recrutement(self, interaction: discord.Interaction):
        global RECRUTEMENT_ENABLED
        RECRUTEMENT_ENABLED = not RECRUTEMENT_ENABLED
        self.refresh_select()
        self.refresh()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Affilié", style=discord.ButtonStyle.green, emoji="🤝", row=1)
    async def toggle_affilie(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.name == STAFF_ROLE_NAME for role in interaction.user.roles):
            return await interaction.response.send_message("❌ Seul le staff peut utiliser ces boutons.", ephemeral=True)

    async def toggle_affilie(self, interaction: discord.Interaction):
        global AFFILIE_ENABLED
        AFFILIE_ENABLED = not AFFILIE_ENABLED
        self.refresh_select()
        self.refresh()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def get_embed(self):
@@ -147,17 +152,26 @@
@commands.has_permissions(administrator=True)
async def ticket(interaction: discord.Interaction):
    view = TicketPanelView()
    
    # Attache les callbacks aux boutons
    for child in view.children:
        if isinstance(child, discord.ui.Button):
            if child.custom_id == "toggle_rec":
                child.callback = view.toggle_recrutement
            elif child.custom_id == "toggle_aff":
                child.callback = view.toggle_affilie

    await interaction.response.send_message(embed=view.get_embed(), view=view)


@bot.event
async def on_ready():
    print(f"✅ {bot.user} est en ligne !")
    try:
        await bot.tree.sync()
        print("Commandes slash synchronisées.")
    except Exception as e:
        print(f"Erreur sync : {e}")


bot.run(os.getenv("TOKEN"))
