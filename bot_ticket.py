import discord
from discord.ext import commands
import os
import asyncio
import json
from pathlib import Path

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== CONFIG ====================
TICKET_CATEGORY_ID = 1516575212559142994
STAFF_ROLE_NAME = "tickets"

# Fichier pour persister l'état
CONFIG_FILE = Path("ticket_config.json")

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"recrutement": True, "affilie": True}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

config = load_config()

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
        except discord.NotFound:
            pass
        except Exception as e:
            print(f"Erreur suppression ticket: {e}")

# ==================== MENU JOUEURS ====================
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Recrutement", value="recrutement", emoji="👤"),
            discord.SelectOption(label="Affilié", value="affilie", emoji="🤝"),
            discord.SelectOption(label="Autre demande", value="autre", emoji="❓"),
        ]
        super().__init__(placeholder="Sélectionner une catégorie", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        value = self.values[0]
        member = interaction.user
        guild = interaction.guild

        cfg = {
            "recrutement": {"name": "recrutement", "emoji": "👤", "color": 0x00ff00},
            "affilie": {"name": "affilie", "emoji": "🤝", "color": 0xffaa00},
            "autre": {"name": "autre-demande", "emoji": "❓", "color": 0x7289da}
        }[value]

        # Vérification que le type est activé
        if value == "recrutement" and not config["recrutement"]:
            return await interaction.followup.send("❌ Recrutement actuellement désactivé.", ephemeral=True)
        if value == "affilie" and not config["affilie"]:
            return await interaction.followup.send("❌ Système affilié actuellement désactivé.", ephemeral=True)

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

        try:
            ticket_channel = await guild.create_text_channel(
                name=ticket_name, 
                category=category, 
                overwrites=overwrites
            )
        except Exception as e:
            return await interaction.followup.send(f"❌ Erreur création ticket: {e}", ephemeral=True)

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
            q_embed = discord.Embed(
                title="📋 Questionnaire Recrutement",
                description="Merci de répondre à toutes les questions :\n\n1. Âge ?\n2. Disponibilités ?\n3. Expérience en ville ?\n4. Nom & Prénom IG ?\n5. Heures FiveM ?",
                color=0x00ff00
            )
            await ticket_channel.send(embed=q_embed)

        await ticket_channel.send(view=CloseTicketView(ticket_channel))

# ==================== PANNEAU PRINCIPAL ====================
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.refresh()

    def refresh(self):
        self.clear_items()
        self.add_item(TicketSelect())

        # Boutons staff
        self.add_item(discord.ui.Button(
            label="Recrutement",
            style=discord.ButtonStyle.green if config["recrutement"] else discord.ButtonStyle.red,
            emoji="👤",
            row=1,
            custom_id="toggle_rec"
        ))
        self.add_item(discord.ui.Button(
            label="Affilié",
            style=discord.ButtonStyle.green if config["affilie"] else discord.ButtonStyle.red,
            emoji="🤝",
            row=1,
            custom_id="toggle_aff"
        ))

    async def toggle_recrutement(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Seul un admin peut faire ça.", ephemeral=True)
        
        config["recrutement"] = not config["recrutement"]
        save_config(config)
        self.refresh()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def toggle_affilie(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Seul un admin peut faire ça.", ephemeral=True)
        
        config["affilie"] = not config["affilie"]
        save_config(config)
        self.refresh()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def get_embed(self):
        return discord.Embed(
            title="Centre d'assistance",
            description="Merci de fournir le plus d'informations pour un traitement efficace.\n\n"
                       f"**Recrutement : {'🟢 Activé' if config['recrutement'] else '🔴 Désactivé'}**\n"
                       f"**Affilié : {'🟢 Activé' if config['affilie'] else '🔴 Désactivé'}**",
            color=0x2b2d31
        )

@bot.tree.command(name="ticket", description="Envoie le panneau Centre d'assistance")
@commands.has_permissions(administrator=True)
async def ticket(interaction: discord.Interaction):
    view = TicketPanelView()
    
    # Attache les callbacks
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
        print("✅ Commandes slash synchronisées.")
    except Exception as e:
        print(f"Erreur sync : {e}")

# ==================== LANCEMENT ====================
if __name__ == "__main__":
    token = os.getenv("TOKEN")
    if not token:
        print("❌ TOKEN non trouvé dans les variables d'environnement !")
    else:
        bot.run(token)
