"""
Sistema de Leaderboard - Rankings de XP
Mostra o ranking dos usuários com mais XP no servidor
"""

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="🏆 Mostra o ranking de XP do servidor")
    @app_commands.describe(
        pagina="Página do ranking para visualizar (padrão: 1)", tipo="Tipo de ranking a mostrar"
    )
    @app_commands.choices(
        tipo=[
            app_commands.Choice(name="XP Total", value="xp"),
            app_commands.Choice(name="Level", value="level"),
            app_commands.Choice(name="Mensagens", value="messages"),
            app_commands.Choice(name="XP Hoje", value="daily"),
        ]
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        pagina: int | None = 1,
        tipo: str | None = "xp",
    ):
        try:
            await interaction.response.defer()

            # 🛡️ VALIDAÇÕES
            pagina = max(pagina, 1)
            if pagina > 50:  # Limite máximo
                pagina = 50

            # 📊 BUSCAR DADOS DO RANKING
            try:
                from ...utils.database import database

                # Determinar query baseada no tipo
                order_by = "xp DESC"
                if tipo == "level":
                    order_by = "level DESC, xp DESC"
                elif tipo == "messages":
                    order_by = "messages DESC"
                elif tipo == "daily":
                    order_by = "xp DESC"  # Implementar XP diário depois

                # Calcular offset
                per_page = 10
                offset = (pagina - 1) * per_page

                # Buscar dados
                leaderboard_data = await database.get_all(
                    f"SELECT * FROM user_levels WHERE guild_id = ? ORDER BY {order_by} LIMIT ? OFFSET ?",
                    (str(interaction.guild.id), per_page, offset),
                )

                # Contar total de usuários
                total_users = await database.get(
                    "SELECT COUNT(*) as count FROM user_levels WHERE guild_id = ?",
                    (str(interaction.guild.id),),
                )
                total_count = total_users["count"] if total_users else 0

            except Exception as e:
                print(f"Erro no banco: {e}")
                leaderboard_data = []
                total_count = 0

            if not leaderboard_data:
                embed = discord.Embed(
                    title="❌ Leaderboard Vazio",
                    description="Ainda não há dados de level neste servidor.\n\n"
                    "💡 **Dica**: Envie mensagens para começar a ganhar XP!",
                    color=0xFF9999,
                    timestamp=datetime.now(),
                )
                await interaction.followup.send(embed=embed)
                return

            # 🎨 CRIAR EMBED DO LEADERBOARD
            embed = discord.Embed(
                title=f"🏆 Leaderboard - {self.get_type_name(tipo)}",
                color=0xFFD700,
                timestamp=datetime.now(),
            )

            # 📋 CRIAR LISTA DE USUÁRIOS
            leaderboard_text = ""

            for i, user_data in enumerate(leaderboard_data):
                position = offset + i + 1
                user_id = int(user_data["user_id"])

                # Buscar usuário
                user = interaction.guild.get_member(user_id)
                if not user:
                    try:
                        user = await interaction.guild.fetch_member(user_id)
                    except:
                        continue

                # 🏅 MEDAL/EMOJI POR POSIÇÃO
                if position == 1:
                    medal = "🥇"
                elif position == 2:
                    medal = "🥈"
                elif position == 3:
                    medal = "🥉"
                elif position <= 10:
                    medal = "🏆"
                else:
                    medal = "📊"

                # 📈 DADOS BASEADOS NO TIPO
                if tipo == "level":
                    value = f"Level {user_data['level']} ({user_data['xp']:,} XP)"
                elif tipo == "messages":
                    value = f"{user_data['messages']:,} mensagens"
                elif tipo == "daily":
                    value = f"{user_data['xp']:,} XP (hoje)"  # Implementar XP diário depois
                else:  # xp
                    value = f"{user_data['xp']:,} XP (Lv.{user_data['level']})"

                # 🔍 DESTACAR USUÁRIO ATUAL
                if user.id == interaction.user.id:
                    leaderboard_text += f"{medal} **#{position} {user.display_name}** ⭐\n"
                    leaderboard_text += f"   └ **{value}**\n\n"
                else:
                    leaderboard_text += f"{medal} **#{position}** {user.display_name}\n"
                    leaderboard_text += f"   └ {value}\n\n"

            embed.description = leaderboard_text

            # 📊 INFORMAÇÕES DA PÁGINA
            total_pages = (total_count + per_page - 1) // per_page

            embed.add_field(name="📄 Página", value=f"{pagina}/{total_pages}", inline=True)

            embed.add_field(name="👥 Total de Usuários", value=f"{total_count:,}", inline=True)

            embed.add_field(name="🎯 Tipo", value=self.get_type_name(tipo), inline=True)

            # 🔍 BUSCAR POSIÇÃO DO USUÁRIO ATUAL
            try:
                user_position = await database.get(
                    "SELECT COUNT(*) + 1 as position FROM user_levels WHERE guild_id = ? AND xp > (SELECT xp FROM user_levels WHERE guild_id = ? AND user_id = ?)",
                    (
                        str(interaction.guild.id),
                        str(interaction.guild.id),
                        str(interaction.user.id),
                    ),
                )

                if user_position:
                    embed.add_field(
                        name="📍 Sua Posição", value=f"#{user_position['position']}", inline=True
                    )
            except:
                pass

            # 🎨 VISUAL ENHANCEMENTS
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
            embed.set_footer(
                text=f"Servidor: {interaction.guild.name} • Use /level para detalhes",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            # 🔘 CRIAR VIEW COM NAVEGAÇÃO
            view = LeaderboardView(
                pagina, total_pages, tipo, interaction.guild.id, interaction.user.id
            )

            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            print(f"❌ Erro no comando leaderboard: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao carregar leaderboard. Tente novamente.", ephemeral=True
                )
            except:
                pass

    def get_type_name(self, tipo: str) -> str:
        """Retorna nome amigável do tipo"""
        types = {"xp": "XP Total", "level": "Níveis", "messages": "Mensagens", "daily": "XP Diário"}
        return types.get(tipo, "XP Total")


class LeaderboardView(discord.ui.View):
    def __init__(
        self, current_page: int, total_pages: int, ranking_type: str, guild_id: int, user_id: int
    ):
        super().__init__(timeout=300)
        self.current_page = current_page
        self.total_pages = total_pages
        self.ranking_type = ranking_type
        self.guild_id = guild_id
        self.user_id = user_id

        # Desabilitar botões se necessário
        if current_page <= 1:
            self.first_page.disabled = True
            self.prev_page.disabled = True
        if current_page >= total_pages:
            self.next_page.disabled = True
            self.last_page.disabled = True

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_page(interaction, 1)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_page(interaction, self.current_page - 1)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_page(interaction, self.current_page + 1)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_page(interaction, self.total_pages)

    @discord.ui.button(label="🔄 Atualizar", style=discord.ButtonStyle.primary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_page(interaction, self.current_page)

    async def update_page(self, interaction: discord.Interaction, new_page: int):
        """Atualizar página do leaderboard"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Apenas quem solicitou pode navegar no leaderboard!", ephemeral=True
            )
            return

        # Executar comando leaderboard novamente com nova página
        cog = interaction.client.get_cog("Leaderboard")
        if cog:
            await interaction.response.defer()
            await cog.leaderboard.callback(cog, interaction, new_page, self.ranking_type)
        else:
            await interaction.response.send_message(
                "❌ Erro ao atualizar leaderboard.", ephemeral=True
            )

    async def on_timeout(self):
        """Desabilitar botões ao expirar"""
        for item in self.children:
            item.disabled = True


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
