"""
Comando user nick - Moderar nickname de usuários
Convertido do arquivo user-nick.js
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


def create_embed(title: str, description: str, color: int = 0x00FF00, **kwargs: Any) -> discord.Embed:
    """Função simples para criar embeds"""
    return discord.Embed(title=title, description=description, color=color)


class UserNick(commands.Cog):
    """Sistema de moderação de nicknames"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(name="user-nick", description="Modera o nickname de um usuário")
    @app_commands.describe(
        user="Usuário para alterar nickname", nickname="Novo nickname para o usuário"
    )
    @app_commands.default_permissions(manage_nicknames=True)
    async def user_nick(
        self, interaction: discord.Interaction, user: discord.Member, nickname: str
    ) -> None:
        """Comando para alterar nickname de usuário"""

        # Verificar permissões
        if not interaction.user.guild_permissions.manage_nicknames:  # type: ignore
            await interaction.response.send_message(
                "❌ Você não tem permissão para alterar nicknames.", ephemeral=True
            )
            return

        # Verificar se o bot tem permissão
        if not interaction.guild.me.guild_permissions.manage_nicknames:  # type: ignore
            await interaction.response.send_message(
                "❌ Eu não tenho permissão para alterar nicknames.", ephemeral=True
            )
            return

        # Verificar hierarquia de cargos
        if (
            user.top_role >= interaction.user.top_role  # type: ignore
            and interaction.user != interaction.guild.owner  # type: ignore
        ):
            await interaction.response.send_message(
                "❌ Você não pode alterar o nickname de alguém com cargo igual ou superior ao seu.",
                ephemeral=True,
            )
            return

        if user.top_role >= interaction.guild.me.top_role:  # type: ignore
            await interaction.response.send_message(
                "❌ Não posso alterar o nickname de alguém com cargo igual ou superior ao meu.",
                ephemeral=True,
            )
            return

        # Verificar se não está tentando alterar o dono
        if user == interaction.guild.owner:  # type: ignore
            await interaction.response.send_message(
                "❌ Não posso alterar o nickname do dono do servidor.", ephemeral=True
            )
            return

        try:
            old_nick: str | None = user.display_name
            await user.edit(nick=nickname, reason=f"Alterado por {interaction.user}")

            embed: discord.Embed = create_embed(
                title="✅ Nickname Alterado",
                description=f"Nickname de {user.mention} alterado com sucesso!",
                color=discord.Color.green(),
            )
            embed.add_field(name="👤 Usuário", value=user.mention, inline=True)
            embed.add_field(name="📝 Nickname Anterior", value=old_nick or "Nenhum", inline=True)
            embed.add_field(name="✨ Novo Nickname", value=nickname, inline=True)
            embed.add_field(name="👮 Moderador", value=interaction.user.mention, inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para alterar o nickname deste usuário.", ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"❌ Erro ao alterar nickname: {e!s}", ephemeral=True
            )
        except Exception as e:
            print(f"❌ Erro no comando user-nick: {e}")
            await interaction.response.send_message(
                "❌ Erro interno ao alterar nickname.", ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UserNick(bot))
