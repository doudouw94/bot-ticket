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

# ==================== CONFIG ====================
STAFF_ROLE_NAME = "tickets"   # ← Nom du rôle que tu as créé

# ==================== VIEWS ====================
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
        value = self.values[0]
        member = interaction.user
        guild = interaction.guild

        config = {
            "recrutement": {"name": "recrutement", "emoji": "👤", "color": 0x00ff00},
            "affilie": {"name": "affilie", "emoji": "🤝", "color": 0xffaa00},
            "autre": {"name": "autre-demande", "emoji": "❓", "color": 0x7289da}
        }
        cfg = config[value]

        ticket_name = f"{cfg['name']}-{member.name.lower()}"

        # Récupération du rôle staff
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        # Ajout du rôle staff
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True)

        category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None

        ticket_channel = await guild.create_text_channel(
            name=ticket_name,
            category=category,
            overwrites=overwrites
        )

        await interaction.followup.send(f"✅ Ton ticket a été créé → {ticket_channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title=f"{cfg['emoji']} Ticket {value.title()}",
            description=f"Bonjour {member.mention},\nUn membre du staff va te répondre bientôt.",
            color=cfg["color"]
        )
        if staff_role:
            embed.description += f"\n\n{staff_role.mention} un ticket a été ouvert !"
        
        await ticket_channel.send(embed=embed)

        if value == "recrutement":
            await asyncio.sleep(1.5)
            q_embed = discord.Embed(
                title="📋 Questionnaire Recrutement",
                description="Merci de répondre à toutes les questions :\n\n1. Âge ?\n2. Disponibilités ?\n3. Expérience en ville ?\n4. Nom & Prénom IG ?\n5. Heures FiveM ?",
                color=0x00ff00
            )
            await ticket_channel.send(embed=q_embed)

        # Bouton fermer
        close_btn = discord.ui.Button(label="Fermer le ticket", style=discord.ButtonStyle.red)
        async def close_callback(inter: discord.Interaction):
            await inter.response.send_message("🔒 Fermeture dans 5 secondes...", ephemeral=False)
            await asyncio.sleep(5)
            await ticket_channel.delete()
        close_btn.callback = close_callback
        view = discord.ui.View()
        view.add_item(close_btn)
        await ticket_channel.send(view=view)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.tree.command(name="ticket", description="Envoie le panneau Centre d'assistance")
@commands.has_permissions(administrator=True)
async def ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Centre d'assistance",
        description="Merci de fournir le plus d'informations pour un traitement efficace.",
        color=0x2b2d31
    )
    await interaction.response.send_message(embed=embed, view=TicketView())

@bot.event
async def on_ready():
    print(f"✅ {bot.user} est en ligne !")
    await bot.tree.sync()

bot.run(os.getenv("TOKEN"))
