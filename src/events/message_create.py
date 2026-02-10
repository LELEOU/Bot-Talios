"""
Event handler para mensagens - Sistema completo ADAPTADO DO JS
Inclui: Antispam, Leveling, Sticky Messages, Logs
"""

import asyncio
import re
import sys
import time
from pathlib import Path

import discord
from discord.ext import commands

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import database


class MessageCreate(commands.Cog):
    """Event handler para mensagens"""

    def __init__(self, bot):
        self.bot = bot
        # Cache para antispam
        self.spam_cache = {}
        # Cache para sticky messages
        self.sticky_cache = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Processar todas as mensagens"""
        # Ignorar bots
        if message.author.bot:
            return

        # Ignorar DMs
        if not message.guild:
            return

        try:
            # 🛡️ Sistema de Antispam
            await self.handle_antispam(message)

            # 📈 Sistema de Leveling/XP
            await self.handle_leveling(message)

            # 📌 Sticky Messages
            await self.handle_sticky_messages(message)

            # 📝 Message Logging
            await self.handle_message_logging(message)

            # 🔍 Filtros de Conteúdo
            await self.handle_content_filters(message)

        except Exception as e:
            print(f"❌ Erro processando mensagem: {e}")

    async def handle_antispam(self, message: discord.Message):
        """Sistema completo de antispam ADAPTADO DO JS"""
        try:
            # Buscar configurações do servidor
            settings = await database.get_guild_settings(str(message.guild.id))

            if not settings or not settings.get("antispam_enabled", False):
                return

            antispam_config = settings.get(
                "antispam_config",
                {
                    "message_limit": 5,
                    "time_window": 10,  # segundos
                    "action": "warn",  # warn, mute, kick, ban
                    "mute_duration": 300,  # 5 minutos
                },
            )

            user_id = str(message.author.id)
            current_time = time.time()

            # Inicializar cache do usuário
            if user_id not in self.spam_cache:
                self.spam_cache[user_id] = []

            user_messages = self.spam_cache[user_id]

            # Limpar mensagens antigas (IGUAL AO JS)
            time_window = antispam_config["time_window"]
            recent_messages = [
                timestamp for timestamp in user_messages if current_time - timestamp < time_window
            ]

            # Adicionar mensagem atual
            recent_messages.append(current_time)
            self.spam_cache[user_id] = recent_messages

            # Verificar se ultrapassou o limite
            message_limit = antispam_config["message_limit"]
            if len(recent_messages) > message_limit:
                await self.execute_antispam_action(message, antispam_config)

            # Limpeza automática do cache (performance)
            if len(self.spam_cache) > 1000:
                self.cleanup_spam_cache()

        except Exception as e:
            print(f"❌ Erro antispam: {e}")

    async def execute_antispam_action(self, message: discord.Message, config: dict):
        """Executar ação de antispam IGUAL AO JS"""
        try:
            action = config.get("action", "warn")
            user = message.author

            # Verificar se usuário tem permissões administrativas (bypass)
            if user.guild_permissions.administrator:
                return

            if action == "warn":
                embed = discord.Embed(
                    title="⚠️ Antispam - Aviso",
                    description=f"{user.mention}, você está enviando mensagens muito rapidamente!",
                    color=0xFFAA00,
                )
                await message.channel.send(embed=embed, delete_after=10)

            elif action == "mute":
                # Buscar ou criar role de mute
                mute_role = discord.utils.get(message.guild.roles, name="Muted")
                if not mute_role:
                    mute_role = await self.create_mute_role(message.guild)

                await user.add_roles(mute_role, reason="Antispam automático")

                # Remover mute depois do tempo
                duration = config.get("mute_duration", 300)

                embed = discord.Embed(
                    title="🔇 Usuário Mutado - Antispam",
                    description=f"{user.mention} foi mutado por {duration}s por spam",
                    color=0xFF6600,
                )
                await message.channel.send(embed=embed)

                # Programar unmute automático
                async def auto_unmute():
                    await asyncio.sleep(duration)
                    try:
                        await user.remove_roles(mute_role, reason="Fim do mute de antispam")
                    except:
                        pass

                asyncio.create_task(auto_unmute())

            # Registrar caso no sistema de moderação
            await database.add_moderation_case(
                str(message.guild.id),
                str(user.id),
                str(self.bot.user.id),  # Bot como moderador
                action,
                "Antispam automático",
                config.get("mute_duration", 0) if action == "mute" else 0,
            )

        except Exception as e:
            print(f"❌ Erro executando ação antispam: {e}")

    async def create_mute_role(self, guild: discord.Guild):
        """Criar role de mute com permissões corretas"""
        try:
            mute_role = await guild.create_role(
                name="Muted", color=discord.Color.dark_gray(), reason="Role de mute para antispam"
            )

            # Configurar permissões em todos os canais
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(
                        mute_role,
                        send_messages=False,
                        add_reactions=False,
                        send_messages_in_threads=False,
                    )
                elif isinstance(channel, discord.VoiceChannel):
                    await channel.set_permissions(mute_role, speak=False, connect=False)

            return mute_role

        except Exception as e:
            print(f"❌ Erro criando mute role: {e}")
            return None

    async def handle_leveling(self, message: discord.Message):
        """Sistema de XP e Leveling ADAPTADO DO JS"""
        try:
            # Verificar se leveling está habilitado
            settings = await database.get_guild_settings(str(message.guild.id))
            if not settings or not settings.get("leveling_enabled", True):
                return

            user_id = str(message.author.id)
            guild_id = str(message.guild.id)

            # Verificar cooldown de XP (1 minuto - IGUAL AO JS)
            if not hasattr(self.bot, "xp_cooldowns"):
                self.bot.xp_cooldowns = {}

            cooldown_key = f"{guild_id}_{user_id}"
            current_time = time.time()

            if cooldown_key in self.bot.xp_cooldowns:
                if current_time - self.bot.xp_cooldowns[cooldown_key] < 60:
                    return  # Ainda em cooldown

            self.bot.xp_cooldowns[cooldown_key] = current_time

            # Calcular XP baseado no comprimento da mensagem (IGUAL AO JS)
            base_xp = 15
            length_bonus = min(len(message.content) // 10, 10)  # Max 10 bonus
            total_xp = base_xp + length_bonus

            # Buscar dados atuais do usuário
            user_data = await database.get_user_level_data(guild_id, user_id)

            if not user_data:
                # Criar novo usuário
                await database.create_user_level_data(guild_id, user_id, total_xp)
                return

            # Atualizar XP
            new_xp = user_data["xp"] + total_xp
            current_level = user_data["level"]

            # Calcular novo nível (FÓRMULA IGUAL AO JS)
            new_level = self.calculate_level(new_xp)

            # Atualizar no banco
            await database.update_user_level_data(guild_id, user_id, new_xp, new_level)

            # Verificar se subiu de nível
            if new_level > current_level:
                await self.handle_level_up(message, new_level)

        except Exception as e:
            print(f"❌ Erro sistema leveling: {e}")

    def calculate_level(self, xp: int) -> int:
        """Calcular nível baseado no XP - FÓRMULA DO JS"""
        # Fórmula: level = sqrt(xp / 100)
        import math

        return int(math.sqrt(xp / 100))

    async def handle_level_up(self, message: discord.Message, new_level: int):
        """Lidar com subida de nível IGUAL AO JS"""
        try:
            # Verificar se mensagens de level up estão habilitadas
            settings = await database.get_guild_settings(str(message.guild.id))

            if settings and not settings.get("levelup_messages", True):
                return

            embed = discord.Embed(
                title="🎉 Level Up!",
                description=f"Parabéns {message.author.mention}! Você alcançou o **nível {new_level}**!",
                color=0x00FF00,
            )

            embed.set_thumbnail(url=message.author.display_avatar.url)

            # Verificar se há reward de role para este nível
            level_role = await database.get_level_role_reward(str(message.guild.id), new_level)

            if level_role:
                role = message.guild.get_role(int(level_role["role_id"]))
                if role:
                    try:
                        await message.author.add_roles(role, reason=f"Level {new_level} reward")
                        embed.add_field(
                            name="🎁 Recompensa",
                            value=f"Você recebeu o cargo {role.mention}!",
                            inline=False,
                        )
                    except:
                        pass

            await message.channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro level up: {e}")

    async def handle_sticky_messages(self, message: discord.Message):
        """Sistema de Sticky Messages ADAPTADO DO JS"""
        try:
            channel_id = str(message.channel.id)

            # Verificar se canal tem sticky message ativa
            sticky_data = await database.get_sticky_message(channel_id)

            if not sticky_data or not sticky_data.get("is_active"):
                return

            # Atualizar contador de mensagens
            message_count = sticky_data.get("message_count", 0) + 1
            await database.increment_sticky_message_count(channel_id)

            # Verificar se deve reenviar (a cada X mensagens - IGUAL AO JS)
            message_threshold = sticky_data.get("message_threshold", 5)

            if message_count >= message_threshold:
                await self.repost_sticky_message(message.channel, sticky_data)
                await database.reset_sticky_message_count(channel_id)

        except Exception as e:
            print(f"❌ Erro sticky messages: {e}")

    async def repost_sticky_message(self, channel: discord.TextChannel, sticky_data: dict):
        """Reenviar sticky message IGUAL AO JS"""
        try:
            # Deletar mensagem anterior se existir
            if sticky_data.get("current_message_id"):
                try:
                    old_message = await channel.fetch_message(
                        int(sticky_data["current_message_id"])
                    )
                    await old_message.delete()
                except:
                    pass

            # Criar embed da sticky message (FORMATAÇÃO DO JS)
            embed = discord.Embed(
                title="📌 Mensagem Fixada", description=sticky_data["content"], color=0x00AAFF
            )

            if sticky_data.get("image_url"):
                embed.set_image(url=sticky_data["image_url"])

            # Enviar nova mensagem
            new_message = await channel.send(embed=embed)

            # Atualizar ID da mensagem no banco
            await database.update_sticky_message_id(sticky_data["channel_id"], str(new_message.id))

        except Exception as e:
            print(f"❌ Erro reenviando sticky: {e}")

    async def handle_message_logging(self, message: discord.Message):
        """Sistema de logs de mensagens IGUAL AO JS"""
        try:
            # Buscar canal de logs
            settings = await database.get_guild_settings(str(message.guild.id))

            if not settings or not settings.get("message_logs_enabled", False):
                return

            log_channel_id = settings.get("message_logs_channel_id")
            if not log_channel_id:
                return

            log_channel = message.guild.get_channel(int(log_channel_id))
            if not log_channel:
                return

            # Não logar mensagens do próprio canal de logs
            if message.channel.id == log_channel.id:
                return

            embed = discord.Embed(
                title="📝 Nova Mensagem", color=0x00AA00, timestamp=message.created_at
            )

            embed.add_field(name="Canal", value=message.channel.mention, inline=True)
            embed.add_field(name="Autor", value=message.author.mention, inline=True)
            embed.add_field(
                name="Conteúdo", value=message.content[:1000] or "*Sem texto*", inline=False
            )

            embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)

            embed.set_footer(text=f"ID: {message.id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro message logging: {e}")

    async def handle_content_filters(self, message: discord.Message):
        """Filtros de conteúdo ADAPTADO DO JS"""
        try:
            settings = await database.get_guild_settings(str(message.guild.id))

            if not settings:
                return

            content = message.content.lower()

            # Filtro de palavrões (IGUAL AO JS)
            if settings.get("filter_profanity", False):
                profanity_list = settings.get("profanity_words", [])
                for word in profanity_list:
                    if word.lower() in content:
                        await message.delete()

                        embed = discord.Embed(
                            title="🚫 Mensagem Filtrada",
                            description=f"{message.author.mention}, sua mensagem foi removida por conter linguagem inadequada.",
                            color=0xFF6600,
                        )

                        await message.channel.send(embed=embed, delete_after=10)
                        return

            # Filtro de links (IGUAL AO JS)
            if settings.get("filter_links", False):
                link_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

                if re.search(link_pattern, content):
                    # Verificar se usuário tem permissão para postar links
                    if not message.author.guild_permissions.manage_messages:
                        await message.delete()

                        embed = discord.Embed(
                            title="🚫 Link Bloqueado",
                            description=f"{message.author.mention}, você não tem permissão para enviar links.",
                            color=0xFF6600,
                        )

                        await message.channel.send(embed=embed, delete_after=10)
                        return

        except Exception as e:
            print(f"❌ Erro filtros: {e}")

    def cleanup_spam_cache(self):
        """Limpar cache de spam antigo - PERFORMANCE"""
        try:
            current_time = time.time()
            users_to_remove = []

            for user_id, messages in self.spam_cache.items():
                # Remover mensagens antigas
                recent = [msg for msg in messages if current_time - msg < 3600]  # 1 hora

                if recent:
                    self.spam_cache[user_id] = recent
                else:
                    users_to_remove.append(user_id)

            # Remover usuários sem mensagens recentes
            for user_id in users_to_remove:
                del self.spam_cache[user_id]

            print(f"✅ Cache limpo: {len(users_to_remove)} usuários removidos")

        except Exception as e:
            print(f"❌ Erro limpando cache: {e}")


async def setup(bot):
    """Setup function para carregar o cog"""
    await bot.add_cog(MessageCreate(bot))
