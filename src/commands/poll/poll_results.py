"""
Sistema de Poll - Resultados e Gerenciamento
Comandos para ver resultados e gerenciar votações
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class PollResults(commands.Cog):
    """Sistema de resultados e gerenciamento de enquetes"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(
        name="poll-results", description="📊 Ver resultados detalhados de uma votação"
    )
    @app_commands.describe(poll_id="ID da votação para ver resultados")
    async def poll_results(self, interaction: discord.Interaction, poll_id: str) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # Buscar poll no banco
            try:
                from ...utils.database import database

                poll: dict[str, Any] | None = await database.get(
                    "SELECT * FROM polls WHERE id = ? AND guild_id = ?",
                    (poll_id, str(interaction.guild.id)),
                )

                if not poll:
                    await interaction.followup.send(
                        f"❌ **Votação não encontrada!**\n"
                        f"ID buscado: `{poll_id}`\n\n"
                        f"💡 Use `/poll-list` para ver suas votações",
                        ephemeral=True,
                    )
                    return

            except Exception as e:
                print(f"❌ Erro ao buscar poll: {e}")
                await interaction.followup.send(
                    "❌ Erro ao buscar votação no banco de dados.", ephemeral=True
                )
                return

            # Buscar votos
            try:
                votes: list[dict[str, Any]] | None = await database.get_all(
                    "SELECT option_index, user_id, voted_at FROM poll_votes WHERE poll_id = ?",
                    (poll_id,),
                )
            except Exception as e:
                print(f"❌ Erro ao buscar votos: {e}")
                votes = None

            votes = votes or []

            # Processar opções
            try:
                options: list[dict[str, str]] = json.loads(poll["options"])
            except:
                options: list[dict[str, str]] = []

            total_votes: int = len(votes)

            # Contar votos por opção
            vote_counts: dict[int, int] = {}
            voters_by_option: dict[int, list[str]] = {}

            for vote in votes:
                option_index: int = vote["option_index"]
                vote_counts[option_index] = vote_counts.get(option_index, 0) + 1

                if option_index not in voters_by_option:
                    voters_by_option[option_index] = []
                voters_by_option[option_index].append(vote["user_id"])

            # Criar embed de resultados
            results_embed: discord.Embed = discord.Embed(
                title="📊 **RESULTADOS DA VOTAÇÃO**",
                description=f"**Pergunta:** {poll['question']}",
                color=0x2F3136 if poll["status"] == "active" else 0xFF6B6B,
                timestamp=datetime.now(),
            )

            if poll["description"]:
                results_embed.add_field(
                    name="📝 Descrição", value=poll["description"], inline=False
                )

            # Resultados detalhados por opção
            results_text: str = ""

            # Encontrar opção vencedora
            max_votes: int = max(vote_counts.values()) if vote_counts else 0
            winners: list[int] = (
                [i for i, count in vote_counts.items() if count == max_votes]
                if max_votes > 0
                else []
            )

            for i, option in enumerate(options):
                count: int = vote_counts.get(i, 0)
                percentage: float = (count / total_votes * 100) if total_votes > 0 else 0

                # Emoji de status
                if i in winners and max_votes > 0:
                    status_emoji: str = "🏆"  # Vencedor
                elif count > 0:
                    status_emoji: str = "📊"  # Tem votos
                else:
                    status_emoji: str = "⚪"  # Sem votos

                # Barra de progresso visual
                bar_length: int = 15
                filled_bars: int = int(percentage / (100 / bar_length)) if percentage > 0 else 0
                progress_bar: str = "█" * filled_bars + "░" * (bar_length - filled_bars)

                results_text += f"{status_emoji} {option['emoji']} **{option['text']}**\n"
                results_text += f"`{progress_bar}` **{count}** votos (**{percentage:.1f}%**)\n"

                # Mostrar alguns eleitores (se não for muitos)
                if count > 0 and count <= 10:
                    voters: list[str] = [
                        f"<@{user_id}>" for user_id in voters_by_option.get(i, [])
                    ]
                    results_text += f"👥 {', '.join(voters)}\n"
                elif count > 10:
                    results_text += f"👥 {count} eleitores (muitos para listar)\n"

                results_text += "\n"

            results_embed.add_field(
                name="🗳️ Resultados Detalhados", value=results_text, inline=False
            )

            # Estatísticas gerais
            stats_text: str = f"**Total de votos:** {total_votes}\n"
            stats_text += f"**Opções:** {len(options)}\n"

            if winners and max_votes > 0:
                if len(winners) == 1:
                    winner_option: dict[str, str] = options[winners[0]]
                    stats_text += f"**🏆 Vencedor:** {winner_option['emoji']} {winner_option['text']} ({max_votes} votos)\n"
                else:
                    stats_text += (
                        f"**🤝 Empate:** {len(winners)} opções empatadas ({max_votes} votos cada)\n"
                    )
            else:
                stats_text += "**🏆 Vencedor:** Nenhum voto ainda\n"

            stats_text += (
                f"**Status:** {'🟢 Ativa' if poll['status'] == 'active' else '🔴 Finalizada'}"
            )

            results_embed.add_field(name="📈 Estatísticas", value=stats_text, inline=True)

            # Informações temporais
            created_time: datetime = datetime.fromisoformat(poll["created_at"])
            time_text: str = f"**Criada:** <t:{int(created_time.timestamp())}:F>\n"

            if poll["end_time"]:
                end_time: datetime = datetime.fromisoformat(poll["end_time"])
                if datetime.now() < end_time and poll["status"] == "active":
                    time_text += f"**Termina:** <t:{int(end_time.timestamp())}:R>"
                else:
                    time_text += f"**Terminou:** <t:{int(end_time.timestamp())}:F>"
            else:
                time_text += "**Duração:** Permanente"

            results_embed.add_field(name="⏰ Tempo", value=time_text, inline=True)

            # Criador
            creator: discord.Member | None = interaction.guild.get_member(int(poll["user_id"]))
            creator_text: str = (
                creator.mention if creator else f"Usuário não encontrado (`{poll['user_id']}`)"
            )

            results_embed.add_field(name="👤 Criador", value=creator_text, inline=True)

            # Link para mensagem original
            try:
                channel: discord.TextChannel | None = interaction.guild.get_channel(
                    int(poll["channel_id"])
                )
                message_url: str = f"https://discord.com/channels/{poll['guild_id']}/{poll['channel_id']}/{poll['message_id']}"

                results_embed.add_field(
                    name="🔗 Links",
                    value=f"[Ver votação original]({message_url})\n"
                    f"Canal: {channel.mention if channel else 'Canal não encontrado'}",
                    inline=False,
                )
            except:
                pass

            results_embed.set_footer(
                text=f"Poll ID: {poll_id} • Resultados atualizados em tempo real",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            if creator:
                results_embed.set_thumbnail(url=creator.display_avatar.url)

            await interaction.followup.send(embed=results_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando poll-results: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao buscar resultados. Tente novamente.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="poll-end", description="🔒 Finalizar uma votação")
    @app_commands.describe(poll_id="ID da votação para finalizar")
    async def poll_end(self, interaction: discord.Interaction, poll_id: str) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # Buscar poll no banco
            try:
                from ...utils.database import database

                poll: dict[str, Any] | None = await database.get(
                    "SELECT * FROM polls WHERE id = ? AND guild_id = ?",
                    (poll_id, str(interaction.guild.id)),
                )

                if not poll:
                    await interaction.followup.send(
                        f"❌ **Votação não encontrada!**\nID: `{poll_id}`", ephemeral=True
                    )
                    return

            except Exception as e:
                print(f"❌ Erro ao buscar poll: {e}")
                await interaction.followup.send("❌ Erro ao buscar votação.", ephemeral=True)
                return

            # Verificar permissões
            is_creator: bool = poll["user_id"] == str(interaction.user.id)
            is_admin: bool = interaction.user.guild_permissions.manage_guild

            if not (is_creator or is_admin):
                await interaction.followup.send(
                    "❌ **Sem permissão!**\n"
                    "Apenas o criador da votação ou administradores podem finalizá-la.",
                    ephemeral=True,
                )
                return

            # Verificar se já foi finalizada
            if poll["status"] != "active":
                await interaction.followup.send(
                    "ℹ️ **Esta votação já foi finalizada!**\n"
                    f"Use `/poll-results {poll_id}` para ver os resultados.",
                    ephemeral=True,
                )
                return

            # Finalizar votação
            try:
                await database.execute(
                    "UPDATE polls SET status = 'finished' WHERE id = ?", (poll_id,)
                )
            except Exception as e:
                print(f"❌ Erro ao finalizar poll: {e}")
                await interaction.followup.send(
                    "❌ Erro ao finalizar votação no banco de dados.", ephemeral=True
                )
                return

            # Atualizar mensagem original
            try:
                channel: discord.TextChannel | None = interaction.guild.get_channel(
                    int(poll["channel_id"])
                )
                message: discord.Message = await channel.fetch_message(int(poll["message_id"]))

                if message.embeds:
                    embed: discord.Embed = message.embeds[0]
                    embed.color = 0xFF6B6B
                    embed.title = f"🔒 **{poll['question']}** (FINALIZADA)"

                    # Atualizar status
                    for i, field in enumerate(embed.fields):
                        if "Estatísticas" in field.name:
                            old_value: str = field.value
                            new_value: str = old_value.replace("🟢 Ativo", "🔴 Finalizada")
                            embed.set_field_at(
                                i, name=field.name, value=new_value, inline=field.inline
                            )
                            break

                    embed.set_footer(
                        text=f"Poll ID: {poll_id} • Finalizada por {interaction.user}",
                        icon_url=embed.footer.icon_url,
                    )

                    await message.edit(embed=embed, view=None)

            except Exception as e:
                print(f"❌ Erro ao atualizar mensagem: {e}")

            # Buscar resultados finais
            try:
                votes: list[dict[str, Any]] | None = await database.get_all(
                    "SELECT option_index FROM poll_votes WHERE poll_id = ?", (poll_id,)
                )

                votes = votes or []
                options: list[dict[str, str]] = json.loads(poll["options"])
                total_votes: int = len(votes)

                # Contar votos
                vote_counts: dict[int, int] = {}
                for vote in votes:
                    option_index: int = vote["option_index"]
                    vote_counts[option_index] = vote_counts.get(option_index, 0) + 1

                # Encontrar vencedor
                max_votes: int = max(vote_counts.values()) if vote_counts else 0
                winners: list[int] = (
                    [i for i, count in vote_counts.items() if count == max_votes]
                    if max_votes > 0
                    else []
                )

            except Exception as e:
                print(f"❌ Erro ao calcular resultados: {e}")
                winners: list[int] = []
                total_votes: int = 0
                max_votes: int = 0

            # Embed de confirmação
            end_embed: discord.Embed = discord.Embed(
                title="🔒 **Votação Finalizada!**",
                description=f'A votação "{poll["question"]}" foi finalizada.',
                color=0xFF6B6B,
                timestamp=datetime.now(),
            )

            end_embed.add_field(
                name="📊 Resultado Final", value=f"**Total de votos:** {total_votes}", inline=True
            )

            if winners and max_votes > 0:
                if len(winners) == 1:
                    winner_option: dict[str, str] = options[winners[0]]
                    end_embed.add_field(
                        name="🏆 Vencedor",
                        value=f"{winner_option['emoji']} **{winner_option['text']}**\n{max_votes} votos",
                        inline=True,
                    )
                else:
                    end_embed.add_field(
                        name="🤝 Resultado",
                        value=f"Empate entre {len(winners)} opções\n{max_votes} votos cada",
                        inline=True,
                    )
            else:
                end_embed.add_field(
                    name="📊 Resultado", value="Nenhum voto registrado", inline=True
                )

            end_embed.add_field(name="🆔 ID da Votação", value=f"`{poll_id}`", inline=True)

            end_embed.add_field(
                name="⚖️ Finalizada por", value=interaction.user.mention, inline=True
            )

            end_embed.add_field(
                name="🔗 Comandos úteis",
                value=f"`/poll-results {poll_id}` - Ver resultados detalhados",
                inline=False,
            )

            await interaction.followup.send(embed=end_embed, ephemeral=True)

            # Anunciar no canal da votação
            try:
                announcement_embed: discord.Embed = discord.Embed(
                    title="🔒 **Votação Finalizada!**",
                    description=f'A enquete "{poll["question"]}" foi finalizada por {interaction.user.mention}.',
                    color=0xFF6B6B,
                    timestamp=datetime.now(),
                )

                if winners and max_votes > 0:
                    if len(winners) == 1:
                        winner_option: dict[str, str] = options[winners[0]]
                        announcement_embed.add_field(
                            name="🏆 Resultado",
                            value=f"**Vencedor:** {winner_option['emoji']} {winner_option['text']} ({max_votes} votos)",
                            inline=False,
                        )
                    else:
                        announcement_embed.add_field(
                            name="🤝 Resultado",
                            value=f"**Empate:** {len(winners)} opções empatadas com {max_votes} votos cada",
                            inline=False,
                        )

                announcement_embed.add_field(
                    name="📊 Estatísticas",
                    value=f"**Total:** {total_votes} votos\n**Opções:** {len(options)}",
                    inline=True,
                )

                announcement_embed.add_field(
                    name="🔍 Ver detalhes", value=f"`/poll-results {poll_id}`", inline=True
                )

                await channel.send(embed=announcement_embed)

            except Exception as e:
                print(f"❌ Erro ao enviar anúncio: {e}")

        except Exception as e:
            print(f"❌ Erro no comando poll-end: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao finalizar votação. Tente novamente.", ephemeral=True
                )
            except:
                pass


async def setup(bot: commands.Bot) -> None:
    """Carrega o cog"""
    await bot.add_cog(PollResults(bot))
