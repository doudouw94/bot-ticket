import discord
from discord.ext import commands
import os
import asyncio
import json
from pathlib import Path
from datetime import datetime, UTC
import io

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== CONFIG ====================
STAFF_ROLE_NAME = "tickets"
CONFIG_FILE = Path("ticket_config.json")

CATEGORIES = {
    "recrutement": 1564652583778517123,
    "groupe_independant": 1564653168913023109,
    "affilie": 1564653286479634473,
    "autre": 1564653481825017876
}

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"recrutement": True, "affilie": True, "log_channel_id": None}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

config = load_config()

# ==================== FERMER TICKET + LOG ====================
class CloseTicketView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel = None):
        super().__init__(timeout=None)
        self.channel = channel

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = self.channel or interaction.channel
        await interaction.response.send_message("🔒 Fermeture dans 5 secondes...", ephemeral=False)

        transcript = await generate_transcript(channel, interaction.user)

        log_channel_id = config.get("log_channel_id")
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                file = discord.File(fp=transcript, filename=f"transcript-{channel.name}.txt")
                embed = discord.Embed(
                    title="📁 Ticket fermé",
                    description=f"**Salon :** {channel.name}\n**Fermé par :** {interaction.user.mention}",
                    color=discord.Color.red(),
                    timestamp=datetime.now(UTC)
                )
                await log_channel.send(embed=embed, file=file)

        await asyncio.sleep(5)
        try:
            await channel.delete()
        except discord.NotFound:
            pass
        except Exception as e:
            print(f"Erreur suppression ticket: {e}")

async def generate_transcript(channel: discord.TextChannel, closer: discord.Member):
    messages = []
    async for message in channel.history(limit=200, oldest_first=True):
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        content = message.content or "[Embed/Fichier]"
        messages.append(f"[{timestamp}] {message.author}: {content}")

    header = (
        f"=== TRANSCRIPT TICKET ===\n"
        f"Salon : {channel.name}\n"
        f"Fermé par : {closer}\n"
        f"Date : {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"{'='*40}\n\n"
    )
    content = header + "\n".join(messages)
    file = io.BytesIO(content.encode("utf-8"))
    file.seek(0)
    return file

