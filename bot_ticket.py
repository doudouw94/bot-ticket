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

# ==================== CONFIG ====================
RECRUTEMENT_ENABLED = True   # ← Change ici si tu veux démarrer désactivé


# ==================== VIEW POUR FERMER LE TICKET ====================
class CloseTicketView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel):
        super().__init__(timeout=None)
        self.channel = channel

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fermeture du ticket dans 5 secondes...", ephemeral=False)
        await asyncio.sleep(5)
        
        try:
            await self.channel.delete()
        except Exception:
            pass


# ==================== SELECT MENU DYNAMIQUE ====================
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Affilié", value="affilie", emoji="🤝"),
            discord.SelectOption(label="Autre demande", value="autre", emoji="❓"),
        ]
        
        # Ajoute Recrutement seulement s'il est activé
        if RECRUTEMENT_ENABLED:
            options.insert(0, discord.SelectOption(label="Recrutement", value="recrutement", emoji="👤"))

        super().__init__(placeholder="Sélectionner une catégorie", options=options, min_values=1, max_values=1)

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

        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

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
                description="Merci de répondre à toutes les questions :\n\n"
                            "1. Âge ?\n2. Disponibilités ?\n3. Expérience en ville ?\n"
                            "4. Nom & Prénom IG ?\n5. Heures FiveM ?",
                color=0x00ff00
            )
            await ticket_channel.send(embed=q_embed)

        # Bouton fermer
        close_view = CloseTicketView(ticket_channel)
        await ticket_channel.send(view=close_view)


# ==================== VIEW PRINCIPALE ====================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# ==================== COMMANDES DE GESTION RECRUTEMENT ====================
@bot.tree.command(name="recrutement", description="Activer ou désactiver les tickets recrutement")
@commands.has_permissions(administrator=True)
async def gestion_recrutement(interaction: discord.Interaction, etat: str):
    global RECRUTEMENT_ENABLED
    
    if etat.lower() in ["on", "activer", "enable"]:
        RECRUTEMENT_ENABLED = True
        await interaction.response.send_message("✅ Les tickets **Recrutement** sont maintenant **activés**.", ephemeral=True)
    elif etat.lower() in ["off", "désactiver", "disable"]:
        RECRUTEMENT_ENABLED = False
        await interaction.response.send_message("❌ Les tickets **Recrutement** sont maintenant **désactivés**.", ephemeral=True)
    else:
        await interaction.response.send_message("Utilise `/recrutement on` ou `/recrutement off`", ephemeral=True)


# ==================== COMMANDE PANNEAU ====================
@bot.tree.command(name="ticket", description="Envoie le panneau Centre d'assistance")
@commands.has_permissions(administrator=True)
async def ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Centre d'assistance",
        description="Merci de fournir le plus d'informations pour un traitement efficace.",
        color=0x2b2d31
    )
    await interaction.response.send_message(embed=embed, view=TicketView())


# ==================== ON READY ====================
@bot.event
async def on_ready():
    print(f"✅ {bot.user} est en ligne !")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} commandes slash synchronisées.")
    except Exception as e:
        print(f"Erreur sync : {e}")


bot.run(os.getenv("TOKEN"))
