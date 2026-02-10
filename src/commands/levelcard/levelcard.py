"""
Comando levelcard - Mostra card de nível detalhado
Convertido do arquivo levelcard.js
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

import discord
from discord import app_commands
from discord.ext import commands

from ...utils.database import database

if TYPE_CHECKING:
    from ...main import ModularBot

# from ...utils.embeds import create_embed  # Temporariamente desabilitado


def create_embed(title: str, description: str, color: int = 0x00FF00, **kwargs: Any) -> discord.Embed:
    """Função simples para criar embeds"""
    return discord.Embed(title=title, description=description, color=color)


class LevelCard(commands.Cog):
    """Sistema de levelcard para mostrar dados de XP/nível"""

    def __init__(self, bot: ModularBot) -> None:
        self.bot: ModularBot = bot

    @app_commands.command(
        name="levelcard", description="Mostra o card de nível detalhado do usuário"
    )
    @app_commands.describe(
        usuario="Usuário para ver o card (padrão: você)", estilo="Estilo do card"
    )
    async def levelcard(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member | None = None,
        estilo: Literal["full", "simple", "stats"] = "full",
    ) -> None:
        """Comando para mostrar levelcard detalhado"""

        target_user: discord.Member = usuario or interaction.user  # type: ignore

        try:
            await interaction.response.defer()

            # Buscar dados do usuário no banco
            user_data: dict[str, Any] | None = await database.get(
                "SELECT * FROM user_levels WHERE guild_id = ? AND user_id = ?",
                (str(interaction.guild.id), str(target_user.id)),
            )

            if not user_data:
                # Se usuário não tem dados, criar registro básico
                user_data = {
                    "xp": 0,
                    "level": 0,
                    "messages": 0,
                    "last_xp_time": datetime.now().isoformat(),
                }

            # Calcular estatísticas
            current_level: int = user_data.get("level", 0)
            current_xp: int = user_data.get("xp", 0)
            messages: int = user_data.get("messages", 0)

            # XP necessário para próximo nível
            xp_needed_for_next: int = self.calculate_xp_for_level(current_level + 1)
            xp_needed_for_current: int = self.calculate_xp_for_level(current_level)
            xp_progress: int = current_xp - xp_needed_for_current
            xp_required: int = xp_needed_for_next - xp_needed_for_current

            # Buscar posição no ranking
            ranking: dict[str, Any] | None = await database.get(
                """SELECT COUNT(*) + 1 as rank FROM user_levels 
                   WHERE guild_id = ? AND (
                       level > ? OR 
                       (level = ? AND xp > ?)
                   )""",
                (str(interaction.guild.id), current_level, current_level, current_xp),
            )

            rank: int | str = ranking.get("rank", "?") if ranking else "?"

            # Criar embed baseado no estilo
            embed: discord.Embed
            if estilo == "simple":
                embed = await self.create_simple_card(target_user, user_data, rank)
            elif estilo == "stats":
                embed = await self.create_stats_card(target_user, user_data, rank)
            else:  # full
                embed = await self.create_full_card(
                    target_user, user_data, rank, xp_progress, xp_required, messages
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro no comando levelcard: {e}")
            await interaction.followup.send(
                "❌ Erro ao gerar levelcard. Tente novamente.", ephemeral=True
            )

    def calculate_xp_for_level(self, level: int) -> int:
        """Calcular XP necessário para um nível específico"""
        if level <= 0:
            return 0
        return int(5 * (level**2) + 50 * level + 100)

    async def create_simple_card(self, user: discord.Member, data: dict[str, Any], rank: int | str) -> discord.Embed:
        """Criar card simples"""
        embed: discord.Embed = create_embed(
            title=f"📊 Nível de {user.display_name}",
            description=f"**Nível:** {data.get('level', 0)}\n**XP:** {data.get('xp', 0):,}\n**Rank:** #{rank}",
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    async def create_stats_card(self, user: discord.Member, data: dict[str, Any], rank: int | str) -> discord.Embed:
        """Criar card de estatísticas"""
        level: int = data.get("level", 0)
        xp: int = data.get("xp", 0)
        messages: int = data.get("messages", 0)

        embed: discord.Embed = create_embed(
            title=f"📈 Estatísticas de {user.display_name}", color=discord.Color.green()
        )

        embed.add_field(name="📊 Nível", value=f"`{level}`", inline=True)
        embed.add_field(name="✨ XP Total", value=f"`{xp:,}`", inline=True)
        embed.add_field(name="🏆 Ranking", value=f"`#{rank}`", inline=True)
        embed.add_field(name="💬 Mensagens", value=f"`{messages:,}`", inline=True)

        if messages > 0:
            xp_per_msg: float = round(xp / messages, 2)
            embed.add_field(name="📊 XP/Mensagem", value=f"`{xp_per_msg}`", inline=True)

        embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    async def create_full_card(
        self,
        user: discord.Member,
        data: dict[str, Any],
        rank: int | str,
        xp_progress: int,
        xp_required: int,
        messages: int,
    ) -> discord.Embed:
        """Criar card completo"""
        level: int = data.get("level", 0)
        xp: int = data.get("xp", 0)

        # Calcular progresso em porcentagem
        progress_percent: float = (xp_progress / xp_required * 100) if xp_required > 0 else 0

        # Barra de progresso visual
        progress_bar: str = self.create_progress_bar(progress_percent)

        embed: discord.Embed = create_embed(
            title=f"🎯 Levelcard Completo - {user.display_name}", color=discord.Color.gold()
        )

        # Informações principais
        embed.add_field(name="📊 Nível Atual", value=f"```\nNível {level}\n```", inline=True)
        embed.add_field(name="✨ XP Total", value=f"```\n{xp:,} XP\n```", inline=True)
        embed.add_field(name="🏆 Ranking", value=f"```\n#{rank}\n```", inline=True)

        # Progresso para próximo nível
        embed.add_field(
            name="📈 Progresso para Nível " + str(level + 1),
            value=f"{progress_bar}\n`{xp_progress:,}/{xp_required:,} XP ({progress_percent:.1f}%)`",
            inline=False,
        )

        # Estatísticas adicionais
        embed.add_field(name="💬 Mensagens", value=f"`{messages:,}`", inline=True)

        if messages > 0:
            xp_per_msg: float = round(xp / messages, 2)
            embed.add_field(name="📊 XP/Msg", value=f"`{xp_per_msg}`", inline=True)

        # XP restante para próximo nível
        xp_remaining: int = xp_required - xp_progress
        embed.add_field(name="🎯 XP Restante", value=f"`{xp_remaining:,}`", inline=True)

        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Sistema de Leveling")

        return embed

    def create_progress_bar(self, percent: float, length: int = 20) -> str:
        """Criar barra de progresso visual"""
        filled: int = int(length * percent / 100)
        empty: int = length - filled

        bar: str = "▰" * filled + "▱" * empty
        return f"[{bar}]"


async def setup(bot: ModularBot) -> None:
    await bot.add_cog(LevelCard(bot))
