"""
Sistema de Sugestões - Gerenciar Sugestões (Admin)
Comando para administradores aprovarem/rejeitarem sugestões
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class SuggestionManageView(discord.ui.View):
    """Interface para gerenciar sugestões (admin only)"""

    def __init__(self, suggestion_data: dict[str, Any]) -> None:
        super().__init__(timeout=300)
        self.suggestion_data: dict[str, Any] = suggestion_data

    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.success, emoji="✅")
    async def approve_suggestion(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.handle_decision(interaction, "approved", "✅", 0x00FF00)

    @discord.ui.button(label="❌ Rejeitar", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject_suggestion(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.handle_decision(interaction, "rejected", "❌", 0xFF0000)

    @discord.ui.button(label="⏸️ Pausar", style=discord.ButtonStyle.secondary, emoji="⏸️")
    async def pause_suggestion(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.handle_decision(interaction, "paused", "⏸️", 0xFFFF00)

    async def handle_decision(
        self, interaction: discord.Interaction, status: str, emoji: str, color: int
    ) -> None:
        """Processa decisão admin sobre sugestão"""
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(
                    "❌ Apenas administradores podem gerenciar sugestões!", ephemeral=True
                )
                return

            # Modal para motivo
            modal: ReasonModal = ReasonModal(self.suggestion_data, status, emoji, color)
            await interaction.response.send_modal(modal)

        except Exception as e:
            print(f"❌ Erro ao processar decisão: {e}")


class ReasonModal(discord.ui.Modal):
    """Modal para inserir motivo da decisão"""

    def __init__(self, suggestion_data: dict[str, Any], status: str, emoji: str, color: int) -> None:
        super().__init__(title=f"{emoji} {status.title()} Sugestão")
        self.suggestion_data: dict[str, Any] = suggestion_data
        self.status: str = status
        self.emoji: str = emoji
        self.color: int = color

        self.reason: discord.ui.TextInput = discord.ui.TextInput(
            label="Motivo da decisão (opcional)",
            placeholder="Explique o motivo da aprovação/rejeição...",
            required=False,
            max_length=500,
            style=discord.TextStyle.long,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer()

            # Buscar mensagem original da sugestão
            try:
                channel: discord.TextChannel | None = interaction.guild.get_channel(int(self.suggestion_data["channel_id"]))
                message: discord.Message = await channel.fetch_message(int(self.suggestion_data["message_id"]))
            except:
                await interaction.followup.send(
                    "❌ Mensagem da sugestão não encontrada!", ephemeral=True
                )
                return

            # Atualizar banco de dados
            try:
                from ...utils.database import database

                await database.execute(
                    "UPDATE suggestions SET status = ?, decided_by = ?, decided_at = ?, decision_reason = ? WHERE id = ?",
                    (
                        self.status,
                        str(interaction.user.id),
                        datetime.now().isoformat(),
                        self.reason.value or None,
                        self.suggestion_data["id"],
                    ),
                )
            except Exception as e:
                print(f"❌ Erro ao atualizar banco: {e}")

            # Atualizar embed da sugestão
            if message.embeds:
                embed: discord.Embed = message.embeds[0]

                # Atualizar cor e status
                embed.color = self.color

                # Atualizar field de status
                for i, field in enumerate(embed.fields):
                    if "Status" in field.name:
                        status_text: dict[str, str] = {
                            "approved": f"{self.emoji} **Aprovada** - Implementação em andamento",
                            "rejected": f"{self.emoji} **Rejeitada** - Não será implementada",
                            "paused": f"{self.emoji} **Pausada** - Em análise",
                        }

                        embed.set_field_at(
                            i, name="📅 Status", value=status_text[self.status], inline=True
                        )
                        break

                # Adicionar field com decisão
                embed.add_field(
                    name="⚖️ Decisão Admin",
                    value=f"**Por:** {interaction.user.mention}\n"
                    f"**Em:** <t:{int(datetime.now().timestamp())}:F>\n"
                    + (
                        f"**Motivo:** {self.reason.value}"
                        if self.reason.value
                        else "**Motivo:** Não especificado"
                    ),
                    inline=False,
                )

                # Remover botões de votação
                await message.edit(embed=embed, view=None)

            # Notificar autor da sugestão
            try:
                author: discord.Member | None = interaction.guild.get_member(int(self.suggestion_data["user_id"]))
                if author:
                    dm_embed: discord.Embed = discord.Embed(
                        title=f"{self.emoji} Sugestão {self.status.title()}!",
                        description=f"**Sua sugestão:** {self.suggestion_data['title']}",
                        color=self.color,
                        timestamp=datetime.now(),
                    )

                    dm_embed.add_field(
                        name="📍 Servidor", value=interaction.guild.name, inline=True
                    )

                    dm_embed.add_field(
                        name="⚖️ Decidido por", value=str(interaction.user), inline=True
                    )

                    if self.reason.value:
                        dm_embed.add_field(name="📝 Motivo", value=self.reason.value, inline=False)

                    dm_embed.add_field(
                        name="🔗 Link", value=f"[Ver sugestão]({message.jump_url})", inline=False
                    )

                    await author.send(embed=dm_embed)
            except:
                pass

            # Confirmação para admin
            success_embed: discord.Embed = discord.Embed(
                title=f"✅ Sugestão {self.status.title()}!",
                description=f"A sugestão `{self.suggestion_data['id']}` foi {self.status}.",
                color=self.color,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="💡 Sugestão", value=self.suggestion_data["title"], inline=True
            )

            success_embed.add_field(
                name="👤 Autor", value=f"<@{self.suggestion_data['user_id']}>", inline=True
            )

            if self.reason.value:
                success_embed.add_field(name="📝 Motivo", value=self.reason.value, inline=False)

            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro ao processar decisão: {e}")
            await interaction.followup.send(
                "❌ Erro ao processar decisão. Tente novamente.", ephemeral=True
            )


class SuggestionManage(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(
        name="suggestion-manage", description="⚖️ Gerenciar sugestões (aprovar/rejeitar)"
    )
    @app_commands.describe(
        suggestion_id="ID da sugestão para gerenciar",
        acao="Ação a ser tomada",
        motivo="Motivo da decisão",
    )
    async def suggestion_manage(
        self,
        interaction: discord.Interaction,
        suggestion_id: str,
        acao: Literal["aprovar", "rejeitar", "pausar"] | None = None,
        motivo: str | None = None,
    ) -> None:
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para gerenciar sugestões. **Necessário**: Gerenciar Servidor",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar sugestão no banco
            try:
                from ...utils.database import database

                suggestion: dict[str, Any] | None = await database.get(
                    "SELECT * FROM suggestions WHERE id = ? AND guild_id = ?",
                    (suggestion_id, str(interaction.guild.id)),
                )

                if not suggestion:
                    await interaction.followup.send(
                        f"❌ Sugestão `{suggestion_id}` não encontrada!\n"
                        f"Verifique se o ID está correto e se a sugestão existe neste servidor.",
                        ephemeral=True,
                    )
                    return

            except Exception as e:
                print(f"❌ Erro ao buscar sugestão: {e}")
                await interaction.followup.send(
                    "❌ Erro ao buscar sugestão no banco de dados.", ephemeral=True
                )
                return

            # Se ação foi especificada, processar diretamente
            if acao:
                status_map: dict[str, tuple[str, str, int]] = {
                    "aprovar": ("approved", "✅", 0x00FF00),
                    "rejeitar": ("rejected", "❌", 0xFF0000),
                    "pausar": ("paused", "⏸️", 0xFFFF00),
                }

                status: str
                emoji: str
                color: int
                status, emoji, color = status_map[acao]

                # Buscar mensagem original
                try:
                    channel: discord.TextChannel | None = interaction.guild.get_channel(int(suggestion["channel_id"]))
                    message: discord.Message = await channel.fetch_message(int(suggestion["message_id"]))
                except:
                    await interaction.followup.send(
                        "❌ Mensagem da sugestão não encontrada!", ephemeral=True
                    )
                    return

                # Atualizar banco
                await database.execute(
                    "UPDATE suggestions SET status = ?, decided_by = ?, decided_at = ?, decision_reason = ? WHERE id = ?",
                    (
                        status,
                        str(interaction.user.id),
                        datetime.now().isoformat(),
                        motivo,
                        suggestion_id,
                    ),
                )

                # Atualizar embed
                if message.embeds:
                    embed: discord.Embed = message.embeds[0]
                    embed.color = color

                    # Atualizar status
                    for i, field in enumerate(embed.fields):
                        if "Status" in field.name:
                            status_texts: dict[str, str] = {
                                "approved": f"{emoji} **Aprovada** - Implementação em andamento",
                                "rejected": f"{emoji} **Rejeitada** - Não será implementada",
                                "paused": f"{emoji} **Pausada** - Em análise",
                            }
                            embed.set_field_at(
                                i, name="📅 Status", value=status_texts[status], inline=True
                            )
                            break

                    # Adicionar decisão
                    embed.add_field(
                        name="⚖️ Decisão Admin",
                        value=f"**Por:** {interaction.user.mention}\n"
                        f"**Em:** <t:{int(datetime.now().timestamp())}:F>\n"
                        + (f"**Motivo:** {motivo}" if motivo else "**Motivo:** Não especificado"),
                        inline=False,
                    )

                    await message.edit(embed=embed, view=None)

                # Confirmação
                await interaction.followup.send(
                    f"{emoji} **Sugestão {status}!**\n"
                    f"ID: `{suggestion_id}`\n"
                    f"Título: {suggestion['title']}",
                    ephemeral=True,
                )

            else:
                # Mostrar interface de gerenciamento
                manage_embed: discord.Embed = discord.Embed(
                    title="⚖️ **GERENCIAR SUGESTÃO**", color=0x2F3136, timestamp=datetime.now()
                )

                manage_embed.add_field(
                    name="💡 Sugestão",
                    value=f"**{suggestion['title']}**\n{suggestion['description'][:200]}{'...' if len(suggestion['description']) > 200 else ''}",
                    inline=False,
                )

                manage_embed.add_field(
                    name="👤 Autor",
                    value=f"<@{suggestion['user_id']}>\n`{suggestion['user_id']}`",
                    inline=True,
                )

                manage_embed.add_field(
                    name="📂 Categoria", value=suggestion["category"], inline=True
                )

                manage_embed.add_field(name="🆔 ID", value=f"`{suggestion_id}`", inline=True)

                manage_embed.add_field(
                    name="📅 Status Atual",
                    value=f"🟡 **{suggestion['status'].title()}**",
                    inline=True,
                )

                manage_embed.add_field(
                    name="⏰ Criado",
                    value=f"<t:{int(datetime.fromisoformat(suggestion['created_at']).timestamp())}:R>",
                    inline=True,
                )

                # Buscar votos
                try:
                    votes: list[dict[str, Any]] | None = await database.get_all(
                        "SELECT vote_type FROM suggestion_votes WHERE suggestion_id = ?",
                        (suggestion_id,),
                    )

                    approve_count: int = len([v for v in votes if v["vote_type"] == "approve"])
                    reject_count: int = len([v for v in votes if v["vote_type"] == "reject"])
                    neutral_count: int = len([v for v in votes if v["vote_type"] == "neutral"])

                    manage_embed.add_field(
                        name="📊 Votação",
                        value=f"👍 **{approve_count}** | 👎 **{reject_count}** | 🤷 **{neutral_count}**\n"
                        f"**Total:** {len(votes)} votos",
                        inline=False,
                    )
                except:
                    manage_embed.add_field(
                        name="📊 Votação", value="Erro ao carregar votos", inline=False
                    )

                manage_embed.set_footer(
                    text="Use os botões abaixo para tomar uma decisão",
                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
                )

                view: SuggestionManageView = SuggestionManageView(suggestion)
                await interaction.followup.send(embed=manage_embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando suggestion-manage: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao gerenciar sugestão. Tente novamente.", ephemeral=True
                )
            except:
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SuggestionManage(bot))
