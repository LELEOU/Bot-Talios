"""
Comando Admin - Status do Bot
Gerenciamento de status e presença do bot
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Literal

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class AdminStatus(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.owner_id: str | None = os.getenv("OWNER_ID")

    @app_commands.command(name="status", description="🤖 Alterar status do bot")
    @app_commands.describe(
        tipo="Tipo de atividade do bot",
        texto="Texto do status",
        url="URL para streaming (apenas se tipo for streaming)",
        status_online="Status de presença do bot",
    )
    async def status(
        self,
        interaction: discord.Interaction,
        tipo: Literal["playing", "watching", "listening", "competing", "streaming"],
        texto: str,
        url: str | None = None,
        status_online: Literal["online", "idle", "dnd", "invisible"] | None = "online",
    ) -> None:
        try:
            # Verificar permissões (dono do bot ou administrador)
            is_owner: bool = str(interaction.user.id) == self.owner_id
            is_admin: bool = (
                interaction.user.guild_permissions.administrator if interaction.guild else False
            )

            if not is_owner and not is_admin:
                await interaction.response.send_message(
                    "❌ **Acesso Negado**\n"
                    "Apenas o dono do bot ou administradores podem alterar o status.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Validar URL para streaming
            if tipo == "streaming":
                if not url:
                    await interaction.followup.send(
                        "❌ **URL Obrigatória**\n"
                        "Para streaming, você deve fornecer uma URL válida.",
                        ephemeral=True,
                    )
                    return

                if not url.startswith(("https://twitch.tv/", "https://www.twitch.tv/")):
                    await interaction.followup.send(
                        "❌ **URL Inválida**\n"
                        "Para streaming, você deve usar uma URL válida do Twitch.\n"
                        "Exemplo: `https://twitch.tv/seucanal`",
                        ephemeral=True,
                    )
                    return

            # Mapear tipos de atividade
            activity_types: dict[str, discord.ActivityType] = {
                "playing": discord.ActivityType.playing,
                "watching": discord.ActivityType.watching,
                "listening": discord.ActivityType.listening,
                "competing": discord.ActivityType.competing,
                "streaming": discord.ActivityType.streaming,
            }

            # Mapear status de presença
            presence_status: dict[str, discord.Status] = {
                "online": discord.Status.online,
                "idle": discord.Status.idle,
                "dnd": discord.Status.dnd,
                "invisible": discord.Status.invisible,
            }

            try:
                # Configurar atividade
                activity: discord.Activity | discord.Streaming
                if tipo == "streaming" and url:
                    activity = discord.Streaming(name=texto, url=url)
                else:
                    activity = discord.Activity(type=activity_types[tipo], name=texto)

                # Atualizar presença do bot
                await self.bot.change_presence(
                    activity=activity, status=presence_status[status_online]
                )

            except Exception as e:
                print(f"❌ Erro ao alterar status: {e}")
                await interaction.followup.send(
                    "❌ **Erro de Sistema**\nOcorreu um erro ao alterar o status do bot.",
                    ephemeral=True,
                )
                return

            # Emojis e nomes amigáveis
            type_info: dict[str, dict[str, str]] = {
                "playing": {"emoji": "🎮", "name": "Jogando"},
                "watching": {"emoji": "👀", "name": "Assistindo"},
                "listening": {"emoji": "🎵", "name": "Ouvindo"},
                "competing": {"emoji": "🏆", "name": "Competindo"},
                "streaming": {"emoji": "📹", "name": "Transmitindo"},
            }

            status_info: dict[str, dict[str, str]] = {
                "online": {"emoji": "🟢", "name": "Online"},
                "idle": {"emoji": "🟡", "name": "Ausente"},
                "dnd": {"emoji": "🔴", "name": "Não Perturbe"},
                "invisible": {"emoji": "⚫", "name": "Invisível"},
            }

            # Embed de confirmação
            success_embed: discord.Embed = discord.Embed(
                title="✅ **STATUS ALTERADO**",
                description="O status do bot foi alterado com sucesso!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="🤖 Nova Configuração",
                value=f"**Tipo:** {type_info[tipo]['emoji']} {type_info[tipo]['name']}\n"
                f"**Texto:** {texto}\n"
                f"**Status:** {status_info[status_online]['emoji']} {status_info[status_online]['name']}",
                inline=True,
            )

            if url:
                success_embed.add_field(
                    name="🔗 URL do Stream", value=f"[{url}]({url})", inline=False
                )

            # Informações adicionais
            success_embed.add_field(
                name="ℹ️ Informações",
                value="• O status será mantido até o próximo restart\n"
                "• Visível em todos os servidores\n"
                "• Pode ser alterado novamente a qualquer momento",
                inline=False,
            )

            # Preview do status
            preview_text: str = f"{type_info[tipo]['emoji']} {type_info[tipo]['name']} **{texto}**"
            if tipo == "streaming" and url:
                preview_text += f"\n🔗 {url}"

            success_embed.add_field(name="👁️ Preview", value=preview_text, inline=False)

            success_embed.set_footer(
                text=f"Alterado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

            # Log da alteração
            log_text: str = f"Status alterado por {interaction.user} ({interaction.user.id}): "
            log_text += f"{tipo} - {texto}"
            if url:
                log_text += f" | URL: {url}"
            log_text += f" | Status: {status_online}"

            print(f"🔧 {log_text}")

        except Exception as e:
            print(f"❌ Erro no comando status: {e}")
            try:
                await interaction.followup.send(
                    "❌ **Erro Crítico**\nOcorreu um erro inesperado ao processar o comando.",
                    ephemeral=True,
                )
            except:
                try:
                    await interaction.response.send_message(
                        "❌ Erro ao alterar status do bot.", ephemeral=True
                    )
                except:
                    pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminStatus(bot))
