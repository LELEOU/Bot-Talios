"""
Handler de Moderação - Sistema completo
Gerencia bans temporários, warns, mutes, cases
"""

import sys
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import tasks

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import database


class ModerationHandler:
    """Handler completo para sistema de moderação"""

    def __init__(self, bot):
        self.bot = bot
        # Iniciar task de verificação de bans temporários
        self.check_temp_bans.start()
        self.check_temp_mutes.start()

    @tasks.loop(minutes=1)
    async def check_temp_bans(self):
        """Verificar e remover bans temporários expirados"""
        try:
            # Buscar bans temporários expirados
            expired_bans = await database.get_expired_temp_bans()

            for ban_data in expired_bans:
                try:
                    guild = self.bot.get_guild(int(ban_data["guild_id"]))
                    if not guild:
                        continue

                    user_id = int(ban_data["user_id"])

                    # Remover ban
                    try:
                        await guild.unban(
                            discord.Object(id=user_id), reason="Ban temporário expirado"
                        )

                        # Atualizar status no banco
                        await database.mark_temp_ban_as_expired(
                            ban_data["guild_id"], ban_data["user_id"]
                        )

                        print(f"✅ Ban temporário removido: {user_id} no servidor {guild.name}")

                        # Log do unban
                        log_channel = await self.get_log_channel(guild)
                        if log_channel:
                            embed = discord.Embed(
                                title="🔓 Ban Temporário Expirado",
                                description=f"**Usuário:** <@{user_id}>\\n"
                                f"**Razão:** Ban temporário expirado",
                                color=0x00FF00,
                                timestamp=datetime.now(),
                            )
                            await log_channel.send(embed=embed)

                    except discord.NotFound:
                        # Usuário não estava banido
                        await database.mark_temp_ban_as_expired(
                            ban_data["guild_id"], ban_data["user_id"]
                        )

                except Exception as e:
                    print(f"❌ Erro removendo ban temporário: {e}")

        except Exception as e:
            print(f"❌ Erro verificando bans temporários: {e}")

    @tasks.loop(minutes=1)
    async def check_temp_mutes(self):
        """Verificar e remover mutes temporários expirados"""
        try:
            # Buscar mutes temporários expirados
            expired_mutes = await database.get_expired_temp_mutes()

            for mute_data in expired_mutes:
                try:
                    guild = self.bot.get_guild(int(mute_data["guild_id"]))
                    if not guild:
                        continue

                    member = guild.get_member(int(mute_data["user_id"]))
                    if not member:
                        # Marcar como expirado mesmo se membro não estiver no servidor
                        await database.mark_temp_mute_as_expired(
                            mute_data["guild_id"], mute_data["user_id"]
                        )
                        continue

                    # Buscar role de mute
                    mute_role = discord.utils.get(guild.roles, name="Muted")
                    if mute_role and mute_role in member.roles:
                        await member.remove_roles(mute_role, reason="Mute temporário expirado")

                    # Atualizar status no banco
                    await database.mark_temp_mute_as_expired(
                        mute_data["guild_id"], mute_data["user_id"]
                    )

                    print(f"✅ Mute temporário removido: {member} no servidor {guild.name}")

                    # Log do unmute
                    log_channel = await self.get_log_channel(guild)
                    if log_channel:
                        embed = discord.Embed(
                            title="🔊 Mute Temporário Expirado",
                            description=f"**Usuário:** {member.mention}\\n"
                            f"**Razão:** Mute temporário expirado",
                            color=0x00FF00,
                            timestamp=datetime.now(),
                        )
                        await log_channel.send(embed=embed)

                except Exception as e:
                    print(f"❌ Erro removendo mute temporário: {e}")

        except Exception as e:
            print(f"❌ Erro verificando mutes temporários: {e}")

    @check_temp_bans.before_loop
    async def before_check_temp_bans(self):
        """Aguardar bot ficar pronto antes de iniciar verificação"""
        await self.bot.wait_until_ready()

    @check_temp_mutes.before_loop
    async def before_check_temp_mutes(self):
        """Aguardar bot ficar pronto antes de iniciar verificação"""
        await self.bot.wait_until_ready()

    async def get_log_channel(self, guild: discord.Guild):
        """Buscar canal de logs do servidor"""
        try:
            settings = await database.get_guild_settings(str(guild.id))

            if settings and settings.get("moderation_logs_channel_id"):
                channel_id = int(settings["moderation_logs_channel_id"])
                return guild.get_channel(channel_id)

            return None

        except Exception as e:
            print(f"❌ Erro buscando canal de logs: {e}")
            return None

    async def create_moderation_case(
        self,
        guild_id: str,
        user_id: str,
        moderator_id: str,
        action: str,
        reason: str,
        duration: int = 0,
        evidence_url: str = None,
    ):
        """Criar novo case de moderação"""
        try:
            case_id = await database.add_moderation_case(
                guild_id, user_id, moderator_id, action, reason, duration, evidence_url
            )

            return case_id

        except Exception as e:
            print(f"❌ Erro criando case de moderação: {e}")
            return None

    async def log_moderation_action(self, guild: discord.Guild, case_data: dict):
        """Logar ação de moderação no canal de logs"""
        try:
            log_channel = await self.get_log_channel(guild)
            if not log_channel:
                return

            action = case_data["action"]
            user_id = case_data["user_id"]
            moderator_id = case_data["moderator_id"]
            reason = case_data["reason"]
            case_id = case_data.get("case_id", "N/A")

            # Emoji baseado na ação
            action_emojis = {
                "warn": "⚠️",
                "mute": "🔇",
                "kick": "👢",
                "ban": "🔨",
                "temp_ban": "⏱️",
                "temp_mute": "🔇",
                "unban": "🔓",
                "unmute": "🔊",
            }

            emoji = action_emojis.get(action, "🔨")

            embed = discord.Embed(
                title=f"{emoji} Ação de Moderação - Case #{case_id}",
                color=self.get_action_color(action),
                timestamp=datetime.now(),
            )

            embed.add_field(name="Usuário", value=f"<@{user_id}>", inline=True)
            embed.add_field(name="Moderador", value=f"<@{moderator_id}>", inline=True)
            embed.add_field(name="Ação", value=action.replace("_", " ").title(), inline=True)
            embed.add_field(name="Razão", value=reason, inline=False)

            # Adicionar duração se aplicável
            if case_data.get("duration", 0) > 0:
                duration = case_data["duration"]
                embed.add_field(name="Duração", value=f"{duration} segundos", inline=True)

            # Adicionar evidência se houver
            if case_data.get("evidence_url"):
                embed.add_field(name="Evidência", value=case_data["evidence_url"], inline=False)

            embed.set_footer(text=f"ID do usuário: {user_id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro logando ação de moderação: {e}")

    def get_action_color(self, action: str) -> int:
        """Retornar cor baseada na ação"""
        colors = {
            "warn": 0xFFAA00,  # Laranja
            "mute": 0xFF6600,  # Vermelho-laranja
            "temp_mute": 0xFF6600,  # Vermelho-laranja
            "kick": 0xFF3300,  # Vermelho
            "ban": 0xFF0000,  # Vermelho escuro
            "temp_ban": 0xFF0000,  # Vermelho escuro
            "unban": 0x00FF00,  # Verde
            "unmute": 0x00FF00,  # Verde
        }
        return colors.get(action, 0x666666)

    async def get_user_warnings(self, guild_id: str, user_id: str):
        """Buscar warnings de um usuário"""
        try:
            warnings = await database.get_user_warnings(guild_id, user_id)
            return warnings

        except Exception as e:
            print(f"❌ Erro buscando warnings: {e}")
            return []

    async def get_moderation_cases(self, guild_id: str, user_id: str = None, limit: int = 10):
        """Buscar cases de moderação"""
        try:
            cases = await database.get_moderation_cases(guild_id, user_id, limit)
            return cases

        except Exception as e:
            print(f"❌ Erro buscando cases: {e}")
            return []

    async def create_mute_role(self, guild: discord.Guild):
        """Criar role de mute se não existir"""
        try:
            mute_role = discord.utils.get(guild.roles, name="Muted")

            if mute_role:
                return mute_role

            # Criar nova role
            mute_role = await guild.create_role(
                name="Muted", color=discord.Color.dark_gray(), reason="Role de mute para moderação"
            )

            # Configurar permissões em todos os canais
            for channel in guild.channels:
                try:
                    if isinstance(channel, discord.TextChannel):
                        await channel.set_permissions(
                            mute_role,
                            send_messages=False,
                            add_reactions=False,
                            send_messages_in_threads=False,
                            create_public_threads=False,
                            create_private_threads=False,
                        )
                    elif isinstance(channel, discord.VoiceChannel):
                        await channel.set_permissions(mute_role, speak=False, stream=False)
                except:
                    continue

            return mute_role

        except Exception as e:
            print(f"❌ Erro criando mute role: {e}")
            return None

    async def apply_automatic_action(
        self, guild: discord.Guild, user: discord.Member, warning_count: int
    ):
        """Aplicar ação automática baseada no número de warnings"""
        try:
            settings = await database.get_guild_settings(str(guild.id))

            if not settings:
                return None

            auto_mod_config = settings.get("auto_moderation", {})

            # Configurações padrão
            actions = auto_mod_config.get(
                "actions",
                {
                    3: "mute",  # 3 warns = mute 1 hora
                    5: "temp_ban",  # 5 warns = ban 1 dia
                    7: "ban",  # 7 warns = ban permanente
                },
            )

            if warning_count in actions:
                action = actions[warning_count]

                if action == "mute":
                    mute_role = await self.create_mute_role(guild)
                    if mute_role:
                        await user.add_roles(
                            mute_role, reason=f"Auto-moderação: {warning_count} warnings"
                        )

                        # Programar unmute em 1 hora
                        await database.add_temp_mute(
                            str(guild.id),
                            str(user.id),
                            3600,  # 1 hora
                        )

                elif action == "temp_ban":
                    await user.ban(
                        reason=f"Auto-moderação: {warning_count} warnings", delete_message_days=1
                    )

                    # Programar unban em 1 dia
                    await database.add_temp_ban(
                        str(guild.id),
                        str(user.id),
                        86400,  # 1 dia
                    )

                elif action == "ban":
                    await user.ban(
                        reason=f"Auto-moderação: {warning_count} warnings", delete_message_days=1
                    )

                # Criar case
                case_id = await self.create_moderation_case(
                    str(guild.id),
                    str(user.id),
                    str(self.bot.user.id),
                    action,
                    f"Auto-moderação: {warning_count} warnings",
                )

                return action, case_id

            return None, None

        except Exception as e:
            print(f"❌ Erro aplicando ação automática: {e}")
            return None, None
