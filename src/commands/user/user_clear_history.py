"""
Comando user clear-history - Limpar histórico de moderação
Convertido do arquivo user-clear-history.js
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import discord
from discord import app_commands
from discord.ext import commands

from ...utils.database import database

if TYPE_CHECKING:
    pass


def create_embed(title: str, description: str, color: int = 0x00FF00, **kwargs: Any) -> discord.Embed:
    """Função simples para criar embeds"""
    return discord.Embed(title=title, description=description, color=color)


class UserClearHistory(commands.Cog):
    """Sistema para limpar histórico de moderação"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(
        name="user-clear-history", description="Limpa o histórico de moderação de um usuário"
    )
    @app_commands.describe(
        user="Usuário para limpar o histórico",
        tipo="Tipo de histórico para limpar",
        confirmar="Digite 'CONFIRMAR' para executar a ação",
    )
    @app_commands.default_permissions(administrator=True)
    async def user_clear_history(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        tipo: Literal["todos", "casos", "avisos", "notas"] = "todos",
        confirmar: str | None = None,
    ) -> None:
        """Comando para limpar histórico de moderação"""

        # Verificar permissões
        if not interaction.user.guild_permissions.administrator:  # type: ignore
            await interaction.response.send_message(
                "❌ Apenas administradores podem limpar histórico de moderação.", ephemeral=True
            )
            return

        # Verificar confirmação
        if not confirmar or confirmar.upper() != "CONFIRMAR":
            embed: discord.Embed = create_embed(
                title="⚠️ Confirmação Necessária",
                description=f"Esta ação irá limpar **{tipo}** do histórico de moderação de {user.mention}.\n\n"
                "**Esta ação é IRREVERSÍVEL!**\n\n"
                "Para confirmar, execute o comando novamente com o parâmetro `confirmar: CONFIRMAR`",
                color=discord.Color.yellow(),
            )

            embed.add_field(
                name="📋 Tipos Disponíveis",
                value="• `todos` - Limpa tudo\n• `casos` - Apenas casos de moderação\n• `avisos` - Apenas avisos\n• `notas` - Apenas notas",
                inline=False,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            await interaction.response.defer(ephemeral=True)

            guild_id: str = str(interaction.guild.id)  # type: ignore
            user_id: str = str(user.id)
            deleted_count: int = 0

            # Executar limpeza baseada no tipo
            result: int | None
            if tipo == "todos" or tipo == "casos":
                result = await database.run(
                    "DELETE FROM mod_cases WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
                )
                deleted_count += result if result else 0

            if tipo == "todos" or tipo == "avisos":
                result = await database.run(
                    "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
                )
                deleted_count += result if result else 0

            if tipo == "todos" or tipo == "notas":
                result = await database.run(
                    "DELETE FROM user_notes WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
                )
                deleted_count += result if result else 0

            # Registrar a ação como um caso de moderação
            await database.run(
                """INSERT INTO mod_cases (guild_id, user_id, moderator_id, type, reason, created_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (
                    guild_id,
                    user_id,
                    str(interaction.user.id),
                    "clear_history",
                    f"Limpeza de histórico ({tipo}) por {interaction.user}",
                ),
            )

            embed_success: discord.Embed = create_embed(
                title="✅ Histórico Limpo",
                description="Histórico de moderação limpo com sucesso!",
                color=discord.Color.green(),
            )

            embed_success.add_field(name="👤 Usuário", value=user.mention, inline=True)
            embed_success.add_field(name="🗂️ Tipo", value=tipo.title(), inline=True)
            embed_success.add_field(name="📊 Registros Removidos", value=f"{deleted_count}", inline=True)
            embed_success.add_field(name="👮 Moderador", value=interaction.user.mention, inline=False)

            embed_success.set_footer(text="Esta ação foi registrada nos logs de moderação")

            await interaction.followup.send(embed=embed_success, ephemeral=True)

            # Log para canal de logs se configurado
            try:
                log_embed: discord.Embed = create_embed(
                    title="🧹 Histórico de Moderação Limpo",
                    description=f"**Usuário:** {user.mention} ({user.id})\n"
                    f"**Tipo:** {tipo}\n"
                    f"**Registros removidos:** {deleted_count}\n"
                    f"**Moderador:** {interaction.user.mention}",
                    color=discord.Color.orange(),
                )

                # Tentar enviar para canal de logs
                # (implementar busca por canal de logs configurado)

            except Exception as e:
                print(f"Erro enviando log: {e}")

        except Exception as e:
            print(f"❌ Erro no comando user-clear-history: {e}")
            await interaction.followup.send(
                "❌ Erro ao limpar histórico de moderação.", ephemeral=True
            )


def setup(bot: commands.Bot) -> None:
    """Adiciona o cog ao bot"""
    bot.add_cog(UserClearHistory(bot))
