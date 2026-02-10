"""
Sistema de Tickets - Gerenciar Tickets
Comando para listar e gerenciar todos os tickets
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class TicketListView(discord.ui.View):
    """Interface para navegação na lista de tickets"""

    def __init__(
        self, tickets_data: list[dict[str, Any]], guild: discord.Guild, page: int = 0
    ) -> None:
        super().__init__(timeout=300)
        self.tickets_data: list[dict[str, Any]] = tickets_data
        self.guild: discord.Guild = guild
        self.page: int = page
        self.items_per_page: int = 5
        self.max_pages: int = max(
            1, (len(tickets_data) + self.items_per_page - 1) // self.items_per_page
        )

        # Atualizar botões
        self.update_buttons()

    def update_buttons(self) -> None:
        """Atualiza estado dos botões de navegação"""
        self.previous_page.disabled = self.page <= 0
        self.next_page.disabled = self.page >= self.max_pages - 1

        # Atualizar label da página
        self.page_info.label = f"Página {self.page + 1}/{self.max_pages}"

    def get_page_embed(self) -> discord.Embed:
        """Gera embed da página atual"""
        start_idx: int = self.page * self.items_per_page
        end_idx: int = start_idx + self.items_per_page
        page_tickets: list[dict[str, Any]] = self.tickets_data[start_idx:end_idx]

        embed: discord.Embed = discord.Embed(
            title="🎫 **LISTA DE TICKETS**",
            description=f"Mostrando {len(page_tickets)} de {len(self.tickets_data)} tickets",
            color=0x2F3136,
            timestamp=datetime.now(),
        )

        if not page_tickets:
            embed.add_field(
                name="📝 Nenhum ticket encontrado",
                value="Não há tickets com os filtros aplicados.",
                inline=False,
            )
            return embed

        for i, ticket in enumerate(page_tickets, start=start_idx + 1):
            # Buscar canal
            channel: discord.TextChannel | None = self.guild.get_channel(
                int(ticket["channel_id"])
            )
            channel_mention: str = (
                channel.mention if channel else f"Canal deletado (`{ticket['channel_id']}`)"
            )

            # Buscar usuário
            user: discord.Member | None = self.guild.get_member(int(ticket["user_id"]))
            user_info: str = (
                user.mention if user else f"Usuário não encontrado (`{ticket['user_id']}`)"
            )

            # Status emoji
            status_emoji: str = {"open": "🟢", "closed": "🔴", "pending": "🟡"}.get(
                ticket["status"], "⚪"
            )

            # Calcular duração
            created_time: datetime = datetime.fromisoformat(ticket["created_at"])
            if ticket.get("closed_at"):
                closed_time: datetime = datetime.fromisoformat(ticket["closed_at"])
                duration = closed_time - created_time
            else:
                duration = datetime.now() - created_time

            duration_str: str = (
                f"{duration.days}d {duration.seconds // 3600}h"
                if duration.days > 0
                else f"{duration.seconds // 3600}h {(duration.seconds % 3600) // 60}m"
            )

            embed.add_field(
                name=f"{status_emoji} Ticket #{i} - {ticket['status'].title()}",
                value=f"**👤 Usuário:** {user_info}\n"
                f"**📍 Canal:** {channel_mention}\n"
                f"**⏰ Criado:** <t:{int(created_time.timestamp())}:R>\n"
                f"**⏱️ Duração:** {duration_str}"
                + (
                    f"\n**🔒 Fechado por:** <@{ticket.get('closed_by', 'N/A')}>"
                    if ticket.get("closed_at")
                    else ""
                ),
                inline=False,
            )

        embed.set_footer(
            text=f"Página {self.page + 1}/{self.max_pages} • Total: {len(self.tickets_data)} tickets",
            icon_url=self.guild.icon.url if self.guild.icon else None,
        )

        return embed

    @discord.ui.button(label="◀️ Anterior", style=discord.ButtonStyle.secondary)
    async def previous_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.page > 0:
            self.page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Página 1/1", style=discord.ButtonStyle.primary, disabled=True)
    async def page_info(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()

    @discord.ui.button(label="Próxima ▶️", style=discord.ButtonStyle.secondary)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.page < self.max_pages - 1:
            self.page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="🔄 Atualizar", style=discord.ButtonStyle.success, emoji="🔄")
    async def refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        # Recarregar dados do banco
        try:
            from ...utils.database import database

            fresh_tickets: list[dict[str, Any]] | None = await database.get_all(
                "SELECT * FROM tickets WHERE guild_id = ? ORDER BY created_at DESC",
                (str(self.guild.id),),
            )
            self.tickets_data = fresh_tickets or []
            self.max_pages = max(
                1, (len(self.tickets_data) + self.items_per_page - 1) // self.items_per_page
            )

            # Ajustar página se necessário
            if self.page >= self.max_pages:
                self.page = max(0, self.max_pages - 1)

            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao atualizar: {e}", ephemeral=True)

    @discord.ui.button(label="🗑️ Limpar Fechados", style=discord.ButtonStyle.danger)
    async def cleanup_closed(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        # Verificar permissões
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Apenas administradores podem limpar tickets fechados!", ephemeral=True
            )
            return

        try:
            # Contar tickets fechados
            from ...utils.database import database

            closed_tickets: list[dict[str, Any]] | None = await database.get_all(
                "SELECT * FROM tickets WHERE guild_id = ? AND status = 'closed'",
                (str(self.guild.id),),
            )

            if not closed_tickets:
                await interaction.response.send_message(
                    "ℹ️ Não há tickets fechados para limpar!", ephemeral=True
                )
                return

            # Confirmar limpeza
            confirm_embed: discord.Embed = discord.Embed(
                title="⚠️ **CONFIRMAR LIMPEZA**",
                description=f"Isso irá **remover permanentemente** {len(closed_tickets)} tickets fechados do banco de dados.\n\n"
                f"**⚠️ Esta ação não pode ser desfeita!**",
                color=0xFF6B6B,
                timestamp=datetime.now(),
            )

            confirm_view: ConfirmCleanupView = ConfirmCleanupView(closed_tickets, self)

            await interaction.response.send_message(
                embed=confirm_embed, view=confirm_view, ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


class ConfirmCleanupView(discord.ui.View):
    """View para confirmar limpeza de tickets"""

    def __init__(
        self, tickets_to_clean: list[dict[str, Any]], parent_view: TicketListView
    ) -> None:
        super().__init__(timeout=60)
        self.tickets_to_clean: list[dict[str, Any]] = tickets_to_clean
        self.parent_view: TicketListView = parent_view

    @discord.ui.button(label="✅ Confirmar Limpeza", style=discord.ButtonStyle.danger)
    async def confirm_cleanup(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            await interaction.response.defer()

            # Remover tickets fechados do banco
            from ...utils.database import database

            await database.execute(
                "DELETE FROM tickets WHERE guild_id = ? AND status = 'closed'",
                (str(interaction.guild.id),),
            )

            # Atualizar view principal
            fresh_tickets: list[dict[str, Any]] | None = await database.get_all(
                "SELECT * FROM tickets WHERE guild_id = ? ORDER BY created_at DESC",
                (str(interaction.guild.id),),
            )
            self.parent_view.tickets_data = fresh_tickets or []
            self.parent_view.max_pages = max(1, (len(fresh_tickets or []) + 5 - 1) // 5)
            self.parent_view.page = 0
            self.parent_view.update_buttons()

            success_embed: discord.Embed = discord.Embed(
                title="✅ Limpeza Concluída!",
                description=f"**{len(self.tickets_to_clean)} tickets fechados** foram removidos do banco de dados.",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            await interaction.edit_original_response(embed=success_embed, view=None)

        except Exception as e:
            await interaction.followup.send(f"❌ Erro na limpeza: {e}", ephemeral=True)

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel_cleanup(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.edit_message(
            content="❌ **Limpeza cancelada.**", embed=None, view=None
        )


class TicketList(commands.Cog):
    """Sistema de listagem e gerenciamento de tickets"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(name="ticket-list", description="📋 Listar e gerenciar todos os tickets")
    @app_commands.describe(
        filtro="Filtrar tickets por status", usuario="Filtrar tickets de um usuário específico"
    )
    async def ticket_list(
        self,
        interaction: discord.Interaction,
        filtro: Literal["abertos", "fechados", "todos"] | None = "todos",
        usuario: discord.Member | None = None,
    ) -> None:
        try:
            # 🛡️ VERIFICAR PERMISSÕES
            if not (
                interaction.user.guild_permissions.manage_channels
                or interaction.user.guild_permissions.administrator
            ):
                await interaction.response.send_message(
                    "❌ Você não tem permissão para listar tickets. **Necessário**: Gerenciar Canais",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # 💾 BUSCAR TICKETS NO BANCO
            try:
                from ...utils.database import database

                # Construir query baseada nos filtros
                query: str = "SELECT * FROM tickets WHERE guild_id = ?"
                params: list[str] = [str(interaction.guild.id)]

                if filtro == "abertos":
                    query += " AND status = 'open'"
                elif filtro == "fechados":
                    query += " AND status = 'closed'"

                if usuario:
                    query += " AND user_id = ?"
                    params.append(str(usuario.id))

                query += " ORDER BY created_at DESC"

                tickets: list[dict[str, Any]] | None = await database.get_all(query, params)

            except Exception as e:
                print(f"❌ Erro ao buscar tickets: {e}")
                tickets = None

            # Garantir lista vazia se None
            tickets = tickets or []

            # 📊 ESTATÍSTICAS GERAIS
            total_tickets: int = len(tickets)
            open_tickets: int = len([t for t in tickets if t["status"] == "open"])
            closed_tickets: int = len([t for t in tickets if t["status"] == "closed"])

            if not tickets:
                # 📝 NENHUM TICKET ENCONTRADO
                no_tickets_embed: discord.Embed = discord.Embed(
                    title="📋 Lista de Tickets",
                    description="Nenhum ticket encontrado com os filtros aplicados.",
                    color=0x2F3136,
                    timestamp=datetime.now(),
                )

                no_tickets_embed.add_field(
                    name="📊 Estatísticas Gerais",
                    value=f"**Total:** {total_tickets}\n"
                    f"**Abertos:** {open_tickets} 🟢\n"
                    f"**Fechados:** {closed_tickets} 🔴",
                    inline=True,
                )

                no_tickets_embed.add_field(
                    name="🔍 Filtros Aplicados",
                    value=f"**Status:** {filtro.title()}\n"
                    f"**Usuário:** {usuario.mention if usuario else 'Todos'}",
                    inline=True,
                )

                no_tickets_embed.set_footer(
                    text="Use /ticket-setup para configurar o sistema",
                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
                )

                await interaction.followup.send(embed=no_tickets_embed, ephemeral=True)
                return

            # 🎮 CRIAR VIEW COM PAGINAÇÃO
            view: TicketListView = TicketListView(tickets, interaction.guild)
            embed: discord.Embed = view.get_page_embed()

            # Adicionar estatísticas no embed
            stats_text: str = "**📊 Estatísticas:**\n"
            stats_text += f"• Total: {total_tickets}\n"
            stats_text += f"• Abertos: {open_tickets} 🟢\n"
            stats_text += f"• Fechados: {closed_tickets} 🔴"

            if filtro != "todos" or usuario:
                stats_text += "\n\n**🔍 Filtros:**\n"
                stats_text += f"• Status: {filtro.title()}\n"
                if usuario:
                    stats_text += f"• Usuário: {usuario.mention}"

            embed.add_field(name="📈 Informações", value=stats_text, inline=False)

            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando ticket-list: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao listar tickets. Tente novamente.", ephemeral=True
                )
            except:
                pass


async def setup(bot: commands.Bot) -> None:
    """Carrega o cog"""
    await bot.add_cog(TicketList(bot))
