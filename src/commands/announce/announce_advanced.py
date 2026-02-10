"""
Sistema de Anúncios Avançado
Envio de anúncios personalizados com embeds e proteções
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class AnnounceSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.everyone_cooldowns: dict[str, datetime] = {}

    @app_commands.command(name="announce", description="📢 Enviar anúncio personalizado")
    @app_commands.describe(
        canal="Canal onde enviar o anúncio",
        mensagem="Conteúdo da mensagem do anúncio",
        titulo="Título do embed (opcional)",
        cor="Cor do embed em hexadecimal (ex: #0099ff)",
        imagem="URL da imagem para o embed",
        mencionar="Role para mencionar no anúncio",
        everyone="Mencionar @everyone (requer permissão)",
        embed="Enviar como embed (padrão: sim)",
    )
    async def announce(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        mensagem: str,
        titulo: str | None = None,
        cor: str | None = None,
        imagem: str | None = None,
        mencionar: discord.Role | None = None,
        everyone: bool = False,
        embed: bool = True,
    ) -> None:
        try:
            # Verificar permissões básicas
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message(
                    "❌ **Permissão Insuficiente**\n"
                    "Você precisa da permissão `Gerenciar Mensagens` para usar este comando.",
                    ephemeral=True,
                )
                return

            # Verificar permissão para @everyone
            if everyone and not interaction.user.guild_permissions.mention_everyone:
                await interaction.response.send_message(
                    "❌ **Permissão para @everyone**\n"
                    "Você não tem permissão para mencionar @everyone.\n"
                    "Necessário: **Mencionar Everyone**",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Cooldown para @everyone (5 minutos)
            if everyone:
                cooldown_key: str = f"{interaction.guild.id}_{interaction.user.id}"
                now: datetime = datetime.now()

                if cooldown_key in self.everyone_cooldowns:
                    last_used: datetime = self.everyone_cooldowns[cooldown_key]
                    cooldown_time: timedelta = timedelta(minutes=5)

                    if now - last_used < cooldown_time:
                        remaining: timedelta = cooldown_time - (now - last_used)
                        minutes_left: int = int(remaining.total_seconds() / 60) + 1

                        await interaction.followup.send(
                            f"❌ **Cooldown Ativo**\n"
                            f"Você deve aguardar **{minutes_left} minutos** antes de usar @everyone novamente.\n"
                            f"Esta proteção evita spam de notificações.",
                            ephemeral=True,
                        )
                        return

                self.everyone_cooldowns[cooldown_key] = now

            # Verificar permissões do bot no canal
            bot_perms: discord.Permissions = canal.permissions_for(interaction.guild.me)
            if not (bot_perms.send_messages and bot_perms.view_channel):
                await interaction.followup.send(
                    f"❌ **Sem Permissões**\n"
                    f"Não tenho permissão para enviar mensagens em {canal.mention}.\n"
                    f"Permissões necessárias: `Visualizar Canal`, `Enviar Mensagens`",
                    ephemeral=True,
                )
                return

            # Validar cor hexadecimal
            color_int: int = 0x0099FF  # Cor padrão
            if cor:
                color_match: re.Match[str] | None = re.match(r"^#?([0-9a-fA-F]{6})$", cor)
                if color_match:
                    color_int = int(color_match.group(1), 16)
                else:
                    await interaction.followup.send(
                        "❌ **Cor Inválida**\n"
                        "Use formato hexadecimal válido: `#0099ff` ou `0099ff`",
                        ephemeral=True,
                    )
                    return

            # Validar URL da imagem
            if imagem:
                try:
                    parsed_url: Any = urlparse(imagem)
                    if not all([parsed_url.scheme, parsed_url.netloc]):
                        raise ValueError("URL inválida")

                    # Verificar extensões de imagem comuns
                    valid_extensions: tuple[str, ...] = (
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".webp",
                        ".bmp",
                    )
                    if not any(imagem.lower().endswith(ext) for ext in valid_extensions):
                        await interaction.followup.send(
                            "⚠️ **Aviso de Imagem**\n"
                            "A URL não parece ser uma imagem válida.\n"
                            "Extensões suportadas: PNG, JPG, GIF, WebP, BMP",
                            ephemeral=True,
                        )
                        # Continua mesmo assim

                except Exception:
                    await interaction.followup.send(
                        "❌ **URL da Imagem Inválida**\n"
                        "Por favor, forneça uma URL válida para a imagem.",
                        ephemeral=True,
                    )
                    return

            # Preparar menções
            mention_content: str = ""
            allowed_mentions: discord.AllowedMentions = discord.AllowedMentions(
                everyone=False, roles=False
            )

            if everyone:
                mention_content = "@everyone"
                allowed_mentions = discord.AllowedMentions(everyone=True)
            elif mencionar:
                mention_content = mencionar.mention
                allowed_mentions = discord.AllowedMentions(roles=[mencionar])

            # Criar conteúdo da mensagem
            sent_message: discord.Message
            if embed:
                # Criar embed avançado
                announce_embed: discord.Embed = discord.Embed(
                    description=mensagem, color=color_int, timestamp=datetime.now()
                )

                if titulo:
                    announce_embed.title = titulo

                if imagem:
                    announce_embed.set_image(url=imagem)

                # Adicionar informações do autor
                announce_embed.set_footer(
                    text=f"📢 Anúncio por {interaction.user.display_name}",
                    icon_url=interaction.user.display_avatar.url,
                )

                # Adicionar badge se for @everyone
                if everyone:
                    announce_embed.add_field(
                        name="🔔 Notificação Importante",
                        value="Este é um anúncio para todos os membros do servidor.",
                        inline=False,
                    )

                # Enviar embed
                try:
                    sent_message = await canal.send(
                        content=mention_content if mention_content else None,
                        embed=announce_embed,
                        allowed_mentions=allowed_mentions,
                    )
                except discord.Forbidden:
                    await interaction.followup.send(
                        "❌ **Erro de Permissão**\n"
                        "Não consegui enviar o anúncio. Verifique as permissões do bot.",
                        ephemeral=True,
                    )
                    return

            else:
                # Enviar como texto simples
                content_text: str = mensagem
                if titulo:
                    content_text = f"**{titulo}**\n\n{mensagem}"

                if mention_content:
                    content_text = f"{mention_content}\n\n{content_text}"

                try:
                    sent_message = await canal.send(
                        content=content_text, allowed_mentions=allowed_mentions
                    )
                except discord.Forbidden:
                    await interaction.followup.send(
                        "❌ **Erro de Permissão**\n"
                        "Não consegui enviar o anúncio. Verifique as permissões do bot.",
                        ephemeral=True,
                    )
                    return

            # Embed de confirmação
            success_embed: discord.Embed = discord.Embed(
                title="✅ **ANÚNCIO ENVIADO**",
                description=f"Anúncio enviado com sucesso para {canal.mention}!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="📊 Detalhes do Envio",
                value=f"**Canal:** {canal.mention}\n"
                f"**Tipo:** {'Embed' if embed else 'Texto simples'}\n"
                f"**Menção:** {'@everyone' if everyone else mencionar.mention if mencionar else 'Nenhuma'}\n"
                f"**ID da Mensagem:** `{sent_message.id}`",
                inline=False,
            )

            # Prévia do conteúdo
            preview_content: str = mensagem[:200] + "..." if len(mensagem) > 200 else mensagem
            success_embed.add_field(
                name="👁️ Prévia do Conteúdo", value=f"```{preview_content}```", inline=False
            )

            # Link direto para a mensagem
            message_link: str = (
                f"https://discord.com/channels/{interaction.guild.id}/{canal.id}/{sent_message.id}"
            )
            success_embed.add_field(
                name="🔗 Link Direto", value=f"[Ir para o anúncio]({message_link})", inline=False
            )

            success_embed.set_footer(
                text=f"Enviado por {interaction.user}", icon_url=interaction.user.display_avatar.url
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

            # Log administrativo
            await self._log_announce(
                interaction, canal, mensagem, titulo, everyone, mencionar, embed, sent_message
            )

        except Exception as e:
            print(f"❌ Erro no comando announce: {e}")
            try:
                await interaction.followup.send(
                    "❌ **Erro do Sistema**\nOcorreu um erro inesperado ao enviar o anúncio.",
                    ephemeral=True,
                )
            except:
                try:
                    await interaction.response.send_message(
                        "❌ Erro ao processar anúncio.", ephemeral=True
                    )
                except:
                    pass

    async def _log_announce(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        mensagem: str,
        titulo: str | None,
        everyone: bool,
        mencionar: discord.Role | None,
        embed: bool,
        sent_message: discord.Message,
    ) -> None:
        """Log administrativo do anúncio"""
        try:
            # Procurar canal de logs
            log_channel: discord.TextChannel | None = None
            for channel_name in ["mod-logs", "logs", "audit-logs", "moderacao"]:
                log_channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
                if log_channel:
                    break

            if not log_channel:
                return

            # Verificar permissões no canal de log
            if not log_channel.permissions_for(interaction.guild.me).send_messages:
                return

            # Criar embed de log
            log_embed: discord.Embed = discord.Embed(
                title="📢 **ANÚNCIO ADMINISTRATIVO**", color=0xFFAA00, timestamp=datetime.now()
            )

            log_embed.add_field(
                name="👤 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user} ({interaction.user.id})`",
                inline=True,
            )

            log_embed.add_field(
                name="📍 Canal de Destino", value=f"{canal.mention}\n`#{canal.name}`", inline=True
            )

            log_embed.add_field(
                name="⚙️ Configurações",
                value=f"**Tipo:** {'Embed' if embed else 'Texto'}\n"
                f"**Título:** {titulo if titulo else 'Nenhum'}\n"
                f"**Menção:** {'@everyone' if everyone else mencionar.mention if mencionar else 'Nenhuma'}",
                inline=False,
            )

            # Prévia do conteúdo
            content_preview: str = mensagem[:300] + "..." if len(mensagem) > 300 else mensagem
            log_embed.add_field(name="📄 Conteúdo", value=f"```{content_preview}```", inline=False)

            # Link direto
            message_link: str = (
                f"https://discord.com/channels/{interaction.guild.id}/{canal.id}/{sent_message.id}"
            )
            log_embed.add_field(
                name="🔗 Ações",
                value=f"[Ir para anúncio]({message_link}) | ID: `{sent_message.id}`",
                inline=False,
            )

            log_embed.set_footer(
                text=f"Sistema de Logs • {interaction.guild.name}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            await log_channel.send(embed=log_embed)

        except Exception as e:
            print(f"❌ Erro no log de anúncio: {e}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AnnounceSystem(bot))
