import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", 0)) or None
print(f"DEBUG - ID catégorie chargée : {TICKET_CATEGORY_ID}")

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Recrutement", value="recrutement", emoji="👤"),
            discord.SelectOption(label="Affilié", value="affilie", emoji="🤝"),
            discord.SelectOption(label="Autre demande", value="autre", emoji="❓"),
        ]
        super().__init__(placeholder="Sélectionner une catégorie", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        category = self.values[0]
        member = interaction.user
        guild = interaction.guild

        config = {
            "recrutement": {"name": "recrutement", "emoji": "👤", "color": 0x00ff00},
            "affilie": {"name": "affilie", "emoji": "🤝", "color": 0xffaa00},
            "autre": {"name": "autre-demande", "emoji": "❓", "color": 0x7289da}
        }
        cfg = config[category]

        ticket_name = f"{cfg['name']}-{member.name.lower()}"

        # Debug
        print(f"Création ticket pour {member.name} dans catégorie ID: {TICKET_CATEGORY_ID}")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        category_obj = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None
        ticket_channel = await guild.create_text_channel(
            name=ticket_name, 
            category=category_obj, 
            overwrites=overwrites
        )

        await interaction.followup.send(f"✅ Ticket créé → {ticket_channel.mention}", ephemeral=True)

        # ... (le reste du code reste le même)

        await ticket_channel.send(embed=discord.Embed(
            title=f"{cfg['emoji']} Ticket {category.title()}",
            description=f"Bonjour {member.mention},\nUn staff va te répondre bientôt.",
            color=cfg["color"]
        ))

        if category == "recrutement":
            await asyncio.sleep(1)
            await ticket_channel.send(embed=discord.Embed(
                title="📋 Questionnaire Recrutement",
                description="**Réponds aux questions suivantes :**\n1. Âge ?\n2. Disponibilités ?\n3. Expérience en ville ?\n4. Nom & Prénom IG ?\n5. Heures sur FiveM ?",
                color=0x00ff00
            ))

        view = discord.ui.View()
        close_btn = discord.ui.Button(label="Fermer le ticket", style=discord.ButtonStyle.red)
        async def close(inter: discord.Interaction):
            await inter.response.send_message("Fermeture dans 5s...", ephemeral=False)
            await asyncio.sleep(5)
            await ticket_channel.delete()
        close_btn.callback = close
        view.add_item(close_btn)
        await ticket_channel.send(view=view)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.tree.command(name="ticket", description="Panneau de tickets")
@commands.has_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(title="Centre d'assistance", description="Merci de fournir le plus d'informations pour un traitement efficace.", color=0x2b2d31)
    await interaction.response.send_message(embed=embed, view=TicketView())

@bot.event
async def on_ready():
    print(f"✅ {bot.user} est en ligne !")
    print(f"DEBUG - Catégorie Vandetta ID : {TICKET_CATEGORY_ID}")
    await bot.tree.sync()

bot.run(os.getenv("TOKEN"))
