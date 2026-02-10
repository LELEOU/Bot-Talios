"""
Comando Warn - Moderation
Sistema completo de avisos com ações automáticas
"""

import sqlite3
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands


class WarnCommand(commands.Cog):
    """Sistema de avisos para moderação"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_db_connection(self):
        """Obter conexão com o banco de dados"""
        conn = sqlite3.connect("data/bot.db")
        conn.row_factory = sqlite3.Row
        return conn

    def setup_database(self):
        """Configurar tabelas do banco de dados"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Tabela de avisos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de casos de moderação
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mod_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                case_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                type TEXT,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de configurações de ações automáticas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auto_warn_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                warn_count INTEGER,
                action_type TEXT,
                duration INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def create_mod_case(
        self, guild_id: int, user_id: int, moderator_id: int, case_type: str, reason: str
    ):
        """Criar um caso de moderação"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Obter próximo case_id
        cursor.execute("SELECT MAX(case_id) FROM mod_cases WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        next_case_id = (result[0] + 1) if result[0] else 1

        # Inserir caso
        cursor.execute(
            """
            INSERT INTO mod_cases (guild_id, case_id, user_id, moderator_id, type, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (guild_id, next_case_id, user_id, moderator_id, case_type, reason),
        )

        conn.commit()
        case_id = next_case_id
        conn.close()
        return case_id

    def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str):
        """Adicionar um aviso"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO warnings (guild_id, user_id, moderator_id, reason)
            VALUES (?, ?, ?, ?)
        """,
            (guild_id, user_id, moderator_id, reason),
        )

        conn.commit()
        conn.close()

    def get_warning_count(self, guild_id: int, user_id: int):
        """Obter contagem de avisos de um usuário"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?
        """,
            (guild_id, user_id),
        )

        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_auto_action(self, guild_id: int, warn_count: int):
        """Buscar ação automática baseada no número de avisos"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT action_type, duration FROM auto_warn_actions 
            WHERE guild_id = ? AND warn_count = ?
        """,
            (guild_id, warn_count),
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            return {"action": result[0], "duration": result[1]}

        # Ações padrão se não configuradas
        default_actions = {
            3: {"action": "timeout", "duration": 3600},  # 1 hora
            5: {"action": "kick", "duration": 0},
            7: {"action": "ban", "duration": 0},
        }

        return default_actions.get(warn_count)

    async def execute_auto_action(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        action_data: dict,
        warn_count: int,
    ):
        """Executar ação automática baseada nos avisos"""
        action = action_data["action"]
        duration = action_data["duration"]

        try:
            reason = f"Ação automática: {warn_count} avisos"

            if action == "timeout":
                await member.timeout(
                    discord.utils.utcnow() + timedelta(seconds=duration), reason=reason
                )
                action_text = f"Timeout por {duration // 3600}h"

            elif action == "kick":
                await member.kick(reason=reason)
                action_text = "Expulsão"

            elif action == "ban":
                await member.ban(reason=reason)
                action_text = "Banimento"

            # Notificar sobre ação automática
            auto_embed = discord.Embed(
                title="🤖 Ação Automática Executada",
                description="Ação automática executada devido ao número de avisos.",
                color=0xFF0000,
                timestamp=discord.utils.utcnow(),
            )

            auto_embed.add_field(name="👤 Usuário", value=str(member), inline=True)
            auto_embed.add_field(name="⚠️ Avisos", value=str(warn_count), inline=True)
            auto_embed.add_field(name="⚡ Ação", value=action_text, inline=True)

            await interaction.followup.send(embed=auto_embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao executar ação automática: `{e!s}`", ephemeral=True
            )

    @app_commands.command(name="warn", description="Avisa um usuário")
    @app_commands.describe(user="Usuário para avisar", motivo="Motivo do aviso")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        motivo: str = "Não especificado",
    ):
        """Aplicar aviso a um membro"""

        # Configurar banco se necessário
        self.setup_database()

        # Verificar permissões
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                "❌ Você não tem permissão para avisar membros.", ephemeral=True
            )
            return

        # Verificações de segurança
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ Você não pode avisar a si mesmo.", ephemeral=True
            )
            return

        if user.id == self.bot.user.id:
            await interaction.response.send_message(
                "❌ Não posso avisar a mim mesmo.", ephemeral=True
            )
            return

        # Verificar hierarquia
        if user.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ Você não pode avisar alguém com cargo igual ou superior ao seu.", ephemeral=True
            )
            return

        await interaction.response.defer()

        try:
            # Adicionar aviso ao banco
            self.add_warning(interaction.guild.id, user.id, interaction.user.id, motivo)

            # Criar caso de moderação
            case_id = self.create_mod_case(
                interaction.guild.id, user.id, interaction.user.id, "warning", motivo
            )

            # Contar avisos totais
            warn_count = self.get_warning_count(interaction.guild.id, user.id)

            # Tentar enviar DM
            dm_sent = False
            try:
                dm_embed = discord.Embed(
                    title="⚠️ Você recebeu um aviso",
                    description=f"Você recebeu um aviso no servidor **{interaction.guild.name}**",
                    color=0xFFFF00,
                    timestamp=discord.utils.utcnow(),
                )

                dm_embed.add_field(name="📝 Motivo", value=motivo, inline=False)
                dm_embed.add_field(name="👮 Moderador", value=str(interaction.user), inline=True)
                dm_embed.add_field(name="⚠️ Total de Avisos", value=str(warn_count), inline=True)

                if interaction.guild.icon:
                    dm_embed.set_thumbnail(url=interaction.guild.icon.url)

                await user.send(embed=dm_embed)
                dm_sent = True

            except:
                pass  # DMs bloqueadas

            # Embed de sucesso
            success_embed = discord.Embed(
                title="✅ Aviso Aplicado",
                description=f"Aviso aplicado com sucesso para {user.mention}.",
                color=0xFFFF00,
                timestamp=discord.utils.utcnow(),
            )

            success_embed.add_field(name="👤 Usuário", value=f"{user} ({user.id})", inline=True)
            success_embed.add_field(name="👮 Moderador", value=str(interaction.user), inline=True)
            success_embed.add_field(name="📋 Caso", value=f"#{case_id}", inline=True)
            success_embed.add_field(name="⚠️ Total de Avisos", value=str(warn_count), inline=True)
            success_embed.add_field(
                name="📨 DM Enviada", value="✅ Sim" if dm_sent else "❌ Não", inline=True
            )
            success_embed.add_field(name="📝 Motivo", value=motivo, inline=False)

            success_embed.set_thumbnail(url=user.display_avatar.url)

            await interaction.followup.send(embed=success_embed)

            # Log no canal de moderação
            log_channels = ["mod-logs", "logs", "moderation", "moderacao"]
            log_channel = None

            for channel_name in log_channels:
                log_channel = discord.utils.get(interaction.guild.channels, name=channel_name)
                if log_channel:
                    break

            if log_channel and isinstance(log_channel, discord.TextChannel):
                log_embed = discord.Embed(
                    title="⚠️ Aviso Aplicado", color=0xFFFF00, timestamp=discord.utils.utcnow()
                )

                log_embed.add_field(name="👤 Usuário", value=f"{user} ({user.id})", inline=True)
                log_embed.add_field(name="👮 Moderador", value=str(interaction.user), inline=True)
                log_embed.add_field(name="📋 Caso", value=f"#{case_id}", inline=True)
                log_embed.add_field(name="⚠️ Total de Avisos", value=str(warn_count), inline=True)
                log_embed.add_field(name="📝 Motivo", value=motivo, inline=False)

                log_embed.set_thumbnail(url=user.display_avatar.url)

                await log_channel.send(embed=log_embed)

            # Verificar ação automática
            auto_action = self.get_auto_action(interaction.guild.id, warn_count)
            if auto_action:
                await self.execute_auto_action(interaction, user, auto_action, warn_count)

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao aplicar aviso: `{e!s}`", ephemeral=True)

    @app_commands.command(name="warnings", description="Ver avisos de um usuário")
    @app_commands.describe(user="Usuário para ver avisos")
    async def warnings(self, interaction: discord.Interaction, user: discord.Member = None):
        """Ver avisos de um usuário"""

        if user is None:
            user = interaction.user

        # Verificar se pode ver avisos de outros
        if user != interaction.user and not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                "❌ Você só pode ver seus próprios avisos.", ephemeral=True
            )
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT reason, moderator_id, created_at 
            FROM warnings 
            WHERE guild_id = ? AND user_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        """,
            (interaction.guild.id, user.id),
        )

        warnings = cursor.fetchall()
        warn_count = len(warnings)
        conn.close()

        embed = discord.Embed(
            title=f"⚠️ Avisos de {user.display_name}",
            color=0xFFFF00,
            timestamp=discord.utils.utcnow(),
        )

        if warn_count == 0:
            embed.description = "✅ Nenhum aviso encontrado!"
        else:
            embed.description = f"**Total de avisos:** {warn_count}"

            for i, warning in enumerate(warnings[:5], 1):  # Mostrar só os 5 mais recentes
                moderator = interaction.guild.get_member(warning[1])
                mod_name = moderator.display_name if moderator else "Moderador desconhecido"

                date_str = datetime.fromisoformat(warning[2]).strftime("%d/%m/%Y %H:%M")

                embed.add_field(
                    name=f"📋 Aviso #{i}",
                    value=f"**Motivo:** {warning[0]}\n**Moderador:** {mod_name}\n**Data:** {date_str}",
                    inline=False,
                )

        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"Solicitado por {interaction.user}")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(WarnCommand(bot))
