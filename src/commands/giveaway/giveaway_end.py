"""
Sistema de Giveaway - Finalizar Sorteio
Comando para finalizar sorteios manualmente
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class GiveawayEnd(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(name="giveaway-end", description="🏁 Finalizar um sorteio manualmente")
    @app_commands.describe(
        message_id="ID da mensagem do sorteio",
        canal="Canal onde está o sorteio (padrão: canal atual)",
    )
    async def giveaway_end(
        self,
        interaction: discord.Interaction,
        message_id: str,
        canal: discord.TextChannel | None = None,
    ) -> None:
        try:
            await interaction.response.defer()

            # 🛡️ VERIFICAR PERMISSÕES
            if not interaction.user.guild_permissions.manage_events:  # type: ignore
                await interaction.followup.send(
                    "❌ Você não tem permissão para finalizar sorteios. **Necessário**: Gerenciar Eventos",
                    ephemeral=True,
                )
                return

            # 📍 CANAL DO SORTEIO
            target_channel: discord.TextChannel = canal or interaction.channel  # type: ignore

            # 🔍 BUSCAR MENSAGEM DO GIVEAWAY
            message: discord.Message
            try:
                message = await target_channel.fetch_message(int(message_id))
            except (ValueError, discord.NotFound):
                await interaction.followup.send(
                    "❌ Mensagem do sorteio não encontrada!\n\n"
                    "**Dica**: Use o ID da mensagem do sorteio (números longos)",
                    ephemeral=True,
                )
                return
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Não tenho permissão para acessar essa mensagem!", ephemeral=True
                )
                return

            # 🔍 VERIFICAR SE É UM GIVEAWAY
            if not message.embeds or "SORTEIO" not in message.embeds[0].title.upper():
                await interaction.followup.send(
                    "❌ Esta mensagem não parece ser um sorteio!", ephemeral=True
                )
                return

            # 🔍 VERIFICAR SE JÁ FOI FINALIZADO
            embed: discord.Embed = message.embeds[0]
            if "FINALIZADO" in embed.title.upper():
                await interaction.followup.send(
                    "❌ Este sorteio já foi finalizado!", ephemeral=True
                )
                return

            # 💾 BUSCAR DADOS DO BANCO
            giveaway_data: dict[str, Any] | None
            try:
                from ...utils.database import database

                giveaway_data = await database.get(
                    "SELECT * FROM giveaways WHERE message_id = ? AND guild_id = ?",
                    (message_id, str(interaction.guild.id)),  # type: ignore
                )
            except Exception:
                giveaway_data = None

            # 📊 COLETAR PARTICIPANTES
            participants: list[discord.User | discord.Member] = []

            # Buscar participantes das reactions (🎉)
            for reaction in message.reactions:
                if str(reaction.emoji) == "🎉":
                    async for user in reaction.users():
                        if not user.bot and user != self.bot.user:
                            participants.append(user)
                    break

            # 🔢 DETERMINAR NÚMERO DE GANHADORES
            winners_count: int = 1
            if giveaway_data:
                winners_count = giveaway_data.get("winners", 1)
            else:
                # Extrair do embed
                for field in embed.fields:
                    if "Ganhadores" in field.name:
                        try:
                            winners_count = int(field.value.split()[0])
                        except Exception:
                            pass
                        break

            # 🎲 ESCOLHER GANHADORES
            winners: list[discord.User | discord.Member] = []
            if participants:
                winners_count = min(winners_count, len(participants))
                winners = random.sample(participants, winners_count)

            # 🎨 CRIAR EMBED DE RESULTADO
            result_embed: discord.Embed = discord.Embed(
                title="🏆 **SORTEIO FINALIZADO!**", color=0xFFD700, timestamp=datetime.now()
            )

            # Manter descrição original
            original_prize: str = (
                embed.description.split("**🎁 Prêmio:**")[1].split("\n")[0].strip()
                if embed.description and "**🎁 Prêmio:**" in embed.description
                else "Prêmio não especificado"
            )
            result_embed.description = f"**🎁 Prêmio:** {original_prize}"

            if winners:
                # ✅ HÁ GANHADORES
                winners_text: str = "\n".join([f"🏆 {winner.mention}" for winner in winners])

                result_embed.add_field(
                    name=f"🎉 {'Ganhador' if len(winners) == 1 else 'Ganhadores'}:",
                    value=winners_text,
                    inline=False,
                )

                result_embed.add_field(
                    name="📊 Estatísticas",
                    value=f"**Participantes:** {len(participants)}\n"
                    f"**Ganhadores:** {len(winners)}\n"
                    f"**Taxa:** {len(winners) / len(participants) * 100:.1f}%",
                    inline=True,
                )

                result_embed.add_field(
                    name="⏰ Finalizado por",
                    value=f"{interaction.user.mention}\n**Manualmente**",
                    inline=True,
                )

                # Parabenizar ganhadores
                congratulations: str = f"🎉 **Parabéns {'aos ganhadores' if len(winners) > 1 else 'ao ganhador'}!** 🎉\n\n"
                congratulations += "\n".join([f"🏆 {winner.mention}" for winner in winners])
                congratulations += f"\n\n**Prêmio:** {original_prize}"

                await target_channel.send(congratulations)

            else:
                # ❌ SEM PARTICIPANTES
                result_embed.add_field(
                    name="😔 Sem Ganhadores",
                    value="Não houve participantes suficientes para o sorteio.",
                    inline=False,
                )

                result_embed.add_field(
                    name="📊 Estatísticas",
                    value="**Participantes:** 0\n**Ganhadores:** 0",
                    inline=True,
                )

                result_embed.add_field(
                    name="⏰ Finalizado por",
                    value=f"{interaction.user.mention}\n**Manualmente**",
                    inline=True,
                )

            # 🔄 ATUALIZAR MENSAGEM
            await message.edit(embed=result_embed, view=None)

            # 💾 ATUALIZAR BANCO
            if giveaway_data:
                try:
                    from ...utils.database import database

                    await database.run(
                        "UPDATE giveaways SET ended = 1 WHERE message_id = ?", (message_id,)
                    )
                except Exception:
                    pass

            # ✅ CONFIRMAÇÃO
            success_embed: discord.Embed = discord.Embed(
                title="✅ Sorteio Finalizado com Sucesso!",
                description="O sorteio foi finalizado manualmente.",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(name="🎁 Prêmio", value=original_prize, inline=True)

            success_embed.add_field(
                name="👥 Participantes", value=str(len(participants)), inline=True
            )

            success_embed.add_field(name="🏆 Ganhadores", value=str(len(winners)), inline=True)

            success_embed.add_field(
                name="🔗 Link", value=f"[Ver resultado]({message.jump_url})", inline=True
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando giveaway-end: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao finalizar sorteio. Tente novamente.", ephemeral=True
                )
            except Exception:
                pass


def setup(bot: commands.Bot) -> None:
    """Adiciona o cog ao bot"""
    bot.add_cog(GiveawayEnd(bot))
