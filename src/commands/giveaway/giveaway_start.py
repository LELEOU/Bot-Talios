"""
Sistema de Giveaway - Iniciar Sorteio
Comando completo para criar sorteios com interface moderna
"""

from __future__ import annotations

import random
import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

if TYPE_CHECKING:
    pass


class GiveawayStart(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        # Task temporariamente desabilitada para evitar conflitos
        # TODO: Implementar sistema de task singleton mais robusto
        # if not self.check_giveaways.is_running():
        #     self.check_giveaways.start()

    @app_commands.command(name="giveaway-start", description="🎉 Iniciar um sorteio no servidor")
    @app_commands.describe(
        premio="Prêmio do sorteio",
        duracao="Duração (ex: 1h, 30m, 1d, 2w)",
        ganhadores="Número de ganhadores (padrão: 1)",
        canal="Canal para o sorteio (padrão: atual)",
    )
    async def giveaway_start(
        self,
        interaction: discord.Interaction,
        premio: str,
        duracao: str,
        ganhadores: int | None = 1,
        canal: discord.TextChannel | None = None,
    ) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # 🛡️ VERIFICAR PERMISSÕES
            if not interaction.user.guild_permissions.manage_events:  # type: ignore
                await interaction.followup.send(
                    "❌ Você não tem permissão para criar sorteios. **Necessário**: Gerenciar Eventos",
                    ephemeral=True,
                )
                return

            # 🛡️ VALIDAÇÕES
            winners_count: int = ganhadores if ganhadores else 1
            if winners_count < 1 or winners_count > 50:
                await interaction.followup.send(
                    "❌ O número de ganhadores deve estar entre 1 e 50!", ephemeral=True
                )
                return

            if len(premio) > 200:
                await interaction.followup.send(
                    "❌ O prêmio deve ter no máximo 200 caracteres!", ephemeral=True
                )
                return

            # 📅 CONVERTER DURAÇÃO
            duration_ms: int | None = self.parse_duration(duracao)
            if not duration_ms:
                await interaction.followup.send(
                    "❌ Formato de duração inválido!\n\n"
                    "**Formatos aceitos:**\n"
                    "• `30s` - 30 segundos\n"
                    "• `15m` - 15 minutos\n"
                    "• `2h` - 2 horas\n"
                    "• `3d` - 3 dias\n"
                    "• `1w` - 1 semana",
                    ephemeral=True,
                )
                return

            # 🛡️ LIMITES DE DURAÇÃO
            min_duration: int = 60 * 1000  # 1 minuto
            max_duration: int = 30 * 24 * 60 * 60 * 1000  # 30 dias

            if duration_ms < min_duration:
                await interaction.followup.send(
                    "❌ A duração mínima é de **1 minuto**!", ephemeral=True
                )
                return

            if duration_ms > max_duration:
                await interaction.followup.send(
                    "❌ A duração máxima é de **30 dias**!", ephemeral=True
                )
                return

            # 📍 CANAL DO SORTEIO
            target_channel: discord.TextChannel = canal or interaction.channel  # type: ignore

            # 🛡️ VERIFICAR PERMISSÕES NO CANAL
            if not target_channel.permissions_for(interaction.guild.me).send_messages:  # type: ignore
                await interaction.followup.send(
                    f"❌ Não tenho permissão para enviar mensagens em {target_channel.mention}!",
                    ephemeral=True,
                )
                return

            # ⏰ CALCULAR TEMPO DE TÉRMINO
            end_time: datetime = datetime.now() + timedelta(milliseconds=duration_ms)

            # 🎨 CRIAR EMBED DO GIVEAWAY
            embed: discord.Embed = discord.Embed(
                title="🎉 **SORTEIO ATIVO!**",
                description=f"**🎁 Prêmio:** {premio}\n\n"
                f"**👥 Ganhadores:** {winners_count}\n"
                f"**⏰ Termina:** <t:{int(end_time.timestamp())}:R>\n"
                f"**📅 Data:** <t:{int(end_time.timestamp())}:F>\n\n"
                f"**🎯 Como participar:**\n"
                f"Clique no botão 🎉 abaixo para entrar no sorteio!",
                color=0xFF6B6B,
                timestamp=end_time,
            )

            embed.set_footer(
                text=f"Criado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/787346885996085258.gif")

            # 🔘 CRIAR VIEW DO GIVEAWAY
            view: GiveawayView = GiveawayView(interaction.id)

            # 📤 ENVIAR GIVEAWAY
            giveaway_message: discord.Message = await target_channel.send(
                content="@here 🎉 **NOVO SORTEIO!** 🎉", embed=embed, view=view
            )

            # 💾 SALVAR NO BANCO
            try:
                from ...utils.database import database

                await database.run(
                    """INSERT INTO giveaways 
                    (guild_id, channel_id, message_id, host_id, title, description, winners, end_time, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(interaction.guild.id),  # type: ignore
                        str(target_channel.id),
                        str(giveaway_message.id),
                        str(interaction.user.id),
                        f"Sorteio: {premio}",
                        premio,
                        winners_count,
                        end_time.isoformat(),
                        datetime.now().isoformat(),
                    ),
                )
            except Exception as e:
                print(f"❌ Erro ao salvar giveaway no banco: {e}")

            # ✅ CONFIRMAÇÃO
            success_embed: discord.Embed = discord.Embed(
                title="✅ **SORTEIO CRIADO COM SUCESSO!**",
                description=f"🎉 O sorteio foi iniciado em {target_channel.mention}!",
                color=0x57F287,
                timestamp=datetime.now(),
            )

            success_embed.add_field(name="🎁 Prêmio", value=premio, inline=True)
            success_embed.add_field(name="⏰ Duração", value=duracao, inline=True)
            success_embed.add_field(name="👥 Ganhadores", value=str(winners_count), inline=True)
            success_embed.add_field(
                name="🆔 ID do Sorteio", value=f"`{interaction.id}`", inline=True
            )
            success_embed.add_field(
                name="🔗 Link",
                value=f"[Ir para o sorteio]({giveaway_message.jump_url})",
                inline=True,
            )
            success_embed.add_field(name="📊 Status", value="🟢 Ativo", inline=True)

            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando giveaway-start: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao criar sorteio. Tente novamente.", ephemeral=True
                )
            except Exception:
                pass

    def parse_duration(self, duration_str: str) -> int | None:
        """Converte string de duração para millisegundos"""
        pattern: str = r"^(\d+)([smhdw])$"
        match: re.Match[str] | None = re.match(pattern, duration_str.lower())

        if not match:
            return None

        value: int = int(match.group(1))
        unit: str = match.group(2)

        multipliers: dict[str, int] = {
            "s": 1000,  # segundos
            "m": 60 * 1000,  # minutos
            "h": 60 * 60 * 1000,  # horas
            "d": 24 * 60 * 60 * 1000,  # dias
            "w": 7 * 24 * 60 * 60 * 1000,  # semanas
        }

        return value * multipliers.get(unit, 0)

    @tasks.loop(minutes=1)
    async def check_giveaways(self) -> None:
        """Verificar giveaways que terminaram"""
        try:
            from ...utils.database import database

            # Buscar giveaways ativos que terminaram
            expired_giveaways: list[dict[str, Any]] = await database.get_all(
                "SELECT * FROM giveaways WHERE ended = 0 AND end_time <= ?",
                (datetime.now().isoformat(),),
            )

            for giveaway in expired_giveaways:
                await self.end_giveaway(giveaway)

        except Exception as e:
            print(f"❌ Erro ao verificar giveaways: {e}")

    async def end_giveaway(self, giveaway_data: dict[str, Any]) -> None:
        """Finalizar um giveaway"""
        try:
            # Buscar guild e canal
            guild: discord.Guild | None = self.bot.get_guild(int(giveaway_data["guild_id"]))
            if not guild:
                return

            channel: discord.abc.GuildChannel | None = guild.get_channel(int(giveaway_data["channel_id"]))
            if not channel or not isinstance(channel, discord.TextChannel):
                return

            # Buscar mensagem do giveaway
            message: discord.Message
            try:
                message = await channel.fetch_message(int(giveaway_data["message_id"]))
            except Exception:
                return

            # Buscar participantes (implementar depois com views)
            participants: list[discord.Member] = []  # Será implementado com sistema de participação

            # Marcar como finalizado
            try:
                from ...utils.database import database

                await database.run(
                    "UPDATE giveaways SET ended = 1 WHERE message_id = ?",
                    (giveaway_data["message_id"],),
                )
            except Exception:
                pass

            # Criar embed de finalização
            embed: discord.Embed = discord.Embed(
                title="🏆 **SORTEIO FINALIZADO!**",
                description=f"**🎁 Prêmio:** {giveaway_data['description']}",
                color=0xFFD700,
                timestamp=datetime.now(),
            )

            if participants and len(participants) >= giveaway_data["winners"]:
                # Escolher ganhadores
                winners: list[discord.Member] = random.sample(
                    participants, min(giveaway_data["winners"], len(participants))
                )
                winners_text: str = "\n".join([f"🏆 {winner.mention}" for winner in winners])

                embed.add_field(
                    name=f"🎉 Ganhador{'es' if len(winners) > 1 else ''}:",
                    value=winners_text,
                    inline=False,
                )

                embed.add_field(
                    name="📊 Estatísticas",
                    value=f"**Participantes:** {len(participants)}\n**Ganhadores:** {len(winners)}",
                    inline=True,
                )
            else:
                embed.add_field(
                    name="😔 Sem Ganhadores",
                    value="Não houve participantes suficientes para o sorteio.",
                    inline=False,
                )

            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/787346885996085258.gif")

            await message.edit(embed=embed, view=None)

        except Exception as e:
            print(f"❌ Erro ao finalizar giveaway: {e}")

    def cog_unload(self) -> None:
        """Parar task quando o cog for removido"""
        if self.check_giveaways.is_running():
            self.check_giveaways.cancel()


class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id: int) -> None:
        super().__init__(timeout=None)  # Persistent view
        self.giveaway_id: int = giveaway_id
        self.participants: set[int] = set()

    @discord.ui.button(
        label="🎉 Participar", style=discord.ButtonStyle.primary, custom_id="giveaway_join"
    )
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        user_id: int = interaction.user.id

        if user_id in self.participants:
            await interaction.response.send_message(
                "❌ Você já está participando deste sorteio!", ephemeral=True
            )
            return

        self.participants.add(user_id)

        # Atualizar embed com novo número de participantes
        embed: discord.Embed = interaction.message.embeds[0]  # type: ignore
        for i, field in enumerate(embed.fields):
            if "Participantes" in field.name:
                embed.set_field_at(
                    i,
                    name="📊 Participantes",
                    value=f"{len(self.participants)} pessoas",
                    inline=True,
                )
                break

        await interaction.response.edit_message(embed=embed, view=self)

        # Confirmação privada
        await interaction.followup.send(
            f"✅ Você entrou no sorteio! 🍀\n**Participantes:** {len(self.participants)}",
            ephemeral=True,
        )


def setup(bot: commands.Bot) -> None:
    """Adiciona o cog ao bot"""
    bot.add_cog(GiveawayStart(bot))
