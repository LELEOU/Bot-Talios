"""
Restarts Handler - Gerencia reinicializações do bot
"""

import os
import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class RestartsHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Executado quando bot reinicia"""
        try:
            # Verificar se foi um restart
            await self.check_restart_message()

            # Limpar dados temporários
            await self.cleanup_temp_data()

            # Restaurar estados persistentes
            await self.restore_persistent_states()

        except Exception as e:
            print(f"❌ Erro no restart handler: {e}")

    async def check_restart_message(self):
        """Verificar e enviar mensagem de restart"""
        try:
            # Buscar mensagem de restart pendente
            restart_data = await database.fetchone(
                "SELECT * FROM restart_messages ORDER BY created_at DESC LIMIT 1"
            )

            if not restart_data:
                return

            # Verificar se ainda não foi enviada
            if restart_data.get("sent", 0):
                return

            guild = self.bot.get_guild(int(restart_data["guild_id"]))
            if not guild:
                return

            channel = guild.get_channel(int(restart_data["channel_id"]))
            if not channel:
                return

            # Calcular tempo de restart
            import datetime

            restart_time = datetime.datetime.fromisoformat(restart_data["created_at"])
            current_time = datetime.datetime.utcnow()
            restart_duration = (current_time - restart_time).total_seconds()

            embed = discord.Embed(
                title="🔄 Bot Reiniciado",
                description="✅ O bot foi reiniciado com sucesso!",
                color=0x00FF00,
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(
                name="⏱️ Tempo de Restart", value=f"**{restart_duration:.2f}s**", inline=True
            )

            embed.add_field(
                name="🔧 Versão", value=f"`{os.environ.get('BOT_VERSION', '1.0.0')}`", inline=True
            )

            await channel.send(embed=embed)

            # Marcar como enviada
            await database.run(
                "UPDATE restart_messages SET sent = 1 WHERE id = ?", (restart_data["id"],)
            )

        except Exception as e:
            print(f"❌ Erro verificando mensagem de restart: {e}")

    async def cleanup_temp_data(self):
        """Limpar dados temporários"""
        try:
            # Limpar sessões de comando expiradas
            await database.run(
                "DELETE FROM command_sessions WHERE expires_at < ?",
                (discord.utils.utcnow().isoformat(),),
            )

            # Limpar locks temporários
            await database.run("DELETE FROM temp_locks")

            # Limpar cache de cooldowns
            await database.run(
                "DELETE FROM user_cooldowns WHERE expires_at < ?",
                (discord.utils.utcnow().isoformat(),),
            )

            print("🧹 Dados temporários limpos após restart")

        except Exception as e:
            print(f"❌ Erro limpando dados temporários: {e}")

    async def restore_persistent_states(self):
        """Restaurar estados persistentes"""
        try:
            # Restaurar status rotativo se configurado
            await self.restore_rotating_status()

            # Restaurar timers ativos
            await self.restore_active_timers()

            # Restaurar auto-moderação
            await self.restore_auto_moderation()

        except Exception as e:
            print(f"❌ Erro restaurando estados: {e}")

    async def restore_rotating_status(self):
        """Restaurar status rotativo"""
        try:
            # Buscar configuração de status
            status_config = await database.fetchone(
                "SELECT * FROM bot_status_config WHERE enabled = 1"
            )

            if status_config:
                # Implementar restauração do status rotativo
                # (Será implementado no handler específico)
                pass

        except Exception as e:
            print(f"❌ Erro restaurando status rotativo: {e}")

    async def restore_active_timers(self):
        """Restaurar timers ativos"""
        try:
            # Buscar timers que ainda devem estar ativos
            active_timers = await database.fetchall(
                "SELECT * FROM active_timers WHERE expires_at > ?",
                (discord.utils.utcnow().isoformat(),),
            )

            for timer in active_timers:
                # Reagendar timer
                await self.reschedule_timer(timer)

        except Exception as e:
            print(f"❌ Erro restaurando timers: {e}")

    async def restore_auto_moderation(self):
        """Restaurar sistemas de auto-moderação"""
        try:
            # Limpar estados de spam temporários
            # (será resetado naturalmente)

            # Verificar mutes temporários expirados
            expired_mutes = await database.fetchall(
                "SELECT * FROM temp_mutes WHERE expires_at < ?",
                (discord.utils.utcnow().isoformat(),),
            )

            for mute in expired_mutes:
                await self.remove_expired_mute(mute)

        except Exception as e:
            print(f"❌ Erro restaurando auto-moderação: {e}")

    async def reschedule_timer(self, timer_data):
        """Reagendar um timer após restart"""
        try:
            # Implementar reagendamento baseado no tipo de timer
            timer_type = timer_data.get("type")

            if timer_type == "reminder":
                # Reagendar reminder
                pass
            elif timer_type == "temp_mute":
                # Reagendar unmute
                pass
            elif timer_type == "temp_ban":
                # Reagendar unban
                pass

        except Exception as e:
            print(f"❌ Erro reagendando timer: {e}")

    async def remove_expired_mute(self, mute_data):
        """Remover mute expirado"""
        try:
            guild = self.bot.get_guild(int(mute_data["guild_id"]))
            if not guild:
                return

            member = guild.get_member(int(mute_data["user_id"]))
            if not member:
                return

            # Buscar role de mute
            mute_role = discord.utils.get(guild.roles, name="Muted")
            if mute_role and mute_role in member.roles:
                await member.remove_roles(mute_role, reason="Mute temporário expirado")

            # Remover do banco
            await database.run("DELETE FROM temp_mutes WHERE id = ?", (mute_data["id"],))

        except Exception as e:
            print(f"❌ Erro removendo mute expirado: {e}")

    async def schedule_restart_message(self, guild_id: int, channel_id: int):
        """Agendar mensagem de restart"""
        try:
            await database.run(
                "INSERT INTO restart_messages (guild_id, channel_id, created_at, sent) VALUES (?, ?, ?, ?)",
                (str(guild_id), str(channel_id), discord.utils.utcnow().isoformat(), 0),
            )

        except Exception as e:
            print(f"❌ Erro agendando mensagem de restart: {e}")


async def setup(bot):
    await bot.add_cog(RestartsHandler(bot))
