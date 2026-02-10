"""
Moderation Handler - Sistema principal de moderação
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class ModerationHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """Registrar ban de membro"""
        await self.log_moderation_action("ban", guild, user, None, "Manual")

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        """Registrar unban de membro"""
        await self.log_moderation_action("unban", guild, user, None, "Manual")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Verificar se foi kick ou saída voluntária"""
        try:
            # Aguardar um pouco para ver se é ban
            await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=2))

            # Verificar se foi banido
            try:
                await member.guild.fetch_ban(member)
                return  # Foi banido, já tratado em on_member_ban
            except discord.NotFound:
                # Não foi banido, verificar se foi kick
                await self.check_if_kicked(member)

        except Exception as e:
            print(f"❌ Erro verificando remoção de membro: {e}")

    async def check_if_kicked(self, member):
        """Verificar se membro foi kickado"""
        try:
            # Verificar logs de auditoria
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id:
                    # Foi kickado
                    await self.log_moderation_action(
                        "kick", member.guild, member, entry.user, entry.reason or "Sem motivo"
                    )
                    break

        except Exception as e:
            print(f"❌ Erro verificando kick: {e}")

    async def log_moderation_action(
        self,
        action: str,
        guild: discord.Guild,
        target: discord.User,
        moderator: discord.User = None,
        reason: str = None,
    ):
        """Registrar ação de moderação"""
        try:
            # Salvar no banco de dados
            await database.run(
                """INSERT INTO moderation_logs 
                   (guild_id, action, target_id, moderator_id, reason, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    str(guild.id),
                    action,
                    str(target.id),
                    str(moderator.id) if moderator else None,
                    reason,
                    discord.utils.utcnow().isoformat(),
                ),
            )

            # Enviar log para canal se configurado
            await self.send_moderation_log(guild, action, target, moderator, reason)

        except Exception as e:
            print(f"❌ Erro registrando ação de moderação: {e}")

    async def send_moderation_log(
        self,
        guild: discord.Guild,
        action: str,
        target: discord.User,
        moderator: discord.User = None,
        reason: str = None,
    ):
        """Enviar log de moderação para canal"""
        try:
            # Buscar canal de log
            log_channel = await self.get_moderation_log_channel(guild.id)
            if not log_channel:
                return

            # Cores por ação
            colors = {
                "ban": 0xFF0000,
                "unban": 0x00FF00,
                "kick": 0xFF6600,
                "mute": 0xFFFF00,
                "unmute": 0x00FFFF,
                "warn": 0xFF9900,
                "timeout": 0x9900FF,
            }

            # Emojis por ação
            emojis = {
                "ban": "🔨",
                "unban": "🔓",
                "kick": "👢",
                "mute": "🔇",
                "unmute": "🔊",
                "warn": "⚠️",
                "timeout": "⏱️",
            }

            embed = discord.Embed(
                title=f"{emojis.get(action, '🔧')} {action.title()}",
                color=colors.get(action, 0x666666),
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(
                name="👤 Usuário",
                value=f"{target.mention}\\n`{target}` (`{target.id}`)",
                inline=False,
            )

            if moderator:
                embed.add_field(
                    name="👮 Moderador", value=f"{moderator.mention}\\n`{moderator}`", inline=True
                )
            else:
                embed.add_field(name="👮 Moderador", value="Sistema/Desconhecido", inline=True)

            if reason:
                embed.add_field(name="📋 Motivo", value=reason, inline=False)

            embed.set_thumbnail(url=target.display_avatar.url)
            embed.set_footer(text=f"ID do usuário: {target.id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro enviando log de moderação: {e}")

    async def get_moderation_log_channel(self, guild_id: int):
        """Buscar canal de log de moderação"""
        try:
            result = await database.fetchone(
                "SELECT moderation_log_channel_id FROM guild_settings WHERE guild_id = ?",
                (str(guild_id),),
            )

            if result and result.get("moderation_log_channel_id"):
                return self.bot.get_channel(int(result["moderation_log_channel_id"]))

            # Fallback para canal de log geral
            result = await database.fetchone(
                "SELECT log_channel_id FROM guild_settings WHERE guild_id = ?", (str(guild_id),)
            )

            if result and result.get("log_channel_id"):
                return self.bot.get_channel(int(result["log_channel_id"]))

            return None

        except Exception as e:
            print(f"❌ Erro buscando canal de log: {e}")
            return None

    async def add_moderation_case(
        self,
        guild_id: int,
        action: str,
        target_id: int,
        moderator_id: int,
        reason: str = None,
        duration: str = None,
    ) -> int:
        """Adicionar caso de moderação"""
        try:
            # Gerar próximo número do caso
            last_case = await database.fetchone(
                "SELECT MAX(case_number) as max_case FROM moderation_cases WHERE guild_id = ?",
                (str(guild_id),),
            )

            case_number = (last_case["max_case"] or 0) + 1 if last_case else 1

            # Inserir caso
            await database.run(
                """INSERT INTO moderation_cases 
                   (guild_id, case_number, action, target_id, moderator_id, reason, duration, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(guild_id),
                    case_number,
                    action,
                    str(target_id),
                    str(moderator_id),
                    reason,
                    duration,
                    discord.utils.utcnow().isoformat(),
                ),
            )

            return case_number

        except Exception as e:
            print(f"❌ Erro adicionando caso de moderação: {e}")
            return 0

    async def get_user_moderation_history(
        self, guild_id: int, user_id: int, limit: int = 10
    ) -> list:
        """Buscar histórico de moderação do usuário"""
        try:
            result = await database.fetchall(
                """SELECT * FROM moderation_cases 
                   WHERE guild_id = ? AND target_id = ? 
                   ORDER BY created_at DESC LIMIT ?""",
                (str(guild_id), str(user_id), limit),
            )

            return [dict(row) for row in result] if result else []

        except Exception as e:
            print(f"❌ Erro buscando histórico de moderação: {e}")
            return []

    async def count_user_warnings(self, guild_id: int, user_id: int, days: int = 30) -> int:
        """Contar avisos do usuário nos últimos X dias"""
        try:
            from datetime import datetime, timedelta

            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

            result = await database.fetchone(
                """SELECT COUNT(*) as count FROM moderation_cases 
                   WHERE guild_id = ? AND target_id = ? AND action = 'warn' AND created_at >= ?""",
                (str(guild_id), str(user_id), cutoff_date),
            )

            return result["count"] if result else 0

        except Exception as e:
            print(f"❌ Erro contando avisos: {e}")
            return 0

    async def apply_auto_moderation(self, guild_id: int, user_id: int, infraction_type: str):
        """Aplicar moderação automática baseada em infrações"""
        try:
            # Buscar configuração de auto-moderação
            config = await database.fetchone(
                "SELECT * FROM auto_moderation_config WHERE guild_id = ?", (str(guild_id),)
            )

            if not config or not config.get("enabled"):
                return

            # Contar infrações recentes
            warning_count = await self.count_user_warnings(guild_id, user_id, 30)

            guild = self.bot.get_guild(guild_id)
            if not guild:
                return

            member = guild.get_member(user_id)
            if not member:
                return

            # Aplicar ação baseada na quantidade de avisos
            if warning_count >= config.get("ban_threshold", 5):
                # Ban automático
                await member.ban(reason=f"Auto-moderação: {warning_count} avisos")
                await self.add_moderation_case(
                    guild_id,
                    "ban",
                    user_id,
                    self.bot.user.id,
                    f"Auto-moderação: {warning_count} avisos",
                )

            elif warning_count >= config.get("kick_threshold", 3):
                # Kick automático
                await member.kick(reason=f"Auto-moderação: {warning_count} avisos")
                await self.add_moderation_case(
                    guild_id,
                    "kick",
                    user_id,
                    self.bot.user.id,
                    f"Auto-moderação: {warning_count} avisos",
                )

            elif warning_count >= config.get("mute_threshold", 2):
                # Mute automático
                mute_role = discord.utils.get(guild.roles, name="Muted")
                if mute_role:
                    await member.add_roles(
                        mute_role, reason=f"Auto-moderação: {warning_count} avisos"
                    )
                    await self.add_moderation_case(
                        guild_id,
                        "mute",
                        user_id,
                        self.bot.user.id,
                        f"Auto-moderação: {warning_count} avisos",
                        "1 hora",
                    )

        except Exception as e:
            print(f"❌ Erro aplicando auto-moderação: {e}")


async def setup(bot):
    await bot.add_cog(ModerationHandler(bot))
