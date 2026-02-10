"""
Comandos de Moderação Avançados v2.0
Com sistema de permissões personalizado e logs detalhados
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View

sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.permission_system import require_permission


class ReasonModal(Modal, title="Motivo da Ação"):
    """Modal para solicitar motivo de moderação"""

    reason = TextInput(
        label="Motivo",
        placeholder="Digite o motivo desta ação de moderação...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True,
    )

    def __init__(self, action_callback):
        super().__init__()
        self.action_callback = action_callback

    async def on_submit(self, interaction: discord.Interaction):
        await self.action_callback(interaction, self.reason.value)


class ConfirmView(View):
    """View de confirmação para ações de moderação"""

    def __init__(self, user: discord.User, action: str, callback):
        super().__init__(timeout=60)
        self.user = user
        self.action = action
        self.callback = callback
        self.value = None

    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ReasonModal(self.callback))
        self.value = True
        self.stop()

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content=f"❌ {self.action} cancelado!", view=None, embed=None
        )
        self.value = False
        self.stop()


class ModerationCommandsAdvanced(commands.Cog):
    """Comandos de moderação com permissões customizadas"""

    def __init__(self, bot):
        self.bot = bot
        self.mod_log_channel = {}  # Cache de canais de log

    async def log_moderation(
        self,
        guild: discord.Guild,
        moderator: discord.Member,
        action: str,
        target: discord.Member,
        reason: str,
        duration: str | None = None,
    ):
        """Registrar ação de moderação em canal de logs"""
        # TODO: Implementar busca por canal de logs configurado
        log_channel_id = self.mod_log_channel.get(guild.id)

        if log_channel_id:
            channel = guild.get_channel(log_channel_id)
            if channel:
                embed = discord.Embed(
                    title=f"🛡️ {action}", color=0xE74C3C, timestamp=datetime.utcnow()
                )

                embed.add_field(name="👤 Alvo", value=target.mention, inline=True)
                embed.add_field(name="👮 Moderador", value=moderator.mention, inline=True)

                if duration:
                    embed.add_field(name="⏱️ Duração", value=duration, inline=True)

                embed.add_field(name="📝 Motivo", value=reason, inline=False)
                embed.set_thumbnail(url=target.display_avatar.url)
                embed.set_footer(
                    text=f"ID do Usuário: {target.id}", icon_url=moderator.display_avatar.url
                )

                await channel.send(embed=embed)

    @app_commands.command(name="ban", description="🔨 Banir membro do servidor")
    @app_commands.describe(
        membro="Membro a ser banido",
        deletar_mensagens="Deletar mensagens dos últimos dias (0-7)",
        notificar="Enviar DM ao usuário com o motivo",
    )
    @require_permission(category="moderation", mod=True)
    async def ban_advanced(
        self,
        interaction: discord.Interaction,
        membro: discord.Member,
        deletar_mensagens: Literal[0, 1, 2, 3, 7] | None = 0,
        notificar: bool = True,
    ):
        """Banir membro com sistema de confirmação"""

        # Verificações de segurança
        if membro.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ Você não pode banir a si mesmo!", ephemeral=True
            )
            return

        if membro.id == interaction.guild.owner_id:
            await interaction.response.send_message(
                "❌ Você não pode banir o dono do servidor!", ephemeral=True
            )
            return

        if membro.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ Você não pode banir alguém com cargo igual ou superior ao seu!", ephemeral=True
            )
            return

        if membro.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "❌ Não posso banir alguém com cargo igual ou superior ao meu!", ephemeral=True
            )
            return

        # Embed de confirmação
        embed = discord.Embed(
            title="⚠️ Confirmar Banimento",
            description=(
                f"Você está prestes a **banir** {membro.mention}\n\n"
                f"**👤 Usuário:** {membro} (`{membro.id}`)\n"
                f"**📅 Conta Criada:** <t:{int(membro.created_at.timestamp())}:R>\n"
                f"**📥 Entrou no Servidor:** <t:{int(membro.joined_at.timestamp())}:R>\n"
                f"**🎭 Maior Cargo:** {membro.top_role.mention}\n\n"
                f"**⚙️ Configurações:**\n"
                f"🗑️ Deletar mensagens: **{deletar_mensagens} dia(s)**\n"
                f"💬 Notificar usuário: **{'Sim' if notificar else 'Não'}**"
            ),
            color=0xE74C3C,
        )
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.set_footer(text="Clique em Confirmar e forneça um motivo")

        # Callback para executar ban
        async def execute_ban(modal_interaction: discord.Interaction, reason: str):
            try:
                # Tentar notificar o usuário
                if notificar:
                    try:
                        dm_embed = discord.Embed(
                            title=f"🔨 Você foi banido de {interaction.guild.name}",
                            description=f"**Motivo:** {reason}",
                            color=0xE74C3C,
                            timestamp=datetime.utcnow(),
                        )
                        dm_embed.set_footer(
                            text="Entre em contato com a administração se achar que foi um erro"
                        )
                        await membro.send(embed=dm_embed)
                    except:
                        pass  # Usuário pode ter DMs desabilitadas

                # Executar ban
                await membro.ban(
                    reason=f"{reason} | Moderador: {interaction.user}",
                    delete_message_days=deletar_mensagens,
                )

                # Responder sucesso
                success_embed = discord.Embed(
                    title="✅ Banimento Executado",
                    description=(
                        f"**👤 Usuário:** {membro} (`{membro.id}`)\n"
                        f"**📝 Motivo:** {reason}\n"
                        f"**👮 Moderador:** {interaction.user.mention}\n"
                        f"**⏰ Data:** <t:{int(datetime.utcnow().timestamp())}:F>"
                    ),
                    color=0x2ECC71,
                )

                await modal_interaction.response.edit_message(
                    content=None, embed=success_embed, view=None
                )

                # Log
                await self.log_moderation(
                    interaction.guild, interaction.user, "BAN", membro, reason
                )

            except discord.Forbidden:
                await modal_interaction.response.edit_message(
                    content="❌ Não tenho permissão para banir este usuário!", embed=None, view=None
                )
            except Exception as e:
                await modal_interaction.response.edit_message(
                    content=f"❌ Erro ao banir: {e!s}", embed=None, view=None
                )

        view = ConfirmView(membro, "Banimento", execute_ban)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="kick", description="👢 Expulsar membro do servidor")
    @app_commands.describe(
        membro="Membro a ser expulso", notificar="Enviar DM ao usuário com o motivo"
    )
    @require_permission(category="moderation", mod=True)
    async def kick_advanced(
        self, interaction: discord.Interaction, membro: discord.Member, notificar: bool = True
    ):
        """Expulsar membro com sistema de confirmação"""

        # Verificações de segurança (mesmas do ban)
        if membro.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ Você não pode expulsar a si mesmo!", ephemeral=True
            )
            return

        if membro.id == interaction.guild.owner_id:
            await interaction.response.send_message(
                "❌ Você não pode expulsar o dono do servidor!", ephemeral=True
            )
            return

        if membro.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ Você não pode expulsar alguém com cargo igual ou superior ao seu!",
                ephemeral=True,
            )
            return

        if membro.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "❌ Não posso expulsar alguém com cargo igual ou superior ao meu!", ephemeral=True
            )
            return

        # Embed de confirmação
        embed = discord.Embed(
            title="⚠️ Confirmar Expulsão",
            description=(
                f"Você está prestes a **expulsar** {membro.mention}\n\n"
                f"**👤 Usuário:** {membro} (`{membro.id}`)\n"
                f"**📅 Conta Criada:** <t:{int(membro.created_at.timestamp())}:R>\n"
                f"**📥 Entrou no Servidor:** <t:{int(membro.joined_at.timestamp())}:R>\n"
                f"**🎭 Maior Cargo:** {membro.top_role.mention}\n\n"
                f"**⚙️ Configurações:**\n"
                f"💬 Notificar usuário: **{'Sim' if notificar else 'Não'}**"
            ),
            color=0xFF9800,
        )
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.set_footer(text="Clique em Confirmar e forneça um motivo")

        # Callback
        async def execute_kick(modal_interaction: discord.Interaction, reason: str):
            try:
                # Notificar
                if notificar:
                    try:
                        dm_embed = discord.Embed(
                            title=f"👢 Você foi expulso de {interaction.guild.name}",
                            description=f"**Motivo:** {reason}",
                            color=0xFF9800,
                            timestamp=datetime.utcnow(),
                        )
                        await membro.send(embed=dm_embed)
                    except:
                        pass

                # Expulsar
                await membro.kick(reason=f"{reason} | Moderador: {interaction.user}")

                # Sucesso
                success_embed = discord.Embed(
                    title="✅ Expulsão Executada",
                    description=(
                        f"**👤 Usuário:** {membro} (`{membro.id}`)\n"
                        f"**📝 Motivo:** {reason}\n"
                        f"**👮 Moderador:** {interaction.user.mention}\n"
                        f"**⏰ Data:** <t:{int(datetime.utcnow().timestamp())}:F>"
                    ),
                    color=0x2ECC71,
                )

                await modal_interaction.response.edit_message(
                    content=None, embed=success_embed, view=None
                )

                # Log
                await self.log_moderation(
                    interaction.guild, interaction.user, "KICK", membro, reason
                )

            except discord.Forbidden:
                await modal_interaction.response.edit_message(
                    content="❌ Não tenho permissão para expulsar este usuário!",
                    embed=None,
                    view=None,
                )
            except Exception as e:
                await modal_interaction.response.edit_message(
                    content=f"❌ Erro ao expulsar: {e!s}", embed=None, view=None
                )

        view = ConfirmView(membro, "Expulsão", execute_kick)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="timeout", description="⏱️ Castigar membro temporariamente")
    @app_commands.describe(
        membro="Membro a ser castigado",
        duração="Duração do castigo",
        tempo="Minutos, horas ou dias",
        notificar="Enviar DM ao usuário",
    )
    @require_permission(category="moderation", mod=True)
    async def timeout_advanced(
        self,
        interaction: discord.Interaction,
        membro: discord.Member,
        duração: app_commands.Range[int, 1, 28],
        tempo: Literal["minutos", "horas", "dias"] = "minutos",
        notificar: bool = True,
    ):
        """Aplicar timeout com duração personalizada"""

        # Verificações
        if membro.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ Você não pode castigar a si mesmo!", ephemeral=True
            )
            return

        if membro.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ Você não pode castigar alguém com cargo igual ou superior ao seu!",
                ephemeral=True,
            )
            return

        # Calcular duração
        if tempo == "minutos":
            delta = timedelta(minutes=duração)
            tempo_texto = f"{duração} minuto(s)"
        elif tempo == "horas":
            delta = timedelta(hours=duração)
            tempo_texto = f"{duração} hora(s)"
        else:  # dias
            delta = timedelta(days=duração)
            tempo_texto = f"{duração} dia(s)"

        # Embed de confirmação
        until_timestamp = int((datetime.utcnow() + delta).timestamp())
        embed = discord.Embed(
            title="⚠️ Confirmar Timeout",
            description=(
                f"Você está prestes a **castigar** {membro.mention}\n\n"
                f"**👤 Usuário:** {membro} (`{membro.id}`)\n"
                f"**⏱️ Duração:** {tempo_texto}\n"
                f"**⏰ Termina:** <t:{until_timestamp}:F> (<t:{until_timestamp}:R>)\n"
                f"**💬 Notificar:** **{'Sim' if notificar else 'Não'}**"
            ),
            color=0xF39C12,
        )
        embed.set_thumbnail(url=membro.display_avatar.url)

        # Callback
        async def execute_timeout(modal_interaction: discord.Interaction, reason: str):
            try:
                # Notificar
                if notificar:
                    try:
                        dm_embed = discord.Embed(
                            title=f"⏱️ Você recebeu timeout em {interaction.guild.name}",
                            description=(
                                f"**Duração:** {tempo_texto}\n"
                                f"**Motivo:** {reason}\n"
                                f"**Termina:** <t:{until_timestamp}:R>"
                            ),
                            color=0xF39C12,
                        )
                        await membro.send(embed=dm_embed)
                    except:
                        pass

                # Aplicar timeout
                await membro.timeout(delta, reason=f"{reason} | Moderador: {interaction.user}")

                # Sucesso
                success_embed = discord.Embed(
                    title="✅ Timeout Aplicado",
                    description=(
                        f"**👤 Usuário:** {membro.mention}\n"
                        f"**⏱️ Duração:** {tempo_texto}\n"
                        f"**📝 Motivo:** {reason}\n"
                        f"**⏰ Termina:** <t:{until_timestamp}:R>"
                    ),
                    color=0x2ECC71,
                )

                await modal_interaction.response.edit_message(embed=success_embed, view=None)

                # Log
                await self.log_moderation(
                    interaction.guild, interaction.user, "TIMEOUT", membro, reason, tempo_texto
                )

            except Exception as e:
                await modal_interaction.response.edit_message(
                    content=f"❌ Erro: {e!s}", embed=None, view=None
                )

        view = ConfirmView(membro, "Timeout", execute_timeout)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModerationCommandsAdvanced(bot))
