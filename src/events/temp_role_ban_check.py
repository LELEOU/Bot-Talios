"""
Temp Role Ban Check - Sistema de verificação de bans temporários
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands, tasks

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class TempRoleBanCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_temp_bans.start()

    def cog_unload(self):
        self.check_temp_bans.cancel()

    @tasks.loop(minutes=1)  # Verificar a cada minuto
    async def check_temp_bans(self):
        """Verificar bans temporários expirados"""
        try:
            # Buscar bans expirados
            expired_bans = await database.fetchall(
                "SELECT * FROM temp_bans WHERE expires_at <= ? AND active = 1",
                (discord.utils.utcnow().isoformat(),),
            )

            for ban in expired_bans:
                await self.remove_temp_ban(ban)

            # Buscar mutes expirados
            expired_mutes = await database.fetchall(
                "SELECT * FROM temp_mutes WHERE expires_at <= ? AND active = 1",
                (discord.utils.utcnow().isoformat(),),
            )

            for mute in expired_mutes:
                await self.remove_temp_mute(mute)

            # Buscar roles temporários expirados
            expired_roles = await database.fetchall(
                "SELECT * FROM temp_roles WHERE expires_at <= ? AND active = 1",
                (discord.utils.utcnow().isoformat(),),
            )

            for role_data in expired_roles:
                await self.remove_temp_role(role_data)

        except Exception as e:
            print(f"❌ Erro verificando bans temporários: {e}")

    @check_temp_bans.before_loop
    async def before_check_temp_bans(self):
        """Aguardar bot ficar online"""
        await self.bot.wait_until_ready()

    async def remove_temp_ban(self, ban_data):
        """Remover ban temporário"""
        try:
            guild = self.bot.get_guild(int(ban_data["guild_id"]))
            if not guild:
                return

            user_id = int(ban_data["user_id"])

            # Verificar se usuário ainda está banido
            try:
                ban_entry = await guild.fetch_ban(discord.Object(id=user_id))

                # Desbanir usuário
                await guild.unban(
                    discord.Object(id=user_id),
                    reason=f"Ban temporário expirado - Duração: {ban_data.get('duration', 'N/A')}",
                )

                # Marcar como inativo no banco
                await database.run(
                    "UPDATE temp_bans SET active = 0, removed_at = ? WHERE id = ?",
                    (discord.utils.utcnow().isoformat(), ban_data["id"]),
                )

                # Log do desban
                await self.log_temp_ban_removal(guild, user_id, ban_data)

                print(f"✅ Ban temporário removido: {user_id} em {guild.name}")

            except discord.NotFound:
                # Usuário já foi desbanido manualmente
                await database.run(
                    "UPDATE temp_bans SET active = 0, removed_at = ? WHERE id = ?",
                    (discord.utils.utcnow().isoformat(), ban_data["id"]),
                )

        except Exception as e:
            print(f"❌ Erro removendo ban temporário: {e}")

    async def remove_temp_mute(self, mute_data):
        """Remover mute temporário"""
        try:
            guild = self.bot.get_guild(int(mute_data["guild_id"]))
            if not guild:
                return

            member = guild.get_member(int(mute_data["user_id"]))
            if not member:
                # Usuário saiu do servidor
                await database.run(
                    "UPDATE temp_mutes SET active = 0, removed_at = ? WHERE id = ?",
                    (discord.utils.utcnow().isoformat(), mute_data["id"]),
                )
                return

            # Buscar role de mute
            mute_role = discord.utils.get(guild.roles, name="Muted")
            if not mute_role:
                # Role de mute não existe mais
                await database.run(
                    "UPDATE temp_mutes SET active = 0, removed_at = ? WHERE id = ?",
                    (discord.utils.utcnow().isoformat(), mute_data["id"]),
                )
                return

            # Remover role de mute
            if mute_role in member.roles:
                await member.remove_roles(
                    mute_role,
                    reason=f"Mute temporário expirado - Duração: {mute_data.get('duration', 'N/A')}",
                )

            # Marcar como inativo
            await database.run(
                "UPDATE temp_mutes SET active = 0, removed_at = ? WHERE id = ?",
                (discord.utils.utcnow().isoformat(), mute_data["id"]),
            )

            # Log do unmute
            await self.log_temp_mute_removal(guild, member, mute_data)

            print(f"✅ Mute temporário removido: {member} em {guild.name}")

        except Exception as e:
            print(f"❌ Erro removendo mute temporário: {e}")

    async def remove_temp_role(self, role_data):
        """Remover role temporário"""
        try:
            guild = self.bot.get_guild(int(role_data["guild_id"]))
            if not guild:
                return

            member = guild.get_member(int(role_data["user_id"]))
            if not member:
                # Usuário saiu do servidor
                await database.run(
                    "UPDATE temp_roles SET active = 0, removed_at = ? WHERE id = ?",
                    (discord.utils.utcnow().isoformat(), role_data["id"]),
                )
                return

            role = guild.get_role(int(role_data["role_id"]))
            if not role:
                # Role foi deletado
                await database.run(
                    "UPDATE temp_roles SET active = 0, removed_at = ? WHERE id = ?",
                    (discord.utils.utcnow().isoformat(), role_data["id"]),
                )
                return

            # Remover role
            if role in member.roles:
                await member.remove_roles(
                    role,
                    reason=f"Role temporário expirado - Duração: {role_data.get('duration', 'N/A')}",
                )

            # Marcar como inativo
            await database.run(
                "UPDATE temp_roles SET active = 0, removed_at = ? WHERE id = ?",
                (discord.utils.utcnow().isoformat(), role_data["id"]),
            )

            print(f"✅ Role temporário removido: {role.name} de {member} em {guild.name}")

        except Exception as e:
            print(f"❌ Erro removendo role temporário: {e}")

    async def log_temp_ban_removal(self, guild, user_id, ban_data):
        """Log da remoção de ban temporário"""
        try:
            # Buscar canal de log
            log_channel = await self.get_log_channel(guild.id)
            if not log_channel:
                return

            user = await self.bot.fetch_user(user_id)

            embed = discord.Embed(
                title="🔓 Ban Temporário Expirado", color=0x00FF00, timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="👤 Usuário",
                value=f"**{user}**\\n`{user.id}`" if user else f"`{user_id}`",
                inline=True,
            )

            embed.add_field(
                name="⏱️ Duração Original",
                value=ban_data.get("duration", "Desconhecida"),
                inline=True,
            )

            embed.add_field(
                name="📅 Banido em",
                value=f"<t:{int(discord.utils.parse_time(ban_data['created_at']).timestamp())}:R>",
                inline=True,
            )

            if ban_data.get("reason"):
                embed.add_field(name="📋 Motivo Original", value=ban_data["reason"], inline=False)

            embed.set_footer(text=f"ID: {user_id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro logando remoção de ban: {e}")

    async def log_temp_mute_removal(self, guild, member, mute_data):
        """Log da remoção de mute temporário"""
        try:
            log_channel = await self.get_log_channel(guild.id)
            if not log_channel:
                return

            embed = discord.Embed(
                title="🔊 Mute Temporário Expirado",
                color=0x00FF00,
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(name="👤 Usuário", value=f"{member.mention}\\n`{member}`", inline=True)

            embed.add_field(
                name="⏱️ Duração Original",
                value=mute_data.get("duration", "Desconhecida"),
                inline=True,
            )

            embed.add_field(
                name="📅 Mutado em",
                value=f"<t:{int(discord.utils.parse_time(mute_data['created_at']).timestamp())}:R>",
                inline=True,
            )

            if mute_data.get("reason"):
                embed.add_field(name="📋 Motivo Original", value=mute_data["reason"], inline=False)

            embed.set_footer(text=f"ID: {member.id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro logando remoção de mute: {e}")

    async def get_log_channel(self, guild_id):
        """Buscar canal de log"""
        try:
            result = await database.fetchone(
                "SELECT log_channel_id FROM guild_settings WHERE guild_id = ?", (str(guild_id),)
            )

            if result and result.get("log_channel_id"):
                return self.bot.get_channel(int(result["log_channel_id"]))

            return None

        except Exception as e:
            print(f"❌ Erro buscando canal de log: {e}")
            return None


async def setup(bot):
    await bot.add_cog(TempRoleBanCheck(bot))
