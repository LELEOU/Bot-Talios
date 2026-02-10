"""
Antispam Handler - Sistema de anti-spam
Detecta e previne spam de mensagens
"""

import sys
import time
from collections import defaultdict
from pathlib import Path

import discord
from discord.ext import commands

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import database


class AntispamHandler(commands.Cog):
    """Handler para sistema anti-spam"""

    def __init__(self, bot):
        self.bot = bot
        self.user_messages = defaultdict(list)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Verificar mensagens por spam"""
        if message.author.bot:
            return

        if not message.guild:
            return

        try:
            # Buscar configuração de antispam
            config = await self.get_antispam_config(message.guild.id)
            if not config or not config.get("enabled"):
                return

            # Verificar spam
            await self.check_spam(message, config)

        except Exception as e:
            print(f"❌ Erro no antispam handler: {e}")

    async def get_antispam_config(self, guild_id: int) -> dict:
        """Buscar configuração de antispam"""
        try:
            result = await database.fetchone(
                "SELECT * FROM antispam_config WHERE guild_id = ?", (str(guild_id),)
            )

            if result:
                return {
                    "enabled": bool(result.get("enabled", 1)),
                    "limite": result.get("limite", 5),
                    "intervalo": result.get("intervalo", 10),
                    "acao": result.get("acao", "delete"),
                    "warn_message": result.get(
                        "warn_message", "⚠️ Você está enviando mensagens muito rapidamente!"
                    ),
                }

            return None

        except Exception as e:
            print(f"❌ Erro buscando config antispam: {e}")
            return None

    async def check_spam(self, message: discord.Message, config: dict):
        """Verificar se mensagem é spam"""
        try:
            now = time.time()
            user_id = message.author.id

            # Limpar mensagens antigas do cache
            self.user_messages[user_id] = [
                timestamp
                for timestamp in self.user_messages[user_id]
                if now - timestamp < config["intervalo"]
            ]

            # Adicionar timestamp atual
            self.user_messages[user_id].append(now)

            # Verificar se excedeu o limite
            if len(self.user_messages[user_id]) > config["limite"]:
                await self.handle_spam_detected(message, config)

        except Exception as e:
            print(f"❌ Erro verificando spam: {e}")

    async def handle_spam_detected(self, message: discord.Message, config: dict):
        """Tratar spam detectado"""
        try:
            # Deletar mensagem
            if config["acao"] in ["delete", "warn", "mute", "kick", "ban"]:
                try:
                    await message.delete()
                except discord.NotFound:
                    pass  # Mensagem já foi deletada

            # Executar ação configurada
            if config["acao"] == "warn":
                await self.warn_user(message, config)
            elif config["acao"] == "mute":
                await self.mute_user(message, config)
            elif config["acao"] == "kick":
                await self.kick_user(message, config)
            elif config["acao"] == "ban":
                await self.ban_user(message, config)

            # Log do spam
            await self.log_spam(message, config)

        except Exception as e:
            print(f"❌ Erro tratando spam: {e}")

    async def warn_user(self, message: discord.Message, config: dict):
        """Avisar usuário sobre spam"""
        try:
            embed = discord.Embed(
                title="⚠️ Anti-Spam",
                description=config.get(
                    "warn_message", "⚠️ Você está enviando mensagens muito rapidamente!"
                ),
                color=0xFF9900,
            )

            embed.add_field(
                name="Limite",
                value=f"{config['limite']} mensagens em {config['intervalo']}s",
                inline=False,
            )

            # Tentar enviar DM
            try:
                await message.author.send(embed=embed)
            except discord.Forbidden:
                # Se não conseguir DM, enviar no canal (temporário)
                warning_msg = await message.channel.send(
                    f"{message.author.mention}", embed=embed, delete_after=10
                )

        except Exception as e:
            print(f"❌ Erro enviando warn de spam: {e}")

    async def mute_user(self, message: discord.Message, config: dict):
        """Mutar usuário por spam"""
        try:
            # Buscar ou criar role de mute
            mute_role = discord.utils.get(message.guild.roles, name="Muted")

            if not mute_role:
                mute_role = await message.guild.create_role(
                    name="Muted", permissions=discord.Permissions(send_messages=False, speak=False)
                )

                # Configurar permissões do mute em todos os canais
                for channel in message.guild.channels:
                    await channel.set_permissions(mute_role, send_messages=False, speak=False)

            # Aplicar mute temporário (5 minutos)
            await message.author.add_roles(mute_role, reason="Anti-spam automático")

            # Agendar remoção do mute (implementar sistema de tasks temporárias se necessário)

        except Exception as e:
            print(f"❌ Erro mutando usuário: {e}")

    async def kick_user(self, message: discord.Message, config: dict):
        """Expulsar usuário por spam"""
        try:
            if message.guild.me.guild_permissions.kick_members:
                await message.author.kick(reason="Anti-spam automático")

        except Exception as e:
            print(f"❌ Erro expulsando usuário: {e}")

    async def ban_user(self, message: discord.Message, config: dict):
        """Banir usuário por spam"""
        try:
            if message.guild.me.guild_permissions.ban_members:
                await message.author.ban(reason="Anti-spam automático", delete_message_days=1)

        except Exception as e:
            print(f"❌ Erro banindo usuário: {e}")

    async def log_spam(self, message: discord.Message, config: dict):
        """Log de spam detectado"""
        try:
            # Buscar canal de logs
            log_channel_id = await database.fetchone(
                "SELECT log_channel_id FROM guild_settings WHERE guild_id = ?",
                (str(message.guild.id),),
            )

            if not log_channel_id or not log_channel_id.get("log_channel_id"):
                return

            log_channel = message.guild.get_channel(int(log_channel_id["log_channel_id"]))
            if not log_channel:
                return

            embed = discord.Embed(
                title="🚫 Anti-Spam Ativado", color=0xFF0000, timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="👤 Usuário",
                value=f"{message.author.mention}\\n`{message.author}`",
                inline=True,
            )

            embed.add_field(name="📍 Canal", value=message.channel.mention, inline=True)

            embed.add_field(name="⚡ Ação", value=config.get("acao", "delete").upper(), inline=True)

            embed.add_field(
                name="📊 Limite",
                value=f"{config['limite']} msgs em {config['intervalo']}s",
                inline=False,
            )

            embed.set_footer(text=f"ID: {message.author.id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro logando spam: {e}")


async def setup(bot):
    """Setup function para carregar o cog"""
    await bot.add_cog(AntispamHandler(bot))
