"""
Sistema de Giveaway - Listar Sorteios
Lista todos os sorteios ativos e finalizados do servidor
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class GiveawayList(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(
        name="giveaway-list", description="📋 Lista todos os sorteios do servidor"
    )
    @app_commands.describe(
        status="Filtrar por status do sorteio", pagina="Página para visualizar (padrão: 1)"
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Todos", value="all"),
            app_commands.Choice(name="Ativos", value="active"),
            app_commands.Choice(name="Finalizados", value="ended"),
        ]
    )
    async def giveaway_list(
        self,
        interaction: discord.Interaction,
        status: str | None = "all",
        pagina: int | None = 1,
    ) -> None:
        try:
            await interaction.response.defer()

            # 🛡️ VERIFICAR PERMISSÕES
            if not interaction.user.guild_permissions.manage_events:  # type: ignore
                await interaction.followup.send(
                    "❌ Você não tem permissão para ver a lista de sorteios. **Necessário**: Gerenciar Eventos",
                    ephemeral=True,
                )
                return

            # 🛡️ VALIDAR PÁGINA
            page_num: int = max(pagina if pagina else 1, 1)
            page_num = min(page_num, 50)

            # 📊 BUSCAR GIVEAWAYS DO BANCO
            giveaways: list[dict[str, Any]] = []
            total_count: int = 0
            
            try:
                from ...utils.database import database

                # Construir query baseada no status
                query: str = "SELECT * FROM giveaways WHERE guild_id = ?"
                params: list[str] = [str(interaction.guild.id)]  # type: ignore

                if status == "active":
                    query += " AND ended = 0"
                elif status == "ended":
                    query += " AND ended = 1"

                query += " ORDER BY created_at DESC"

                # Paginação
                per_page: int = 10
                offset: int = (page_num - 1) * per_page
                query += f" LIMIT {per_page} OFFSET {offset}"

                giveaways = await database.get_all(query, tuple(params))

                # Contar total
                count_query: str = "SELECT COUNT(*) as count FROM giveaways WHERE guild_id = ?"
                count_params: list[str] = [str(interaction.guild.id)]  # type: ignore

                if status == "active":
                    count_query += " AND ended = 0"
                elif status == "ended":
                    count_query += " AND ended = 1"

                total_result: dict[str, Any] | None = await database.get(count_query, tuple(count_params))
                total_count = total_result["count"] if total_result else 0

            except Exception as e:
                print(f"❌ Erro ao buscar giveaways: {e}")
                giveaways = []
                total_count = 0

            # 📋 VERIFICAR SE HÁ GIVEAWAYS
            if not giveaways:
                embed: discord.Embed = discord.Embed(
                    title="📋 Lista de Sorteios",
                    description="❌ Nenhum sorteio encontrado neste servidor.",
                    color=0xFF9999,
                    timestamp=datetime.now(),
                )

                if status == "active":
                    embed.description = "❌ Não há sorteios ativos no momento."
                elif status == "ended":
                    embed.description = "❌ Não há sorteios finalizados."

                embed.add_field(
                    name="💡 Dica",
                    value="Use `/giveaway-start` para criar um novo sorteio!",
                    inline=False,
                )

                await interaction.followup.send(embed=embed)
                return

            # 🎨 CRIAR EMBED DA LISTA
            status_names: dict[str, str] = {
                "all": "Todos os Sorteios",
                "active": "Sorteios Ativos",
                "ended": "Sorteios Finalizados",
            }

            embed = discord.Embed(
                title=f"📋 {status_names.get(status if status else 'all', 'Sorteios')}",
                color=0x00FF88,
                timestamp=datetime.now(),
            )

            # 📝 ADICIONAR GIVEAWAYS À LISTA
            giveaway_list: str = ""

            for i, gw in enumerate(giveaways, 1):
                # Status emoji
                status_emoji: str = "🟢" if not gw.get("ended", 0) else "🔴"

                # Buscar host
                host: discord.Member | None = interaction.guild.get_member(int(gw["host_id"]))  # type: ignore
                host_name: str = host.display_name if host else "Usuário Desconhecido"

                # Formatar datas
                try:
                    created: datetime = datetime.fromisoformat(gw["created_at"])
                    created_str: str = f"<t:{int(created.timestamp())}:R>"
                except Exception:
                    created_str = "Data desconhecida"

                try:
                    end_time: datetime = datetime.fromisoformat(gw["end_time"])
                    end_str: str = f"<t:{int(end_time.timestamp())}:R>"
                except Exception:
                    end_str = "Data desconhecida"

                # Adicionar à lista
                position: int = (page_num - 1) * per_page + i
                giveaway_list += f"{status_emoji} **#{position}** {gw.get('title', 'Sorteio')}\n"
                giveaway_list += f"   └ **Por:** {host_name} • **Criado:** {created_str}\n"

                if not gw.get("ended", 0):
                    giveaway_list += f"   └ **Termina:** {end_str}\n"
                else:
                    giveaway_list += f"   └ **Terminou:** {end_str}\n"

                giveaway_list += f"   └ **Ganhadores:** {gw.get('winners', 1)} • **ID:** `{gw['message_id']}`\n\n"

            embed.description = giveaway_list

            # 📊 INFORMAÇÕES DA PÁGINA
            total_pages: int = (total_count + per_page - 1) // per_page

            embed.add_field(name="📄 Página", value=f"{page_num}/{total_pages}", inline=True)

            embed.add_field(
                name="📊 Total",
                value=f"{total_count} sorteio{'s' if total_count != 1 else ''}",
                inline=True,
            )

            embed.add_field(name="🎯 Filtro", value=status_names.get(status if status else "all", status if status else "all"), inline=True)

            # 🔍 ESTATÍSTICAS ADICIONAIS
            try:
                from ...utils.database import database
                
                stats: list[dict[str, Any]] = await database.get_all(
                    "SELECT ended, COUNT(*) as count FROM giveaways WHERE guild_id = ? GROUP BY ended",
                    (str(interaction.guild.id),),  # type: ignore
                )

                active_count: int = 0
                ended_count: int = 0

                for stat in stats:
                    if stat["ended"] == 0:
                        active_count = stat["count"]
                    else:
                        ended_count = stat["count"]

                embed.add_field(
                    name="📈 Estatísticas",
                    value=f"🟢 Ativos: {active_count}\n🔴 Finalizados: {ended_count}",
                    inline=True,
                )
            except Exception:
                pass

            # 🎨 VISUAL ENHANCEMENTS
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)  # type: ignore
            embed.set_footer(
                text=f"Use /giveaway-info <id> para detalhes • Página {page_num}/{total_pages}",
                icon_url=interaction.user.display_avatar.url,
            )

            # 🔘 CRIAR VIEW COM NAVEGAÇÃO
            if total_pages > 1:
                view: GiveawayListView = GiveawayListView(page_num, total_pages, status if status else "all", interaction.user.id)
                await interaction.followup.send(embed=embed, view=view)
            else:
                await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro no comando giveaway-list: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao listar sorteios. Tente novamente.", ephemeral=True
                )
            except Exception:
                pass


class GiveawayListView(discord.ui.View):
    def __init__(self, current_page: int, total_pages: int, status_filter: str, user_id: int) -> None:
        super().__init__(timeout=300)
        self.current_page: int = current_page
        self.total_pages: int = total_pages
        self.status_filter: str = status_filter
        self.user_id: int = user_id

        # Desabilitar botões se necessário
        if current_page <= 1:
            self.prev_page.disabled = True
        if current_page >= total_pages:
            self.next_page.disabled = True

    @discord.ui.button(label="◀️ Anterior", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.change_page(interaction, self.current_page - 1)

    @discord.ui.button(label="▶️ Próxima", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.change_page(interaction, self.current_page + 1)

    @discord.ui.button(label="🔄 Atualizar", style=discord.ButtonStyle.primary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.change_page(interaction, self.current_page)

    async def change_page(self, interaction: discord.Interaction, new_page: int) -> None:
        """Mudar página da lista"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Apenas quem solicitou pode navegar na lista!", ephemeral=True
            )
            return

        # Executar comando novamente
        cog: GiveawayList | None = interaction.client.get_cog("GiveawayList")  # type: ignore
        if cog:
            await interaction.response.defer()
            await cog.giveaway_list.callback(cog, interaction, self.status_filter, new_page)

    async def on_timeout(self) -> None:
        """Desabilitar botões ao expirar"""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


def setup(bot: commands.Bot) -> None:
    """Adiciona o cog ao bot"""
    bot.add_cog(GiveawayList(bot))
