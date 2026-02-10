"""
Guild Member Add Event - Boas vindas e autorole
Evento disparado quando um membro entra no servidor
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import database
from utils.embeds import EmbedBuilder


class GuildMemberAdd(commands.Cog):
    """Event handler para novos membros"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Executado quando membro entra no servidor"""
        try:
            # Buscar configurações do servidor
            settings = await database.get_guild_settings(str(member.guild.id))

            if not settings:
                return

            # 🎭 Aplicar autorole
            await self.apply_autorole(member, settings)

            # 👋 Enviar boas-vindas
            await self.send_welcome_message(member, settings)

            # 📊 Atualizar estatísticas
            await self.update_member_stats(member)

        except Exception as e:
            print(f"❌ Erro no evento member_join: {e}")

    async def apply_autorole(self, member: discord.Member, settings: dict):
        """Aplicar autorole automaticamente"""
        try:
            autorole_id = settings.get("autorole_id")

            if not autorole_id:
                return

            role = member.guild.get_role(int(autorole_id))
            if not role:
                return

            # Verificar se bot tem permissão
            if not member.guild.me.guild_permissions.manage_roles:
                return

            # Verificar hierarquia
            if role >= member.guild.me.top_role:
                return

            await member.add_roles(role, reason="Autorole automático")
            print(f"✅ Autorole aplicado: {role.name} para {member}")

        except Exception as e:
            print(f"❌ Erro aplicando autorole: {e}")

    async def send_welcome_message(self, member: discord.Member, settings: dict):
        """Enviar mensagem de boas-vindas"""
        try:
            welcome_channel_id = settings.get("welcome_channel_id")

            if not welcome_channel_id:
                return

            welcome_channel = member.guild.get_channel(int(welcome_channel_id))
            if not welcome_channel:
                return

            # Buscar configuração de welcome
            welcome_config = settings.get(
                "welcome_config",
                {
                    "enabled": True,
                    "title": f"Bem-vindo(a) ao {member.guild.name}!",
                    "message": "Olá {user.mention}! Seja muito bem-vindo(a) ao nosso servidor! 🎉",
                    "color": "#00ff00",
                    "show_avatar": True,
                    "show_member_count": True,
                },
            )

            if not welcome_config.get("enabled", True):
                return

            # Criar embed de boas-vindas
            embed = discord.Embed(
                title=welcome_config.get("title", f"Bem-vindo(a) ao {member.guild.name}!"),
                description=self.format_welcome_message(welcome_config.get("message", ""), member),
                color=EmbedBuilder.parse_color(welcome_config.get("color", "#00ff00")),
            )

            # Thumbnail com avatar do usuário
            if welcome_config.get("show_avatar", True):
                embed.set_thumbnail(url=member.display_avatar.url)

            # Fields informativos
            embed.add_field(name="👤 Membro", value=f"{member.mention}\\n`{member}`", inline=True)

            embed.add_field(
                name="📅 Conta criada",
                value=f"<t:{int(member.created_at.timestamp())}:R>",
                inline=True,
            )

            if welcome_config.get("show_member_count", True):
                embed.add_field(
                    name="👥 Total de membros",
                    value=f"**{member.guild.member_count:,}**",
                    inline=True,
                )

            # Imagem personalizada se configurada
            if welcome_config.get("image_url"):
                embed.set_image(url=welcome_config["image_url"])

            embed.set_footer(text=f"ID: {member.id}")
            embed.timestamp = discord.utils.utcnow()

            await welcome_channel.send(embed=embed)

            # Enviar DM se configurado
            if welcome_config.get("send_dm", False):
                await self.send_welcome_dm(member, welcome_config)

        except Exception as e:
            print(f"❌ Erro enviando boas-vindas: {e}")

    def format_welcome_message(self, message: str, member: discord.Member) -> str:
        """Formatar mensagem de boas-vindas com variáveis"""
        replacements = {
            "{user}": member.mention,
            "{user.name}": member.name,
            "{user.mention}": member.mention,
            "{guild}": member.guild.name,
            "{guild.name}": member.guild.name,
            "{member_count}": str(member.guild.member_count),
            "{server}": member.guild.name,
        }

        for placeholder, replacement in replacements.items():
            message = message.replace(placeholder, replacement)

        return message

    async def send_welcome_dm(self, member: discord.Member, welcome_config: dict):
        """Enviar DM de boas-vindas"""
        try:
            dm_message = welcome_config.get(
                "dm_message",
                f"Bem-vindo(a) ao **{member.guild.name}**! Esperamos que se divirta conosco! 🎉",
            )

            embed = discord.Embed(
                title=f"Bem-vindo(a) ao {member.guild.name}!",
                description=self.format_welcome_message(dm_message, member),
                color=EmbedBuilder.parse_color(welcome_config.get("color", "#00ff00")),
            )

            embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)

            await member.send(embed=embed)

        except discord.Forbidden:
            # Usuário não aceita DMs
            pass
        except Exception as e:
            print(f"❌ Erro enviando DM de boas-vindas: {e}")

    async def update_member_stats(self, member: discord.Member):
        """Atualizar estatísticas de membros"""
        try:
            await database.run(
                "INSERT OR IGNORE INTO member_stats (guild_id, user_id, join_date) VALUES (?, ?, ?)",
                (str(member.guild.id), str(member.id), member.joined_at.isoformat()),
            )

        except Exception as e:
            print(f"❌ Erro atualizando stats: {e}")


async def setup(bot):
    """Setup function para carregar o cog"""
    await bot.add_cog(GuildMemberAdd(bot))