# ==================== SELECT MENU ====================
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Recrutement", value="recrutement", emoji="👤"),
            discord.SelectOption(label="Affilié", value="affilie", emoji="🤝"),
            discord.SelectOption(label="Groupe indépendant", value="groupe_independant", emoji="🏴"),
            discord.SelectOption(label="Autre demande", value="autre", emoji="❓"),
        ]
        super().__init__(
            placeholder="Sélectionner une catégorie",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        value = self.values[0]
        member = interaction.user
        guild = interaction.guild

        cfg = {
            "recrutement": {"name": "recrutement", "emoji": "👤", "color": 0x00ff00},
            "affilie": {"name": "affilie", "emoji": "🤝", "color": 0xffaa00},
            "groupe_independant": {"name": "groupe-independant", "emoji": "🏴", "color": 0x9b59b6},
            "autre": {"name": "autre-demande", "emoji": "❓", "color": 0x7289da}
        }[value]

        if value == "recrutement" and not config["recrutement"]:
            return await interaction.followup.send("❌ Recrutement actuellement désactivé.", ephemeral=True)
        if value == "affilie" and not config["affilie"]:
            return await interaction.followup.send("❌ Système affilié actuellement désactivé.", ephemeral=True)

        ticket_name = f"{cfg['name']}-{member.name.lower()}-{member.id % 10000}"
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        overwrites = {
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        category_id = CATEGORIES.get(value)
        category = guild.get_channel(category_id) if category_id else None

        try:
            ticket_channel = await guild.create_text_channel(
                name=ticket_name,
                category=category,
                overwrites=overwrites
            )
        except Exception as e:
            return await interaction.followup.send(f"❌ Erreur création ticket : {e}", ephemeral=True)

        await interaction.followup.send(f"✅ Ton ticket a été créé → {ticket_channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title=f"{cfg['emoji']} Ticket {value.replace('_', ' ').title()}",
            description=f"Bonjour {member.mention},\nUn membre du staff va te répondre bientôt.",
            color=cfg["color"]
        )
        if staff_role:
            embed.description += f"\n\n{staff_role.mention} un ticket a été ouvert !"
        await ticket_channel.send(embed=embed)

        if value == "recrutement":
            recrutement_text = (
                "Bonjour,\n"
                "Pour un meilleur traitement de ta demande :\n\n"
                "1) Si ta demande correspond à un point ci-dessous, suis la démarche.\n"
                "2) Sinon, écris ta demande manuellement en donnant un maximum de détails.\n\n"
                "– Recrutement\n\n"
                "♕ 𝐃𝐞𝐬𝐜𝐫𝐢𝐩𝐭𝐢𝐨𝐧 𝐇𝐑𝐏 ♕\n"
                "♕︎ 𝐀𝐠𝐞 :\n"
                "♕︎ 𝐇𝐞𝐮𝐫𝐞 𝐑𝐏 (screen) :\n"
                "♕︎ 𝐏𝐨𝐬𝐬𝐢𝐛𝐢𝐥𝐢𝐭𝐞́ 𝐝𝐞 𝐆𝐎𝐏𝐫𝐨 :\n"
                "♕︎ 𝐕𝐨𝐮𝐬 𝐞̂𝐭𝐞𝐬-𝐯𝐨𝐮𝐬 𝐝𝐞́𝐣𝐚̀ 𝐟𝐚𝐢𝐭 𝐛𝐚𝐧 ?\n"
                "♕︎ 𝐃𝐢𝐬𝐩𝐨𝐧𝐢𝐛𝐢𝐥𝐢𝐭𝐞́ :\n\n"
                "♕ 𝐀𝐬𝐩𝐞𝐜𝐭 𝐜𝐫𝐢𝐦𝐢𝐧𝐞𝐥 ♕\n"
                "♕︎ 𝐓𝐞𝐬 𝐦𝐨𝐭𝐢𝐯𝐚𝐭𝐢𝐨𝐧𝐬 𝐚̀ 𝐧𝐨𝐮𝐬 𝐫𝐞𝐣𝐨𝐢𝐧𝐝𝐫𝐞 :\n"
                "♕︎ 𝐏𝐚𝐬𝐬ée 𝐎𝐫𝐠𝐚𝐧𝐢𝐬𝐚𝐭𝐢𝐨𝐧𝐬 :\n"
                "♕︎ 𝐏𝐚𝐬𝐬ée 𝐆𝐚𝐧𝐠 :\n"
                "♕︎ 𝐏𝐏𝐀 (𝐩𝐞𝐫𝐦𝐢𝐬 𝐚𝐫𝐦𝐞) :\n"
                "♕︎ 𝐀𝐫𝐦𝐞𝐬 :\n"
                "♕︎ 𝐕𝐞́𝐡𝐢𝐜𝐮𝐥𝐞 𝐩𝐞𝐫𝐬𝐨𝐧𝐧𝐞𝐥 :\n"
                "♕︎ 𝐂𝐨𝐧𝐧𝐚𝐢𝐬𝐬𝐚𝐧𝐜𝐞 𝐝𝐮 𝐫𝐞̀𝐠𝐥𝐞𝐦𝐞𝐧𝐭𝐬 :\n"
                "♕︎ 𝐂𝐨𝐧𝐧𝐚𝐢𝐬𝐬𝐚𝐧𝐜𝐞 𝐝𝐞 𝐥'𝐢𝐥𝐥𝐞́𝐠𝐚𝐥 :\n\n"
                "♕ 𝐏𝐞𝐫𝐬𝐨𝐧𝐧𝐚𝐥𝐢𝐭𝐞́ ♕\n"
                "♕︎ 𝐐𝐮𝐚𝐥𝐢𝐭𝐞́𝐬 :\n"
                "♕︎ 𝐃𝐞́𝐟𝐚𝐮𝐭𝐬 :"
            )
            q_embed = discord.Embed(title="📋 Questionnaire Recrutement", description=recrutement_text, color=0x00ff00)
            await ticket_channel.send(embed=q_embed)

        elif value == "groupe_independant":
            groupe_text = (
                "**Questionnaire Groupe Indépendant**\n\n"
                "Merci de répondre aux questions suivantes :\n\n"
                "1. **Présentation du groupe** :\n"
                "2. **Nom du groupe** :\n"
                "3. **Type de groupe** :\n"
                "4. **Activité illégale** :\n"
                "5. **Avez-vous pour objectif de passer reconnu ?** :\n"
                "6. **Êtes-vous affilié ? Si oui, quels groupes ?** :\n"
                "7. **Numéro des leads** :\n"
                "8. **Lieu du QG** :"
            )
            q_embed = discord.Embed(title="🏴 Questionnaire Groupe Indépendant", description=groupe_text, color=0x9b59b6)
            await ticket_channel.send(embed=q_embed)

        await ticket_channel.send(view=CloseTicketView(ticket_channel))

# ==================== PANNEAU PRINCIPAL ====================
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

    @discord.ui.button(label="Recrutement", emoji="👤", style=discord.ButtonStyle.green, custom_id="toggle_rec", row=1)
    async def toggle_recrutement(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Seul un admin peut faire ça.", ephemeral=True)
        config["recrutement"] = not config["recrutement"]
        save_config(config)
        button.style = discord.ButtonStyle.green if config["recrutement"] else discord.ButtonStyle.red
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Affilié", emoji="🤝", style=discord.ButtonStyle.green, custom_id="toggle_aff", row=1)
    async def toggle_affilie(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Seul un admin peut faire ça.", ephemeral=True)
        config["affilie"] = not config["affilie"]
        save_config(config)
        button.style = discord.ButtonStyle.green if config["affilie"] else discord.ButtonStyle.red
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def get_embed(self):
        return discord.Embed(
            title="Centre d'assistance",
            description=(
                "Merci de fournir le plus d'informations pour un traitement efficace.\n\n"
                f"**Recrutement : {'🟢 Activé' if config['recrutement'] else '🔴 Désactivé'}**\n"
                f"**Affilié : {'🟢 Activé' if config['affilie'] else '🔴 Désactivé'}**"
            ),
            color=0x2b2d31
        )

# ==================== COMMANDES ====================
@bot.tree.command(name="ticket", description="Envoie le panneau Centre d'assistance")
@commands.has_permissions(administrator=True)
async def ticket(interaction: discord.Interaction):
    view = TicketPanelView()
    for child in view.children:
        if isinstance(child, discord.ui.Button):
            if child.custom_id == "toggle_rec":
                child.style = discord.ButtonStyle.green if config["recrutement"] else discord.ButtonStyle.red
            elif child.custom_id == "toggle_aff":
                child.style = discord.ButtonStyle.green if config["affilie"] else discord.ButtonStyle.red
    await interaction.response.send_message(embed=view.get_embed(), view=view)

@bot.tree.command(name="setticketlog", description="Définit le salon actuel comme salon de logs des tickets")
@commands.has_permissions(administrator=True)
async def setticketlog(interaction: discord.Interaction):
    config["log_channel_id"] = interaction.channel.id
    save_config(config)
    await interaction.response.send_message(f"✅ Salon de logs défini sur {interaction.channel.mention}", ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} est en ligne !")
    bot.add_view(TicketPanelView())
    bot.add_view(CloseTicketView())
    try:
        await bot.tree.sync()
        print("✅ Commandes slash synchronisées.")
    except Exception as e:
        print(f"Erreur sync : {e}")

if __name__ == "__main__":
    token = os.getenv("TOKEN")
    if not token:
        print("❌ TOKEN non trouvé dans les variables d'environnement !")
    else:
        bot.run(token)
