"""
Comando user history - Ver histórico de moderação de usuário
Convertido do arquivo user-history.js
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

from ...utils.database import database

if TYPE_CHECKING:
    pass


def create_embed(title: str, description: str, color: int = 0x00FF00, **kwargs: Any) -> discord.Embed:
    """Função simples para criar embeds"""
    return discord.Embed(title=title, description=description, color=color)


class UserHistory(commands.Cog):
    """Sistema de histórico de moderação"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(
        name="user-history", description="Mostra o histórico de moderação de um usuário"
    )
    @app_commands.describe(
        user="Usuário para ver o histórico", limite="Quantos registros mostrar (padrão: 10)"
    )
    @app_commands.default_permissions(moderate_members=True)
    async def user_history(
        self, interaction: discord.Interaction, user: discord.Member, limite: int = 10
    ) -> None:
        """Comando para ver histórico de moderação"""

        # Verificar permissões
        if not interaction.user.guild_permissions.moderate_members:  # type: ignore
            await interaction.response.send_message(
                "❌ Você não tem permissão para ver histórico de moderação.", ephemeral=True
            )
            return

        if limite > 50:
            limite = 50
        elif limite < 1:
            limite = 10

        try:
            await interaction.response.defer(ephemeral=True)

            # Buscar casos de moderação
            mod_cases: list[dict[str, Any]] = await database.get_all(
                """SELECT * FROM mod_cases 
                   WHERE guild_id = ? AND user_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (str(interaction.guild.id), str(user.id), limite),
            )

            # Buscar avisos
            warnings: list[dict[str, Any]] = await database.get_all(
                """SELECT * FROM warnings 
                   WHERE guild_id = ? AND user_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (str(interaction.guild.id), str(user.id), limite),
            )

            # Buscar notas
            notes: list[dict[str, Any]] = await database.get_all(
                """SELECT * FROM user_notes 
                   WHERE guild_id = ? AND user_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (str(interaction.guild.id), str(user.id), limite),
            )

            embed: discord.Embed = create_embed(
                title=f"📋 Histórico de Moderação - {user.display_name}",
                description=f"Últimos {limite} registros de moderação",
                color=discord.Color.orange(),
            )

            embed.set_thumbnail(url=user.display_avatar.url)

            # Adicionar estatísticas
            total_cases: int = len(mod_cases)
            total_warnings: int = len(warnings)
            total_notes: int = len(notes)

            embed.add_field(
                name="📊 Resumo",
                value=f"**Casos:** {total_cases}\n**Avisos:** {total_warnings}\n**Notas:** {total_notes}",
                inline=True,
            )

            # Mostrar casos de moderação
            if mod_cases:
                case_text: str = ""
                for case in mod_cases[:5]:  # Mostrar apenas os 5 mais recentes
                    case_type: str = case.get("type", "Desconhecido")
                    reason: str = case.get("reason", "Sem motivo")
                    created: str = case.get("created_at", "")
                    moderator_id: str | None = case.get("moderator_id")

                    # Formatação da data
                    date_str: str
                    try:
                        if created:
                            date_obj: datetime = datetime.fromisoformat(created.replace("Z", "+00:00"))
                            date_str = date_obj.strftime("%d/%m/%Y %H:%M")
                        else:
                            date_str = "Data desconhecida"
                    except Exception:
                        date_str = "Data inválida"

                    case_text += f"• **{case_type}** - {date_str}\n"
                    case_text += f"  *{reason[:50]}{'...' if len(reason) > 50 else ''}*\n\n"

                if case_text:
                    embed.add_field(
                        name="⚖️ Casos Recentes",
                        value=case_text[:1000] or "Nenhum caso encontrado",
                        inline=False,
                    )

            # Mostrar avisos recentes
            if warnings:
                warning_text: str = ""
                for warning in warnings[:3]:  # Mostrar apenas os 3 mais recentes
                    reason_warn: str = warning.get("reason", "Sem motivo")
                    created_warn: str = warning.get("created_at", "")

                    date_str_warn: str
                    try:
                        if created_warn:
                            date_obj_warn: datetime = datetime.fromisoformat(created_warn.replace("Z", "+00:00"))
                            date_str_warn = date_obj_warn.strftime("%d/%m/%Y %H:%M")
                        else:
                            date_str_warn = "Data desconhecida"
                    except Exception:
                        date_str_warn = "Data inválida"

                    warning_text += f"• {date_str_warn}\n"
                    warning_text += f"  *{reason_warn[:50]}{'...' if len(reason_warn) > 50 else ''}*\n\n"

                if warning_text:
                    embed.add_field(
                        name="⚠️ Avisos Recentes",
                        value=warning_text[:1000] or "Nenhum aviso encontrado",
                        inline=False,
                    )

            # Mostrar notas recentes
            if notes:
                note_text: str = ""
                for note in notes[:3]:  # Mostrar apenas as 3 mais recentes
                    content: str = note.get("note", "Sem conteúdo")
                    created_at: str = note.get("created_at", "")

                    date_str: str
                    try:
                        if created_at:
                            date_obj: datetime = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                            date_str = date_obj.strftime("%d/%m/%Y %H:%M")
                        else:
                            date_str = "Data desconhecida"
                    except Exception:
                        date_str = "Data inválida"

                    note_text += f"• {date_str}\n"
                    note_text += f"  *{content[:50]}{'...' if len(content) > 50 else ''}*\n\n"

                if note_text:
                    embed.add_field(
                        name="📝 Notas Recentes",
                        value=note_text[:1000] or "Nenhuma nota encontrada",
                        inline=False,
                    )

            # Se não há dados
            if not mod_cases and not warnings and not notes:
                embed.add_field(
                    name="📭 Histórico Limpo",
                    value="Este usuário não possui registros de moderação.",
                    inline=False,
                )

            embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando user-history: {e}")
            await interaction.followup.send(
                "❌ Erro ao buscar histórico de moderação.", ephemeral=True
            )


def setup(bot: commands.Bot) -> None:
    """Adiciona o cog ao bot"""
    bot.add_cog(UserHistory(bot))

            # Se não há dados
            if not mod_cases and not warnings and not notes:
                embed.add_field(
                    name="📭 Histórico Limpo",
                    value="Este usuário não possui registros de moderação.",
                    inline=False,
                )

            embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando user-history: {e}")
            await interaction.followup.send(
                "❌ Erro ao buscar histórico de moderação.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(UserHistory(bot))
