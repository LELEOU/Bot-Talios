"""
Sistema de Poll - Listar Votações
Comando para listar todas as votações do servidor
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class PollListView(discord.ui.View):
    """Interface de navegação para lista de polls"""

    def __init__(
        self,
        polls: list[dict[str, Any]],
        guild: discord.Guild,
        filter_status: str = "all",
        filter_user: discord.Member | None = None,
        page: int = 0,
    ) -> None:
        super().__init__(timeout=300)
        self.polls: list[dict[str, Any]] = polls
        self.guild: discord.Guild = guild
        self.filter_status: str = filter_status
        self.filter_user: discord.Member | None = filter_user
        self.page: int = page
        self.items_per_page: int = 4
        self.max_pages: int = max(1, (len(polls) + self.items_per_page - 1) // self.items_per_page)

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
        page_polls: list[dict[str, Any]] = self.polls[start_idx:end_idx]

        embed: discord.Embed = discord.Embed(
            title="🗳️ **LISTA DE VOTAÇÕES**",
            description=f"Mostrando {len(page_polls)} de {len(self.polls)} votações",
            color=0x2F3136,
            timestamp=datetime.now(),
        )

        if not page_polls:
            embed.add_field(
                name="📝 Nenhuma votação encontrada",
                value="Não há votações com os filtros aplicados.",
                inline=False,
            )
            return embed

        for i, poll in enumerate(page_polls, start=start_idx + 1):
            # Status emoji
            status_emojis: dict[str, str] = {"active": "🟢", "finished": "🔴", "paused": "🟡"}

            status_emoji: str = status_emojis.get(poll["status"], "⚪")

            # Buscar criador
            creator: discord.Member | None = self.guild.get_member(int(poll["user_id"]))
            creator_text: str = (
                creator.mention if creator else f"Usuário não encontrado (`{poll['user_id']}`)"
            )

            # Calcular tempo
            created_time: datetime = datetime.fromisoformat(poll["created_at"])

            # Informações de tempo
            time_info: str = f"<t:{int(created_time.timestamp())}:R>"
            if poll["end_time"] and poll["status"] == "active":
                end_time: datetime = datetime.fromisoformat(poll["end_time"])
                if datetime.now() < end_time:
                    time_info += f" • Termina <t:{int(end_time.timestamp())}:R>"
                else:
                    time_info += " • **EXPIRADA**"
            elif poll["end_time"]:
                end_time: datetime = datetime.fromisoformat(poll["end_time"])
                time_info += f" • Terminou <t:{int(end_time.timestamp())}:R>"

            # Processar opções
            try:
                options: list[dict[str, str]] = json.loads(poll["options"])
                options_preview: str = ", ".join(
                    [
                        opt["text"][:15] + ("..." if len(opt["text"]) > 15 else "")
                        for opt in options[:3]
                    ]
                )
                if len(options) > 3:
                    options_preview += f" +{len(options) - 3} mais"
            except:
                options_preview: str = "Erro ao carregar opções"

            # Canal
            channel: discord.TextChannel | None = self.guild.get_channel(int(poll["channel_id"]))
            channel_text: str = channel.mention if channel else "Canal não encontrado"

            embed.add_field(
                name=f"{status_emoji} Votação #{i} - {poll['status'].title()}",
                value=f"**🗳️ Pergunta:** {poll['question'][:60]}{'...' if len(poll['question']) > 60 else ''}\n"
                f"**📊 Opções:** {options_preview}\n"
                f"**👤 Criador:** {creator_text}\n"
                f"**📍 Canal:** {channel_text}\n"
                f"**🆔 ID:** `{poll['id']}`\n"
                f"**⏰ {time_info}**",
                inline=False,
            )

        # Estatísticas
        stats: dict[str, int] = self.get_statistics()
        embed.add_field(
            name="📊 Estatísticas",
            value=f"**Total:** {stats['total']}\n"
            f"**Ativas:** {stats['active']} 🟢\n"
            f"**Finalizadas:** {stats['finished']} 🔴\n"
            f"**Pausadas:** {stats.get('paused', 0)} 🟡",
            inline=True,
        )

        # Filtros aplicados
        filters_text: str = f"**Status:** {self.filter_status.title()}"
        if self.filter_user:
            filters_text += f"\n**Criador:** {self.filter_user.mention}"

        embed.add_field(name="🔍 Filtros", value=filters_text, inline=True)

        embed.add_field(
            name="💡 Comandos úteis",
            value="`/poll-results <id>` - Ver resultados\n`/poll-end <id>` - Finalizar votação",
            inline=True,
        )

        embed.set_footer(
            text=f"Página {self.page + 1}/{self.max_pages} • Use os IDs para interagir com votações",
            icon_url=self.guild.icon.url if self.guild.icon else None,
        )

        return embed

    def get_statistics(self) -> dict[str, int]:
        """Calcula estatísticas das votações"""
        stats: dict[str, int] = {"total": len(self.polls), "active": 0, "finished": 0, "paused": 0}

        for poll in self.polls:
            status: str = poll["status"]
            if status in stats:
                stats[status] += 1

        return stats

    @discord.ui.button(label="◀️ Anterior", style=discord.ButtonStyle.secondary)
    async def previous_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.page > 0:
            self.page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Página 1/1", style=discord.ButtonStyle.primary, disabled=True)
    async def page_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()

    @discord.ui.button(label="Próxima ▶️", style=discord.ButtonStyle.secondary)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.page < self.max_pages - 1:
            self.page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="🔄 Atualizar", style=discord.ButtonStyle.success)
    async def refresh_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            # Recarregar votações
            from ...utils.database import database

            query: str = "SELECT * FROM polls WHERE guild_id = ?"
            params: list[str] = [str(self.guild.id)]

            if self.filter_status != "all":
                query += " AND status = ?"
                params.append(self.filter_status)

            if self.filter_user:
                query += " AND user_id = ?"
                params.append(str(self.filter_user.id))

            query += " ORDER BY created_at DESC"

            fresh_polls: list[dict[str, Any]] | None = await database.get_all(query, params)
            self.polls = fresh_polls or []
            self.max_pages = max(
                1, (len(self.polls) + self.items_per_page - 1) // self.items_per_page
            )

            if self.page >= self.max_pages:
                self.page = max(0, self.max_pages - 1)

            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao atualizar: {e}", ephemeral=True)


class PollList(commands.Cog):
    """Sistema de listagem de enquetes/votações"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(name="poll-list", description="📋 Listar votações do servidor")
    @app_commands.describe(
        status="Filtrar por status das votações",
        criador="Filtrar votações de um usuário específico",
    )
    async def poll_list(
        self,
        interaction: discord.Interaction,
        status: Literal["all", "active", "finished", "paused"] | None = "all",
        criador: discord.Member | None = None,
    ) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # Buscar votações no banco
            try:
                from ...utils.database import database

                query: str = "SELECT * FROM polls WHERE guild_id = ?"
                params: list[str] = [str(interaction.guild.id)]

                if status != "all":
                    query += " AND status = ?"
                    params.append(status)

                if criador:
                    query += " AND user_id = ?"
                    params.append(str(criador.id))

                query += " ORDER BY created_at DESC"

                polls: list[dict[str, Any]] | None = await database.get_all(query, params)

            except Exception as e:
                print(f"❌ Erro ao buscar votações: {e}")
                await interaction.followup.send(
                    "❌ Erro ao buscar votações no banco de dados.", ephemeral=True
                )
                return

            if not polls:
                # Nenhuma votação encontrada
                no_polls_embed: discord.Embed = discord.Embed(
                    title="🗳️ Lista de Votações",
                    description="Nenhuma votação encontrada com os filtros aplicados.",
                    color=0x2F3136,
                    timestamp=datetime.now(),
                )

                no_polls_embed.add_field(
                    name="🔍 Filtros Aplicados",
                    value=f"**Status:** {status.title()}\n"
                    + (f"**Criador:** {criador.mention}\n" if criador else ""),
                    inline=True,
                )

                no_polls_embed.add_field(
                    name="💡 Dica",
                    value="Use `/poll-create` para criar uma votação\n"
                    "ou altere os filtros para ver mais resultados.",
                    inline=True,
                )

                no_polls_embed.set_footer(
                    text="Sistema de Votações",
                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
                )

                await interaction.followup.send(embed=no_polls_embed, ephemeral=True)
                return

            # Criar interface de lista paginada
            view: PollListView = PollListView(polls, interaction.guild, status, criador)
            embed: discord.Embed = view.get_page_embed()

            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando poll-list: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao listar votações. Tente novamente.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(
        name="poll-search", description="🔍 Buscar votação por ID ou palavra-chave"
    )
    @app_commands.describe(termo="ID da votação ou palavra-chave para buscar")
    async def poll_search(self, interaction: discord.Interaction, termo: str) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # Buscar por ID exato primeiro
            try:
                from ...utils.database import database

                poll_by_id: dict[str, Any] | None = await database.get(
                    "SELECT * FROM polls WHERE id = ? AND guild_id = ?",
                    (termo, str(interaction.guild.id)),
                )

                if poll_by_id:
                    # Encontrou por ID exato - mostrar detalhes
                    await self.show_poll_details(interaction, poll_by_id)
                    return

            except Exception as e:
                print(f"❌ Erro na busca por ID: {e}")

            # Buscar por palavra-chave na pergunta e descrição
            try:
                keyword_polls: list[dict[str, Any]] | None = await database.get_all(
                    "SELECT * FROM polls WHERE guild_id = ? AND (question LIKE ? OR description LIKE ?) ORDER BY created_at DESC LIMIT 10",
                    (str(interaction.guild.id), f"%{termo}%", f"%{termo}%"),
                )

                if not keyword_polls:
                    await interaction.followup.send(
                        f"🔍 **Nenhuma votação encontrada!**\n\n"
                        f"**Termo buscado:** `{termo}`\n"
                        f"**Buscou em:** Perguntas, descrições e IDs\n\n"
                        f"💡 **Dicas:**\n"
                        f"• Verifique se o ID está correto\n"
                        f"• Tente palavras-chave diferentes\n"
                        f"• Use `/poll-list` para ver todas as votações",
                        ephemeral=True,
                    )
                    return

                # Mostrar resultados da busca
                search_embed: discord.Embed = discord.Embed(
                    title="🔍 **RESULTADOS DA BUSCA**",
                    description=f"Encontradas {len(keyword_polls)} votações para: `{termo}`",
                    color=0x2F3136,
                    timestamp=datetime.now(),
                )

                for i, poll in enumerate(keyword_polls[:5], 1):
                    status_emojis: dict[str, str] = {
                        "active": "🟢",
                        "finished": "🔴",
                        "paused": "🟡",
                    }

                    status_emoji: str = status_emojis.get(poll["status"], "⚪")

                    creator: discord.Member | None = interaction.guild.get_member(
                        int(poll["user_id"])
                    )
                    creator_text: str = creator.mention if creator else "Usuário não encontrado"

                    created_time: datetime = datetime.fromisoformat(poll["created_at"])

                    # Contar votos
                    try:
                        votes: list[dict[str, Any]] | None = await database.get_all(
                            "SELECT COUNT(*) as count FROM poll_votes WHERE poll_id = ?",
                            (poll["id"],),
                        )
                        vote_count: int = votes[0]["count"] if votes else 0
                    except:
                        vote_count: int = 0

                    search_embed.add_field(
                        name=f"{status_emoji} {poll['question'][:40]}{'...' if len(poll['question']) > 40 else ''}",
                        value=f"**ID:** `{poll['id']}`\n"
                        f"**Criador:** {creator_text}\n"
                        f"**Status:** {poll['status'].title()}\n"
                        f"**Votos:** {vote_count}\n"
                        f"**Criado:** <t:{int(created_time.timestamp())}:R>",
                        inline=True,
                    )

                if len(keyword_polls) > 5:
                    search_embed.add_field(
                        name="➕ Mais resultados",
                        value=f"E mais {len(keyword_polls) - 5} votações...\n"
                        f"Use filtros em `/poll-list` para ver todas.",
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
                    "❌ Erro ao buscar votações. Tente novamente.", ephemeral=True
                )

        except Exception as e:
            print(f"❌ Erro no comando poll-search: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro na busca. Tente novamente.", ephemeral=True
                )
            except:
                pass

    async def show_poll_details(
        self, interaction: discord.Interaction, poll: dict[str, Any]
    ) -> None:
        """Mostra detalhes completos de uma votação"""
        try:
            from ...utils.database import database

            # Buscar votos
            votes: list[dict[str, Any]] | None = await database.get_all(
                "SELECT option_index FROM poll_votes WHERE poll_id = ?", (poll["id"],)
            )

            votes = votes or []
            total_votes: int = len(votes)

            # Contar votos por opção
            vote_counts: dict[int, int] = {}
            for vote in votes:
                option_index: int = vote["option_index"]
                vote_counts[option_index] = vote_counts.get(option_index, 0) + 1

            # Processar opções
            try:
                options: list[dict[str, str]] = json.loads(poll["options"])
            except:
                options: list[dict[str, str]] = []

            # Embed detalhado
            detail_embed: discord.Embed = discord.Embed(
                title=f"🗳️ **{poll['question']}**",
                description=poll["description"] or "Sem descrição adicional",
                color={"active": 0x00FF00, "finished": 0xFF0000, "paused": 0xFFFF00}.get(
                    poll["status"], 0x2F3136
                ),
                timestamp=datetime.now(),
            )

            creator: discord.Member | None = interaction.guild.get_member(int(poll["user_id"]))
            creator_text: str = (
                creator.mention if creator else f"Usuário não encontrado (`{poll['user_id']}`)"
            )

            detail_embed.add_field(name="👤 Criador", value=creator_text, inline=True)

            channel: discord.TextChannel | None = interaction.guild.get_channel(
                int(poll["channel_id"])
            )
            channel_text: str = channel.mention if channel else "Canal não encontrado"

            detail_embed.add_field(name="📍 Canal", value=channel_text, inline=True)

            detail_embed.add_field(name="🆔 ID", value=f"`{poll['id']}`", inline=True)

            status_emojis: dict[str, str] = {
                "active": "🟢 Ativa",
                "finished": "🔴 Finalizada",
                "paused": "🟡 Pausada",
            }

            detail_embed.add_field(
                name="📊 Status",
                value=status_emojis.get(poll["status"], poll["status"].title()),
                inline=True,
            )

            created_time: datetime = datetime.fromisoformat(poll["created_at"])
            detail_embed.add_field(
                name="⏰ Criado", value=f"<t:{int(created_time.timestamp())}:F>", inline=True
            )

            # Tempo de fim
            if poll["end_time"]:
                end_time: datetime = datetime.fromisoformat(poll["end_time"])
                if datetime.now() < end_time and poll["status"] == "active":
                    detail_embed.add_field(
                        name="⏳ Termina", value=f"<t:{int(end_time.timestamp())}:R>", inline=True
                    )
                else:
                    detail_embed.add_field(
                        name="🔒 Terminou", value=f"<t:{int(end_time.timestamp())}:F>", inline=True
                    )
            else:
                detail_embed.add_field(name="⏳ Duração", value="Permanente", inline=True)

            # Resultados das opções
            if options:
                results_text: str = ""
                max_votes: int = max(vote_counts.values()) if vote_counts else 0

                for i, option in enumerate(options):
                    count: int = vote_counts.get(i, 0)
                    percentage: float = (count / total_votes * 100) if total_votes > 0 else 0

                    # Emoji de status
                    if count == max_votes and max_votes > 0:
                        status_emoji: str = "🏆"
                    elif count > 0:
                        status_emoji: str = "📊"
                    else:
                        status_emoji: str = "⚪"

                    results_text += f"{status_emoji} {option['emoji']} **{option['text']}**: {count} votos ({percentage:.1f}%)\n"

                detail_embed.add_field(
                    name="🗳️ Opções e Resultados", value=results_text, inline=False
                )

            detail_embed.add_field(
                name="📈 Estatísticas",
                value=f"**Total de votos:** {total_votes}\n**Opções disponíveis:** {len(options)}",
                inline=True,
            )

            # Link para mensagem original
            try:
                message_url: str = f"https://discord.com/channels/{poll['guild_id']}/{poll['channel_id']}/{poll['message_id']}"
                detail_embed.add_field(
                    name="🔗 Link", value=f"[Ver votação original]({message_url})", inline=True
                )
            except:
                pass

            detail_embed.set_footer(
                text=f"Votação {poll['id']} • Criada em {created_time.strftime('%d/%m/%Y')}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            if creator:
                detail_embed.set_thumbnail(url=creator.display_avatar.url)

            await interaction.followup.send(embed=detail_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro ao mostrar detalhes: {e}")


async def setup(bot: commands.Bot) -> None:
    """Carrega o cog"""
    await bot.add_cog(PollList(bot))
