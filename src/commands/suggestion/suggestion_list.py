"""
Sistema de Sugestões - Listar e Buscar
Comando para listar todas as sugestões com filtros
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class SuggestionListView(discord.ui.View):
    """Interface de navegação para lista de sugestões"""

    def __init__(
        self,
        suggestions: list[dict[str, Any]],
        guild: discord.Guild,
        filter_status: str = "all",
        filter_user: discord.Member | None = None,
        page: int = 0,
    ) -> None:
        super().__init__(timeout=300)
        self.suggestions: list[dict[str, Any]] = suggestions
        self.guild: discord.Guild = guild
        self.filter_status: str = filter_status
        self.filter_user: discord.Member | None = filter_user
        self.page: int = page
        self.items_per_page: int = 5
        self.max_pages: int = max(1, (len(suggestions) + self.items_per_page - 1) // self.items_per_page)

        self.update_buttons()

    def update_buttons(self) -> None:
        """Atualiza estado dos botões"""
        self.previous_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= self.max_pages - 1
        self.page_button.label = f"Página {self.page + 1}/{self.max_pages}"

    def get_page_embed(self) -> discord.Embed:
        """Gera embed da página atual"""
        start_idx: int = self.page * self.items_per_page
        end_idx: int = start_idx + self.items_per_page
        page_suggestions: list[dict[str, Any]] = self.suggestions[start_idx:end_idx]

        embed: discord.Embed = discord.Embed(
            title="💡 **LISTA DE SUGESTÕES**",
            description=f"Mostrando {len(page_suggestions)} de {len(self.suggestions)} sugestões",
            color=0x2F3136,
            timestamp=datetime.now(),
        )

        if not page_suggestions:
            embed.add_field(
                name="📝 Nenhuma sugestão encontrada",
                value="Não há sugestões com os filtros aplicados.",
                inline=False,
            )
            return embed

        for i, suggestion in enumerate(page_suggestions, start=start_idx + 1):
            # Status emoji
            status_emojis: dict[str, str] = {"pending": "🟡", "approved": "✅", "rejected": "❌", "paused": "⏸️"}

            status_emoji: str = status_emojis.get(suggestion["status"], "⚪")

            # Buscar autor
            author: discord.Member | None = self.guild.get_member(int(suggestion["user_id"]))
            author_text: str = (
                author.mention if author else f"Usuário não encontrado (`{suggestion['user_id']}`)"
            )

            # Calcular tempo
            created_time: datetime = datetime.fromisoformat(suggestion["created_at"])

            # Buscar votos
            try:
                from ...utils.database import database

                async def get_votes() -> list[dict[str, Any]]:
                    return await database.get_all(
                        "SELECT vote_type FROM suggestion_votes WHERE suggestion_id = ?",
                        (suggestion["id"],),
                    )

                # Como não podemos usar async aqui, vamos mostrar sem votos por enquanto
                votes_text: str = "📊 Carregando..."
            except:
                votes_text = "📊 N/A"

            embed.add_field(
                name=f"{status_emoji} Sugestão #{i} - {suggestion['status'].title()}",
                value=f"**💡 Título:** {suggestion['title'][:50]}{'...' if len(suggestion['title']) > 50 else ''}\n"
                f"**👤 Autor:** {author_text}\n"
                f"**📂 Categoria:** `{suggestion['category']}`\n"
                f"**🆔 ID:** `{suggestion['id']}`\n"
                f"**⏰ Criado:** <t:{int(created_time.timestamp())}:R>\n"
                f"**{votes_text}**",
                inline=False,
            )

        # Estatísticas
        stats: dict[str, int] = self.get_statistics()
        embed.add_field(
            name="📊 Estatísticas",
            value=f"**Total:** {stats['total']}\n"
            f"**Pendentes:** {stats['pending']} 🟡\n"
            f"**Aprovadas:** {stats['approved']} ✅\n"
            f"**Rejeitadas:** {stats['rejected']} ❌",
            inline=True,
        )

        # Filtros aplicados
        filters_text: str = f"**Status:** {self.filter_status.title()}"
        if self.filter_user:
            filters_text += f"\n**Usuário:** {self.filter_user.mention}"

        embed.add_field(name="🔍 Filtros", value=filters_text, inline=True)

        embed.set_footer(
            text=f"Página {self.page + 1}/{self.max_pages} • Use /suggestion-manage para gerenciar",
            icon_url=self.guild.icon.url if self.guild.icon else None,
        )

        return embed

    def get_statistics(self) -> dict[str, int]:
        """Calcula estatísticas das sugestões"""
        stats: dict[str, int] = {
            "total": len(self.suggestions),
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "paused": 0,
        }

        for suggestion in self.suggestions:
            status: str = suggestion["status"]
            if status in stats:
                stats[status] += 1

        return stats

    @discord.ui.button(label="◀️ Anterior", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.page > 0:
            self.page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Página 1/1", style=discord.ButtonStyle.primary, disabled=True)
    async def page_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()

    @discord.ui.button(label="Próxima ▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.page < self.max_pages - 1:
            self.page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="🔄 Atualizar", style=discord.ButtonStyle.success)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        try:
            # Recarregar sugestões
            from ...utils.database import database

            query: str = "SELECT * FROM suggestions WHERE guild_id = ?"
            params: list[str] = [str(self.guild.id)]

            if self.filter_status != "all":
                query += " AND status = ?"
                params.append(self.filter_status)

            if self.filter_user:
                query += " AND user_id = ?"
                params.append(str(self.filter_user.id))

            query += " ORDER BY created_at DESC"

            fresh_suggestions: list[dict[str, Any]] | None = await database.get_all(query, params)
            self.suggestions = fresh_suggestions or []
            self.max_pages = max(
                1, (len(self.suggestions) + self.items_per_page - 1) // self.items_per_page
            )

            if self.page >= self.max_pages:
                self.page = max(0, self.max_pages - 1)

            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao atualizar: {e}", ephemeral=True)


class SuggestionList(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(name="suggestion-list", description="📋 Listar sugestões do servidor")
    @app_commands.describe(
        status="Filtrar por status das sugestões",
        usuario="Filtrar sugestões de um usuário específico",
        categoria="Filtrar por categoria",
    )
    async def suggestion_list(
        self,
        interaction: discord.Interaction,
        status: Literal["all", "pending", "approved", "rejected", "paused"] | None = "all",
        usuario: discord.Member | None = None,
        categoria: str | None = None,
    ) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # Buscar sugestões no banco
            try:
                from ...utils.database import database

                query: str = "SELECT * FROM suggestions WHERE guild_id = ?"
                params: list[str] = [str(interaction.guild.id)]

                if status != "all":
                    query += " AND status = ?"
                    params.append(status)

                if usuario:
                    query += " AND user_id = ?"
                    params.append(str(usuario.id))

                if categoria:
                    query += " AND category = ?"
                    params.append(categoria)

                query += " ORDER BY created_at DESC"

                suggestions: list[dict[str, Any]] | None = await database.get_all(query, params)

            except Exception as e:
                print(f"❌ Erro ao buscar sugestões: {e}")
                await interaction.followup.send(
                    "❌ Erro ao buscar sugestões no banco de dados.", ephemeral=True
                )
                return

            if not suggestions:
                # Nenhuma sugestão encontrada
                no_suggestions_embed: discord.Embed = discord.Embed(
                    title="💡 Lista de Sugestões",
                    description="Nenhuma sugestão encontrada com os filtros aplicados.",
                    color=0x2F3136,
                    timestamp=datetime.now(),
                )

                no_suggestions_embed.add_field(
                    name="🔍 Filtros Aplicados",
                    value=f"**Status:** {status.title()}\n"
                    + (f"**Usuário:** {usuario.mention}\n" if usuario else "")
                    + (f"**Categoria:** `{categoria}`\n" if categoria else ""),
                    inline=True,
                )

                no_suggestions_embed.add_field(
                    name="💡 Dica",
                    value="Use `/suggest` para criar uma sugestão\n"
                    "ou altere os filtros para ver mais resultados.",
                    inline=True,
                )

                no_suggestions_embed.set_footer(
                    text="Sistema de Sugestões",
                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
                )

                await interaction.followup.send(embed=no_suggestions_embed, ephemeral=True)
                return

            # Criar interface de lista paginada
            view: SuggestionListView = SuggestionListView(suggestions, interaction.guild, status, usuario)
            embed: discord.Embed = view.get_page_embed()

            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando suggestion-list: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao listar sugestões. Tente novamente.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(
        name="suggestion-search", description="🔍 Buscar sugestão por ID ou palavra-chave"
    )
    @app_commands.describe(termo="ID da sugestão ou palavra-chave para buscar")
    async def suggestion_search(self, interaction: discord.Interaction, termo: str) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # Buscar por ID exato primeiro
            try:
                from ...utils.database import database

                suggestion_by_id: dict[str, Any] | None = await database.get(
                    "SELECT * FROM suggestions WHERE id = ? AND guild_id = ?",
                    (termo, str(interaction.guild.id)),
                )

                if suggestion_by_id:
                    # Encontrou por ID exato
                    await self.show_suggestion_details(interaction, suggestion_by_id)
                    return

            except Exception as e:
                print(f"❌ Erro na busca por ID: {e}")

            # Buscar por palavra-chave no título e descrição
            try:
                keyword_suggestions: list[dict[str, Any]] | None = await database.get_all(
                    "SELECT * FROM suggestions WHERE guild_id = ? AND (title LIKE ? OR description LIKE ?) ORDER BY created_at DESC LIMIT 10",
                    (str(interaction.guild.id), f"%{termo}%", f"%{termo}%"),
                )

                if not keyword_suggestions:
                    await interaction.followup.send(
                        f"🔍 **Nenhuma sugestão encontrada!**\n\n"
                        f"**Termo buscado:** `{termo}`\n"
                        f"**Buscou em:** Títulos, descrições e IDs\n\n"
                        f"💡 **Dicas:**\n"
                        f"• Verifique se o ID está correto\n"
                        f"• Tente palavras-chave diferentes\n"
                        f"• Use `/suggestion-list` para ver todas",
                        ephemeral=True,
                    )
                    return

                # Mostrar resultados da busca
                search_embed: discord.Embed = discord.Embed(
                    title="🔍 **RESULTADOS DA BUSCA**",
                    description=f"Encontradas {len(keyword_suggestions)} sugestões para: `{termo}`",
                    color=0x2F3136,
                    timestamp=datetime.now(),
                )

                for i, suggestion in enumerate(keyword_suggestions[:5], 1):
                    status_emojis: dict[str, str] = {
                        "pending": "🟡",
                        "approved": "✅",
                        "rejected": "❌",
                        "paused": "⏸️",
                    }

                    status_emoji: str = status_emojis.get(suggestion["status"], "⚪")

                    author: discord.Member | None = interaction.guild.get_member(int(suggestion["user_id"]))
                    author_text: str = author.mention if author else "Usuário não encontrado"

                    created_time: datetime = datetime.fromisoformat(suggestion["created_at"])

                    search_embed.add_field(
                        name=f"{status_emoji} {suggestion['title'][:40]}{'...' if len(suggestion['title']) > 40 else ''}",
                        value=f"**ID:** `{suggestion['id']}`\n"
                        f"**Autor:** {author_text}\n"
                        f"**Status:** {suggestion['status'].title()}\n"
                        f"**Criado:** <t:{int(created_time.timestamp())}:R>",
                        inline=True,
                    )

                if len(keyword_suggestions) > 5:
                    search_embed.add_field(
                        name="➕ Mais resultados",
                        value=f"E mais {len(keyword_suggestions) - 5} sugestões...\n"
                        f"Use filtros em `/suggestion-list` para ver todas.",
                        inline=False,
                    )

                search_embed.set_footer(
                    text=f"Termo: {termo} • Use o ID para ver detalhes completos",
                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
                )

                await interaction.followup.send(embed=search_embed, ephemeral=True)

            except Exception as e:
                print(f"❌ Erro na busca por palavra-chave: {e}")
                await interaction.followup.send(
                    "❌ Erro ao buscar sugestões. Tente novamente.", ephemeral=True
                )

        except Exception as e:
            print(f"❌ Erro no comando suggestion-search: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro na busca. Tente novamente.", ephemeral=True
                )
            except:
                pass

    async def show_suggestion_details(self, interaction: discord.Interaction, suggestion: dict[str, Any]) -> None:
        """Mostra detalhes completos de uma sugestão"""
        try:
            from ...utils.database import database

            # Buscar votos
            votes: list[dict[str, Any]] | None = await database.get_all(
                "SELECT vote_type FROM suggestion_votes WHERE suggestion_id = ?",
                (suggestion["id"],),
            )

            approve_count: int = len([v for v in votes if v["vote_type"] == "approve"])
            reject_count: int = len([v for v in votes if v["vote_type"] == "reject"])
            neutral_count: int = len([v for v in votes if v["vote_type"] == "neutral"])
            total_votes: int = len(votes)

            # Embed detalhado
            detail_embed: discord.Embed = discord.Embed(
                title=f"💡 **{suggestion['title']}**",
                description=suggestion["description"],
                color={
                    "pending": 0xFFFF00,
                    "approved": 0x00FF00,
                    "rejected": 0xFF0000,
                    "paused": 0xFFA500,
                }.get(suggestion["status"], 0x2F3136),
                timestamp=datetime.now(),
            )

            author: discord.Member | None = interaction.guild.get_member(int(suggestion["user_id"]))
            author_text: str = (
                author.mention if author else f"Usuário não encontrado (`{suggestion['user_id']}`)"
            )

            detail_embed.add_field(name="👤 Autor", value=author_text, inline=True)

            detail_embed.add_field(name="📂 Categoria", value=suggestion["category"], inline=True)

            detail_embed.add_field(name="🆔 ID", value=f"`{suggestion['id']}`", inline=True)

            status_emojis: dict[str, str] = {
                "pending": "🟡 Pendente",
                "approved": "✅ Aprovada",
                "rejected": "❌ Rejeitada",
                "paused": "⏸️ Pausada",
            }

            detail_embed.add_field(
                name="📅 Status",
                value=status_emojis.get(suggestion["status"], suggestion["status"].title()),
                inline=True,
            )

            created_time: datetime = datetime.fromisoformat(suggestion["created_at"])
            detail_embed.add_field(
                name="⏰ Criado", value=f"<t:{int(created_time.timestamp())}:F>", inline=True
            )

            # Votação
            if total_votes > 0:
                approve_pct: float = approve_count / total_votes * 100
                reject_pct: float = reject_count / total_votes * 100
                neutral_pct: float = neutral_count / total_votes * 100

                votes_text: str = (
                    f"**👍 Aprovar:** {approve_count} ({approve_pct:.1f}%)\n"
                    f"**👎 Rejeitar:** {reject_count} ({reject_pct:.1f}%)\n"
                    f"**🤷 Neutro:** {neutral_count} ({neutral_pct:.1f}%)\n"
                    f"**📊 Total:** {total_votes} votos"
                )
            else:
                votes_text = "Nenhum voto ainda"

            detail_embed.add_field(name="📊 Votação", value=votes_text, inline=False)

            # Se foi decidida por admin
            if suggestion.get("decided_by"):
                decider: discord.Member | None = interaction.guild.get_member(int(suggestion["decided_by"]))
                decider_text: str = decider.mention if decider else "Admin não encontrado"

                decided_time: datetime = datetime.fromisoformat(suggestion["decided_at"])

                decision_text: str = f"**Por:** {decider_text}\n"
                decision_text += f"**Em:** <t:{int(decided_time.timestamp())}:F>\n"

                if suggestion.get("decision_reason"):
                    decision_text += f"**Motivo:** {suggestion['decision_reason']}"
                else:
                    decision_text += "**Motivo:** Não especificado"

                detail_embed.add_field(name="⚖️ Decisão Admin", value=decision_text, inline=False)

            detail_embed.set_footer(
                text=f"Sugestão {suggestion['id']} • Criada em {created_time.strftime('%d/%m/%Y')}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            if author:
                detail_embed.set_thumbnail(url=author.display_avatar.url)

            await interaction.followup.send(embed=detail_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro ao mostrar detalhes: {e}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SuggestionList(bot))
