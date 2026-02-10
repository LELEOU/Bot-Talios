"""
Sistema de Mute/Timeout Avançado
Controle completo de timeouts com duração e histórico
"""

import os
import re
import sqlite3
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands


class MuteSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.path.join("src", "data", "mutes.db")
        self.init_database()

    def init_database(self):
        """Inicializar banco de dados de mutes"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mute_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                moderator_id TEXT NOT NULL,
                reason TEXT,
                duration_minutes INTEGER,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mute_settings (
                guild_id TEXT PRIMARY KEY,
                max_mute_duration INTEGER DEFAULT 10080,
                default_reason TEXT DEFAULT 'Violação das regras',
                log_channel_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def parse_time_string(self, time_str: str) -> timedelta | None:
        """Converter string de tempo para timedelta"""
        time_str = time_str.lower().strip()

        # Padrões de tempo aceitos
        patterns = {
            r"(\d+)s(?:ec|econds?)?": "seconds",
            r"(\d+)m(?:in|inutes?)?": "minutes",
            r"(\d+)h(?:ours?)?": "hours",
            r"(\d+)d(?:ays?)?": "days",
            r"(\d+)w(?:eeks?)?": "weeks",
        }

        total_seconds = 0

        for pattern, unit in patterns.items():
            match = re.search(pattern, time_str)
            if match:
                value = int(match.group(1))

                if unit == "seconds":
                    total_seconds += value
                elif unit == "minutes":
                    total_seconds += value * 60
                elif unit == "hours":
                    total_seconds += value * 3600
                elif unit == "days":
                    total_seconds += value * 86400
                elif unit == "weeks":
                    total_seconds += value * 604800

        if total_seconds > 0:
            return timedelta(seconds=total_seconds)

        # Fallback: tentar apenas números (assumir minutos)
        try:
            minutes = int(time_str)
            return timedelta(minutes=minutes)
        except ValueError:
            return None

    def format_duration(self, duration: timedelta) -> str:
        """Formatar duração para exibição"""
        total_seconds = int(duration.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds} segundo{'s' if total_seconds != 1 else ''}"

        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes} minuto{'s' if minutes != 1 else ''}"

        hours = minutes // 60
        remaining_minutes = minutes % 60
        if hours < 24:
            if remaining_minutes > 0:
                return f"{hours}h {remaining_minutes}min"
            return f"{hours} hora{'s' if hours != 1 else ''}"

        days = hours // 24
        remaining_hours = hours % 24
        if remaining_hours > 0:
            return f"{days}d {remaining_hours}h"
        return f"{days} dia{'s' if days != 1 else ''}"

    @app_commands.command(name="mute", description="🔇 Aplicar timeout em um usuário")
    @app_commands.describe(
        user="Usuário a ser mutado",
        tempo="Duração do mute (ex: 10m, 1h, 2d)",
        motivo="Motivo do mute",
    )
    @app_commands.default_permissions(moderate_members=True)
    async def mute_add(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        tempo: str,
        motivo: str | None = "Violação das regras",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\nVocê não tem permissão para mutar membros.",
                    ephemeral=True,
                )
                return

            # Verificações de segurança
            if user.id == interaction.user.id:
                await interaction.response.send_message(
                    "❌ **Ação Inválida**\nVocê não pode mutar a si mesmo.", ephemeral=True
                )
                return

            if user.id == interaction.client.user.id:
                await interaction.response.send_message(
                    "❌ **Ação Inválida**\nNão posso mutar a mim mesmo.", ephemeral=True
                )
                return

            # Verificar hierarquia
            if user.top_role >= interaction.user.top_role:
                await interaction.response.send_message(
                    "❌ **Hierarquia Insuficiente**\n"
                    "Você não pode mutar alguém com cargo igual ou superior ao seu.",
                    ephemeral=True,
                )
                return

            if user.top_role >= interaction.guild.me.top_role:
                await interaction.response.send_message(
                    "❌ **Hierarquia Insuficiente**\n"
                    "Não posso mutar alguém com cargo igual ou superior ao meu.",
                    ephemeral=True,
                )
                return

            # Converter tempo
            duration = self.parse_time_string(tempo)
            if not duration:
                await interaction.response.send_message(
                    "❌ **Formato de Tempo Inválido**\n"
                    "Use formatos como: `10m`, `1h`, `2d`, `1w`\n"
                    "Ou apenas números para minutos: `30`",
                    ephemeral=True,
                )
                return

            # Verificar limite máximo (28 dias Discord limit)
            max_duration = timedelta(days=28)
            if duration > max_duration:
                await interaction.response.send_message(
                    "❌ **Duração Muito Longa**\n"
                    f"Duração máxima permitida: 28 dias\n"
                    f"Duração solicitada: {self.format_duration(duration)}",
                    ephemeral=True,
                )
                return

            # Verificar se já está mutado
            if user.is_timed_out():
                await interaction.response.send_message(
                    f"❌ **Usuário Já Mutado**\n"
                    f"{user.mention} já possui um timeout ativo.\n"
                    f"Expira: <t:{int(user.timed_out_until.timestamp())}:R>",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # Aplicar timeout
            expires_at = datetime.now() + duration
            await user.timeout(expires_at, reason=f"Mute por {interaction.user}: {motivo}")

            # Salvar no banco de dados
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO mute_history 
                (guild_id, user_id, moderator_id, reason, duration_minutes, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    str(interaction.guild.id),
                    str(user.id),
                    str(interaction.user.id),
                    motivo,
                    int(duration.total_seconds() // 60),
                    expires_at,
                ),
            )

            conn.commit()
            conn.close()

            # Criar embed de confirmação
            embed = discord.Embed(
                title="🔇 **USUÁRIO MUTADO**", color=0xFF6600, timestamp=datetime.now()
            )

            embed.add_field(name="👤 Usuário", value=f"{user.mention}\n`{user.id}`", inline=True)

            embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            embed.add_field(
                name="⏰ Duração", value=f"**{self.format_duration(duration)}**", inline=True
            )

            embed.add_field(
                name="📝 Motivo",
                value=motivo[:200] + ("..." if len(motivo) > 200 else ""),
                inline=False,
            )

            embed.add_field(
                name="⏳ Expira em",
                value=f"<t:{int(expires_at.timestamp())}:R>\n<t:{int(expires_at.timestamp())}:F>",
                inline=False,
            )

            embed.set_thumbnail(url=user.display_avatar.url)

            embed.set_footer(
                text=f"ID do Mute: {cursor.lastrowid if 'cursor' in locals() else 'N/A'}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=embed)

            # Tentar enviar DM para o usuário
            try:
                dm_embed = discord.Embed(
                    title="🔇 **VOCÊ FOI MUTADO**",
                    description=f"Você recebeu um timeout no servidor **{interaction.guild.name}**",
                    color=0xFF6600,
                    timestamp=datetime.now(),
                )

                dm_embed.add_field(
                    name="⏰ Duração", value=self.format_duration(duration), inline=True
                )

                dm_embed.add_field(name="📝 Motivo", value=motivo, inline=True)

                dm_embed.add_field(
                    name="⏳ Expira em", value=f"<t:{int(expires_at.timestamp())}:R>", inline=False
                )

                dm_embed.set_footer(text=f"Servidor: {interaction.guild.name}")

                await user.send(embed=dm_embed)
            except:
                pass  # Usuário pode ter DMs desabilitadas

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ **Erro de Permissão**\nNão tenho permissão para aplicar timeout neste usuário.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Erro no comando mute: {e}")
            try:
                await interaction.followup.send("❌ Erro ao aplicar mute.", ephemeral=True)
            except:
                pass

    @app_commands.command(name="unmute", description="🔊 Remover timeout de um usuário")
    @app_commands.describe(
        user="Usuário para remover o timeout", motivo="Motivo da remoção do mute"
    )
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        motivo: str | None = "Timeout removido por moderador",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\nVocê não tem permissão para gerenciar timeouts.",
                    ephemeral=True,
                )
                return

            # Verificar se está mutado
            if not user.is_timed_out():
                await interaction.response.send_message(
                    f"❌ **Usuário Não Mutado**\n{user.mention} não possui timeout ativo.",
                    ephemeral=True,
                )
                return

            # Remover timeout
            await user.timeout(None, reason=f"Unmute por {interaction.user}: {motivo}")

            # Atualizar banco de dados
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE mute_history 
                SET is_active = 0 
                WHERE guild_id = ? AND user_id = ? AND is_active = 1
            """,
                (str(interaction.guild.id), str(user.id)),
            )

            conn.commit()
            conn.close()

            # Criar embed de confirmação
            embed = discord.Embed(
                title="🔊 **TIMEOUT REMOVIDO**", color=0x00FF00, timestamp=datetime.now()
            )

            embed.add_field(name="👤 Usuário", value=f"{user.mention}\n`{user.id}`", inline=True)

            embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            embed.add_field(
                name="📝 Motivo",
                value=motivo[:200] + ("..." if len(motivo) > 200 else ""),
                inline=False,
            )

            embed.set_thumbnail(url=user.display_avatar.url)

            embed.set_footer(
                text="Timeout removido com sucesso", icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

            # Tentar enviar DM
            try:
                dm_embed = discord.Embed(
                    title="🔊 **SEU TIMEOUT FOI REMOVIDO**",
                    description=f"Seu timeout no servidor **{interaction.guild.name}** foi removido!",
                    color=0x00FF00,
                    timestamp=datetime.now(),
                )

                dm_embed.add_field(name="📝 Motivo", value=motivo, inline=False)

                dm_embed.set_footer(text=f"Servidor: {interaction.guild.name}")

                await user.send(embed=dm_embed)
            except:
                pass

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ **Erro de Permissão**\nNão tenho permissão para remover timeout deste usuário.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Erro no comando unmute: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao remover timeout.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(
        name="mute-history", description="📋 Ver histórico de mutes de um usuário"
    )
    @app_commands.describe(user="Usuário para ver o histórico")
    @app_commands.default_permissions(moderate_members=True)
    async def mute_history(self, interaction: discord.Interaction, user: discord.Member):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT moderator_id, reason, duration_minutes, applied_at, expires_at, is_active
                FROM mute_history 
                WHERE guild_id = ? AND user_id = ?
                ORDER BY applied_at DESC
                LIMIT 10
            """,
                (str(interaction.guild.id), str(user.id)),
            )

            results = cursor.fetchall()
            conn.close()

            embed = discord.Embed(
                title="📋 **HISTÓRICO DE MUTES**", color=0x6C5CE7, timestamp=datetime.now()
            )

            embed.add_field(name="👤 Usuário", value=f"{user.mention}\n`{user.id}`", inline=True)

            if not results:
                embed.add_field(name="📊 Registros", value="Nenhum mute registrado", inline=True)
            else:
                embed.add_field(
                    name="📊 Total de Mutes",
                    value=f"**{len(results)}** registro{'s' if len(results) != 1 else ''}",
                    inline=True,
                )

                history_text = ""
                for i, (mod_id, reason, duration, applied_at, expires_at, is_active) in enumerate(
                    results[:5]
                ):
                    moderator = self.bot.get_user(int(mod_id))
                    mod_name = moderator.display_name if moderator else f"ID: {mod_id}"

                    status = "🔴 Ativo" if is_active else "✅ Expirado"
                    duration_text = f"{duration}min" if duration else "N/A"

                    applied_timestamp = int(datetime.fromisoformat(applied_at).timestamp())

                    history_text += f"**{i + 1}.** {status}\n"
                    history_text += f"   **Moderador:** {mod_name}\n"
                    history_text += f"   **Duração:** {duration_text}\n"
                    history_text += f"   **Aplicado:** <t:{applied_timestamp}:R>\n"
                    history_text += (
                        f"   **Motivo:** {reason[:50]}{'...' if len(reason) > 50 else ''}\n\n"
                    )

                embed.add_field(
                    name="🕒 Histórico Recente",
                    value=history_text[:1000] + ("..." if len(history_text) > 1000 else ""),
                    inline=False,
                )

            embed.set_thumbnail(url=user.display_avatar.url)

            embed.set_footer(
                text=f"Solicitado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando mute-history: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao buscar histórico.", ephemeral=True
                )
            except:
                pass


async def setup(bot):
    await bot.add_cog(MuteSystem(bot))
