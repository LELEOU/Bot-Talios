"""
Comando Kick - Moderation
Expulsa usuários do servidor com sistema de confirmação
"""

import sqlite3

import discord
from discord import app_commands
from discord.ext import commands


class KickCommand(commands.Cog):
    """Comando de expulsão de membros"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_db_connection(self):
        """Obter conexão com o banco de dados"""
        conn = sqlite3.connect("data/bot.db")
        conn.row_factory = sqlite3.Row
        return conn

    def create_mod_case(
        self, guild_id: int, user_id: int, moderator_id: int, case_type: str, reason: str
    ):
        """Criar um caso de moderação"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Criar tabela se não existir
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

    @app_commands.command(name="kick", description="Expulsa um usuário do servidor")
    @app_commands.describe(user="Usuário para expulsar", motivo="Motivo da expulsão")
    @app_commands.default_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        motivo: str = "Não especificado",
    ):
        """Expulsar um membro"""

        # Verificar permissões do usuário
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message(
                "❌ Você não tem permissão para expulsar membros.", ephemeral=True
            )
            return

        # Verificações de segurança
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ Você não pode expulsar a si mesmo.", ephemeral=True
            )
            return

        if user.id == self.bot.user.id:
            await interaction.response.send_message(
                "❌ Não posso expulsar a mim mesmo.", ephemeral=True
            )
            return

        # Verificar se o usuário ainda está no servidor
        if user not in interaction.guild.members:
            await interaction.response.send_message(
                "❌ Usuário não encontrado no servidor.", ephemeral=True
            )
            return

        # Verificar hierarquia de cargos
        if user.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ Você não pode expulsar alguém com cargo igual ou superior ao seu.",
                ephemeral=True,
            )
            return

        if user.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "❌ Não posso expulsar alguém com cargo igual ou superior ao meu.", ephemeral=True
            )
            return

        # Verificar se o usuário pode ser expulso
        if not user.guild_permissions.kick_members:
            pass  # Pode expulsar
        else:
            # Usuário tem permissões de moderação - confirmar novamente
            pass

        # Criar embed de confirmação
        confirm_embed = discord.Embed(
            title="⚠️ Confirmação de Expulsão",
            description=f"Tem certeza que deseja expulsar {user.mention}?",
            color=0xFF9900,
            timestamp=discord.utils.utcnow(),
        )

        confirm_embed.add_field(name="👤 Usuário", value=f"{user} ({user.id})", inline=True)

        confirm_embed.add_field(name="👮 Moderador", value=interaction.user.mention, inline=True)

        confirm_embed.add_field(name="📝 Motivo", value=motivo, inline=False)

        confirm_embed.set_thumbnail(url=user.display_avatar.url)

        # Criar view com botões
        view = discord.ui.View(timeout=30)

        confirm_button = discord.ui.Button(
            label="Confirmar Kick", style=discord.ButtonStyle.danger, emoji="👢"
        )

        cancel_button = discord.ui.Button(
            label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌"
        )

        async def confirm_callback(button_interaction):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message(
                    "❌ Apenas quem executou o comando pode confirmar.", ephemeral=True
                )
                return

            await button_interaction.response.defer()

            try:
                # Tentar enviar DM antes de expulsar
                try:
                    dm_embed = discord.Embed(
                        title="👢 Você foi expulso",
                        description=f"Você foi expulso do servidor **{interaction.guild.name}**",
                        color=0xFF9900,
                        timestamp=discord.utils.utcnow(),
                    )

                    dm_embed.add_field(name="📝 Motivo", value=motivo, inline=False)
                    dm_embed.add_field(
                        name="👮 Moderador", value=str(interaction.user), inline=False
                    )
                    dm_embed.set_thumbnail(
                        url=interaction.guild.icon.url if interaction.guild.icon else None
                    )

                    await user.send(embed=dm_embed)
                    dm_sent = True
                except:
                    dm_sent = False

                # Expulsar o usuário
                await user.kick(reason=f"{motivo} - Por: {interaction.user}")

                # Criar caso de moderação
                case_id = self.create_mod_case(
                    interaction.guild.id, user.id, interaction.user.id, "kick", motivo
                )

                # Embed de sucesso
                success_embed = discord.Embed(
                    title="✅ Usuário Expulso",
                    description=f"{user.mention} foi expulso com sucesso.",
                    color=0x00FF00,
                    timestamp=discord.utils.utcnow(),
                )

                success_embed.add_field(name="📋 Caso", value=f"#{case_id}", inline=True)

                success_embed.add_field(name="📝 Motivo", value=motivo, inline=False)

                success_embed.add_field(
                    name="📨 DM Enviada",
                    value="✅ Sim" if dm_sent else "❌ Não (DMs bloqueadas)",
                    inline=True,
                )

                await button_interaction.followup.edit_message(
                    interaction.id, embed=success_embed, view=None
                )

                # Log em canal de moderação
                log_channels = ["mod-logs", "logs", "moderation", "moderacao"]
                log_channel = None

                for channel_name in log_channels:
                    log_channel = discord.utils.get(interaction.guild.channels, name=channel_name)
                    if log_channel:
                        break

                if log_channel and isinstance(log_channel, discord.TextChannel):
                    log_embed = discord.Embed(
                        title="👢 Usuário Expulso", color=0xFF9900, timestamp=discord.utils.utcnow()
                    )

                    log_embed.add_field(name="👤 Usuário", value=f"{user} ({user.id})", inline=True)

                    log_embed.add_field(
                        name="👮 Moderador", value=str(interaction.user), inline=True
                    )

                    log_embed.add_field(name="📋 Caso", value=f"#{case_id}", inline=True)

                    log_embed.add_field(name="📝 Motivo", value=motivo, inline=False)

                    log_embed.set_thumbnail(url=user.display_avatar.url)

                    await log_channel.send(embed=log_embed)

            except discord.Forbidden:
                await button_interaction.followup.edit_message(
                    interaction.id,
                    content="❌ Não tenho permissão para expulsar este usuário.",
                    embed=None,
                    view=None,
                )
            except Exception as e:
                await button_interaction.followup.edit_message(
                    interaction.id,
                    content=f"❌ Erro ao expulsar o usuário: `{e!s}`",
                    embed=None,
                    view=None,
                )

        async def cancel_callback(button_interaction):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message(
                    "❌ Apenas quem executou o comando pode cancelar.", ephemeral=True
                )
                return

            cancel_embed = discord.Embed(
                title="❌ Expulsão Cancelada",
                description="A expulsão foi cancelada pelo moderador.",
                color=0x808080,
            )

            await button_interaction.response.edit_message(embed=cancel_embed, view=None)

        # Adicionar callbacks aos botões
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback

        view.add_item(confirm_button)
        view.add_item(cancel_button)

        # Responder com o embed de confirmação
        await interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(KickCommand(bot))
