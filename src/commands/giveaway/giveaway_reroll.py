"""
Sistema de Giveaway - Reroll (Redefinir Ganhadores)
Comando para escolher novos ganhadores de um sorteio finalizado
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


class GiveawayReroll(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(
        name="giveaway-reroll", description="🎲 Escolher novos ganhadores para um sorteio"
    )
    @app_commands.describe(
        message_id="ID da mensagem do sorteio",
        canal="Canal onde está o sorteio (padrão: canal atual)",
        ganhadores="Número de novos ganhadores (padrão: mesmo do sorteio original)",
    )
    async def giveaway_reroll(
        self,
        interaction: discord.Interaction,
        message_id: str,
        canal: discord.TextChannel | None = None,
        ganhadores: int | None = None,
    ) -> None:
        try:
            await interaction.response.defer()

            # 🛡️ VERIFICAR PERMISSÕES
            if not interaction.user.guild_permissions.manage_events:  # type: ignore
                await interaction.followup.send(
                    "❌ Você não tem permissão para reroll sorteios. **Necessário**: Gerenciar Eventos",
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
                    "❌ Mensagem do sorteio não encontrada!", ephemeral=True
                )
                return
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Não tenho permissão para acessar essa mensagem!", ephemeral=True
                )
                return

            # 🔍 VERIFICAR SE É UM GIVEAWAY FINALIZADO
            if not message.embeds:
                await interaction.followup.send(
                    "❌ Esta mensagem não possui embed!", ephemeral=True
                )
                return

            embed: discord.Embed = message.embeds[0]
            if "SORTEIO" not in embed.title.upper():
                await interaction.followup.send(
                    "❌ Esta mensagem não parece ser um sorteio!", ephemeral=True
                )
                return

            if "FINALIZADO" not in embed.title.upper():
                await interaction.followup.send(
                    "❌ Este sorteio ainda não foi finalizado! Use `/giveaway-end` primeiro.",
                    ephemeral=True,
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

            # 🔍 VERIFICAR SE HÁ PARTICIPANTES
            if not participants:
                await interaction.followup.send(
                    "❌ Não há participantes suficientes para fazer reroll!\n\n"
                    "💡 **Dica**: O sorteio precisa ter pelo menos uma reaction 🎉",
                    ephemeral=True,
                )
                return

            # 🔢 DETERMINAR NÚMERO DE GANHADORES
            winners_count: int = ganhadores if ganhadores is not None else 1
            if ganhadores is None:
                # Usar número original
                if giveaway_data:
                    winners_count = giveaway_data.get("winners", 1)
                else:
                    # Extrair do embed
                    winners_count = 1
                    for field in embed.fields:
                        if "Ganhador" in field.name:
                            try:
                                winners_count = len(field.value.split("🏆")) - 1
                            except Exception:
                                pass
                            break

            # 🛡️ VALIDAR NÚMERO DE GANHADORES
            winners_count = max(winners_count, 1)
            winners_count = min(winners_count, 20)
            winners_count = min(winners_count, len(participants))

            # 🎲 ESCOLHER NOVOS GANHADORES
            winners: list[discord.User | discord.Member] = random.sample(participants, winners_count)

            # 🎨 CRIAR EMBED DE REROLL
            reroll_embed: discord.Embed = discord.Embed(
                title="🏆 **SORTEIO FINALIZADO!** (REROLL)",
                color=0xFFD700,
                timestamp=datetime.now(),
            )

            # Manter descrição original do prêmio
            original_prize: str = "Prêmio não especificado"
            if embed.description and "**🎁 Prêmio:**" in embed.description:
                original_prize = embed.description.split("**🎁 Prêmio:**")[1].split("\n")[0].strip()

            reroll_embed.description = f"**🎁 Prêmio:** {original_prize}"

            # ✅ NOVOS GANHADORES
            winners_text: str = "\n".join([f"🏆 {winner.mention}" for winner in winners])

            reroll_embed.add_field(
                name=f"🎲 {'Novo Ganhador' if len(winners) == 1 else 'Novos Ganhadores'} (REROLL):",
                value=winners_text,
                inline=False,
            )

            reroll_embed.add_field(
                name="📊 Estatísticas",
                value=f"**Participantes:** {len(participants)}\n"
                f"**Ganhadores:** {len(winners)}\n"
                f"**Reroll:** #{self.get_reroll_count(embed) + 1}",
                inline=True,
            )

            reroll_embed.add_field(
                name="⏰ Reroll por",
                value=f"{interaction.user.mention}\n<t:{int(datetime.now().timestamp())}:R>",
                inline=True,
            )

            reroll_embed.add_field(
                name="🎯 Chances",
                value=f"{len(winners)}/{len(participants)} ({len(winners) / len(participants) * 100:.1f}%)",
                inline=True,
            )

            # 🔄 ATUALIZAR MENSAGEM
            await message.edit(embed=reroll_embed, view=None)

            # 🎉 ANUNCIAR NOVOS GANHADORES
            congratulations: str = "🎲 **REROLL DO SORTEIO!** 🎲\n\n"
            congratulations += (
                f"🎉 **{'Novo ganhador' if len(winners) == 1 else 'Novos ganhadores'}:**\n\n"
            )
            congratulations += "\n".join([f"🏆 {winner.mention}" for winner in winners])
            congratulations += f"\n\n**🎁 Prêmio:** {original_prize}"
            congratulations += f"\n**🎲 Reroll por:** {interaction.user.mention}"

            await target_channel.send(congratulations)

            # ✅ CONFIRMAÇÃO PARA O MODERADOR
            success_embed: discord.Embed = discord.Embed(
                title="✅ Reroll Realizado com Sucesso!",
                description="Novos ganhadores foram escolhidos para o sorteio.",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(name="🎁 Prêmio", value=original_prize, inline=True)

            success_embed.add_field(
                name="👥 Participantes", value=str(len(participants)), inline=True
            )

            success_embed.add_field(
                name="🏆 Novos Ganhadores", value=str(len(winners)), inline=True
            )

            success_embed.add_field(
                name="🎲 Reroll #", value=str(self.get_reroll_count(embed) + 1), inline=True
            )

            success_embed.add_field(
                name="🔗 Link", value=f"[Ver resultado]({message.jump_url})", inline=True
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando giveaway-reroll: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao fazer reroll do sorteio. Tente novamente.", ephemeral=True
                )
            except Exception:
                pass

    def get_reroll_count(self, embed: discord.Embed) -> int:
        """Conta quantas vezes já foi feito reroll"""
        reroll_count: int = 0

        # Procurar por indicações de reroll no embed
        for field in embed.fields:
            if "REROLL" in field.name.upper():
                try:
                    # Extrair número do reroll se presente
                    if "Reroll:" in field.value:
                        reroll_text: str = field.value.split("Reroll:")[1].split()[0]
                        if reroll_text.startswith("#"):
                            reroll_count = int(reroll_text[1:])
                except Exception:
                    pass
                break

        # Verificar título também
        if "REROLL" in embed.title.upper():
            reroll_count = max(reroll_count, 1)

        return reroll_count


def setup(bot: commands.Bot) -> None:
    """Adiciona o cog ao bot"""
    bot.add_cog(GiveawayReroll(bot))
