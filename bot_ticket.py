import discord
from discord.ext import commands
import os
import asyncio
import psycopg2
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== CONFIG ====================
LOG_CHANNEL_ID = None  # ID du salon de logs (optionnel)
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", 0)) or None
DATABASE_URL = os.getenv("DATABASE_URL")

# ==================== DATABASE ====================
def get_db():
    return psycopg2.connect(DATABASE_URL)

def migrate_database():
    with get_db() as conn:
        with conn.cursor() as c:
            c.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    ticket_id BIGINT,
                    user_id BIGINT NOT NULL,
                    username TEXT,
                    category TEXT NOT NULL,
                    channel_id BIGINT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    status TEXT DEFAULT 'open'
                );
            ''')
            conn.commit()
    print("✅ Base de données tickets prête !")

if DATABASE_URL:
    migrate_database()

# ==================== VIEWS ====================
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Recrutement", value="recrutement", emoji="👤"),
            discord.SelectOption(label="Affilié", value="affilie", emoji="🤝"),
            discord.SelectOption(label="Autre demande", value="autre", emoji="❓"),
        ]
        super().__init__(placeholder="Sélectionner une catégorie", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        category = self.values[0]
        member = interaction.user
        guild = interaction.guild

        # Configuration par catégorie
        config = {
            "recrutement": {"name": "recrutement", "emoji": "👤", "color": 0x00ff00},
            "affilie": {"name": "affilie", "emoji": "🤝", "color": 0xffaa00},
            "autre": {"name": "autre-demande", "emoji": "❓", "color": 0x7289da}
        }
        cfg = config[category]

        ticket_name = f"{cfg['name']}-{member.name.lower()}"

        # Permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        category_obj = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None

        try:
            ticket_channel = await guild.create_text_channel(
                name=ticket_name,
                category=category_obj,
                overwrites=overwrites
            )
        except Exception as e:
            return await interaction.followup.send("❌ Impossible de créer le ticket.", ephemeral=True)

        # Sauvegarde en base
        if DATABASE_URL:
            try:
                with get_db() as conn:
                    with conn.cursor() as c:
                        c.execute("""
                            INSERT INTO tickets (ticket_id, user_id, username, category, channel_id, created_at)
                            VALUES (%s, %s, %s, %s, %s, NOW())
                        """, (ticket_channel.id, member.id, member.display_name, category, ticket_channel.id))
                        conn.commit()
            except:
                pass

        await interaction.followup.send(f"✅ Ton ticket a été créé → {ticket_channel.mention}", ephemeral=True)

        # Message d'accueil
        welcome = discord.Embed(
            title=f"{cfg['emoji']} Ticket {category.title()}",
            description=f"Bonjour {member.mention},\nUn membre du staff va te répondre rapidement.",
            color=cfg["color"]
        )
        await ticket_channel.send(embed=welcome)

        # Questionnaire uniquement pour Recrutement
        if category == "recrutement":
            await asyncio.sleep(1.5)
            q_embed = discord.Embed(
                title="📋 Questionnaire Recrutement",
                description="Merci de répondre à toutes les questions ci-dessous :",
                color=0x00ff00
            )
            q_embed.add_field(
                name="Questions :",
                value=(
                    "**1.** Quel est ton **âge** ?\n"
                    "**2.** Quelles sont tes **disponibilités** ?\n"
                    "**3.** Quelle est ton **expérience en ville** (RP) ?\n"
                    "**4.** Quel est ton **nom et prénom en ville** ?\n"
                    "**5.** Combien d'**heures** as-tu sur FiveM ?"
                ),
                inline=False
            )
            await ticket_channel.send(embed=q_embed)

        # Bouton Fermer
        view = CloseTicketView(ticket_channel)
        await ticket_channel.send(view=view)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

class CloseTicketView(discord.ui.View):
    def __init__(self, channel):
        super().__init__(timeout=None)
        self.channel = channel

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.red)
    async def close_ticket(self, interaction: discord.Interaction, button):
        await interaction.response.send_message("🔒 Fermeture du ticket dans 5 secondes...", ephemeral=False)
        await asyncio.sleep(5)
        try:
            await self.channel.delete()
        except:
            pass

# ==================== COMMANDES ====================
@bot.tree.command(name="ticket", description="Envoie le panneau Centre d'assistance")
@commands.has_permissions(administrator=True)
async def send_ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Centre d'assistance",
        description="Merci de fournir le plus d'informations pour un traitement efficace.",
        color=0x2b2d31
    )
    embed.add_field(
        name="\u200b",
        value="👤 **Recrutement**\n🤝 **Affilié**\n❓ **Autre demande**",
        inline=False
    )

    view = TicketView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} est en ligne !")
    try:
        await bot.tree.sync()
        print("✅ Commandes slash synchronisées")
    except Exception as e:
        print(f"Erreur sync : {e}")

# ==================== LANCEMENT ====================
if __name__ == "__main__":
    token = os.getenv("TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ TOKEN manquant dans les variables d'environnement.")