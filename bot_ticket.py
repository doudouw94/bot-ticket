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

# ==================== MODAL RECRUTEMENT ====================
class RecrutementModal(discord.ui.Modal, title="📋 Candidature Recrutement"):
    def __init__(self):
        super().__init__(timeout=None)

        # 5 champs maximum autorisés par Discord
        self.age = discord.ui.TextInput(label="♕︎ Âge :", placeholder="18", required=True, style=discord.TextStyle.short)
        self.heure_rp = discord.ui.TextInput(label="♕︎ Heure RP (screen) :", placeholder="Ex: 250h+", required=True, style=discord.TextStyle.short)
        self.gopro = discord.ui.TextInput(label="♕︎ Possibilité de GoPro :", placeholder="Oui / Non / Parfois", required=True, style=discord.TextStyle.short)
        self.ban = discord.ui.TextInput(label="♕︎ Déjà fait ban ?", placeholder="Oui/Non + explication", required=True, style=discord.TextStyle.short)
        self.dispo = discord.ui.TextInput(label="♕︎ Disponibilité :", placeholder="Ex: Tous les soirs 20h-00h", required=True, style=discord.TextStyle.short)

        for item in [self.age, self.heure_rp, self.gopro, self.ban, self.dispo]:
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📋 Candidature Recrutement",
            description=f"**Candidat :** {interaction.user.mention}",
            color=0x00ff00,
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(name="♕︎ Âge", value=self.age.value, inline=True)
        embed.add_field(name="♕︎ Heure RP", value=self.heure_rp.value, inline=True)
        embed.add_field(name="♕︎ GoPro", value=self.gopro.value, inline=True)
        embed.add_field(name="♕︎ Ban", value=self.ban.value, inline=True)
        embed.add_field(name="♕︎ Disponibilité", value=self.dispo.value, inline=False)

        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ Ta candidature a été envoyée !", ephemeral=True)


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


# ==================== MENU JOUEURS (modifié uniquement pour recrutement) ====================
class TicketSelect(discord.ui.Select):
    def __init__(self, recrutement: bool, affilie: bool):
        options = []
        if recrutement:
            options.append(discord.SelectOption(label="Recrutement", value="recrutement", emoji="👤"))
        if affilie:
            options.append(discord.SelectOption(label="Affilié", value="affilie", emoji="🤝"))
        options.append(discord.SelectOption(label="Autre demande", value="autre", emoji="❓"))
        super().__init__(placeholder="Sélectionner une catégorie", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        value = self.values[0]
        member = interaction.user
        guild = interaction.guild

        # ===================== RECRUTEMENT =====================
        if value == "recrutement":
            modal = RecrutementModal()
            await interaction.response.send_modal(modal)   # Ouvre le formulaire
            return

        # ===================== AUTRES TICKETS (inchangé) =====================
        config = {
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
            name=ticket_name, category=category, overwrites=overwrites
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
        close_view = CloseTicketView(ticket_channel)
        await ticket_channel.send(view=close_view)


# ==================== PANNEAU PRINCIPAL (inchangé) ====================
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.refresh()

    def refresh(self):
        self.clear_items()
        self.add_item(TicketSelect(RECRUTEMENT_ENABLED, AFFILIE_ENABLED))
        self.add_item(discord.ui.Button(
            label="Recrutement",
            style=discord.ButtonStyle.green if RECRUTEMENT_ENABLED else discord.ButtonStyle.red,
            emoji="👤", row=1, custom_id="toggle_rec"
        ))
        self.add_item(discord.ui.Button(
            label="Affilié",
            style=discord.ButtonStyle.green if AFFILIE_ENABLED else discord.ButtonStyle.red,
            emoji="🤝", row=1, custom_id="toggle_aff"
        ))

    async def toggle_recrutement(self, interaction: discord.Interaction):
        global RECRUTEMENT_ENABLED
        RECRUTEMENT_ENABLED = not RECRUTEMENT_ENABLED
        self.refresh()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def toggle_affilie(self, interaction: discord.Interaction):
        global AFFILIE_ENABLED
        AFFILIE_ENABLED = not AFFILIE_ENABLED
        self.refresh()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def get_embed(self):
        return discord.Embed(
            title="Centre d'assistance",
            description="Merci de fournir le plus d'informations pour un traitement efficace.\n\n"
                       f"**Recrutement : {'🟢 Activé' if RECRUTEMENT_ENABLED else '🔴 Désactivé'}**\n"
                       f"**Affilié : {'🟢 Activé' if AFFILIE_ENABLED else '🔴 Désactivé'}**",
            color=0x2b2d31
        )


@bot.tree.command(name="ticket", description="Envoie le panneau Centre d'assistance")
@commands.has_permissions(administrator=True)
async def ticket(interaction: discord.Interaction):
    view = TicketPanelView()
   
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
