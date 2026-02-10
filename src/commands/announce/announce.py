"""
Sistema de Anúncios Profissional
Comando para enviar anúncios personalizados com embeds, menções e proteções avançadas
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class Announce(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        # Sistema de cooldown para @everyone (5 minutos)
        self.everyone_cooldowns: dict[str, datetime] = {}

    @app_commands.command(
        name="announce", description="📢 Envia um anúncio personalizado em um canal"
    )
    @app_commands.describe(
        canal="Canal onde enviar o anúncio",
        mensagem="Mensagem do anúncio",
        titulo="Título do embed (opcional)",
        cor="Cor do embed em hex (#0099ff)",
        imagem="URL da imagem",
        mencionar="Cargo para mencionar",
        everyone="Mencionar @everyone (requer permissão especial)",
        embed_mode="Enviar como embed (padrão: True)",
    )
    async def announce(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        mensagem: str,
        titulo: str | None = None,
        cor: str | None = "#0099ff",
        imagem: str | None = None,
        mencionar: discord.Role | None = None,
        everyone: bool | None = False,
        embed_mode: bool | None = True,
    ) -> None:
        try:
            # 🛡️ VERIFICAÇÃO DE PERMISSÕES BÁSICAS
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para enviar anúncios. **Necessário**: Gerenciar Mensagens",
                    ephemeral=True,
                )
                return

            # 🛡️ PROTEÇÃO CONTRA @everyone - Exigir permissão especial
            if everyone and not interaction.user.guild_permissions.mention_everyone:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para mencionar @everyone. **Necessário**: Mencionar Everyone",
                    ephemeral=True,
                )
                return

            # 🛡️ SISTEMA DE COOLDOWN PARA @everyone (5 minutos)
            if everyone:
                user_id: int = interaction.user.id
                guild_id: int = interaction.guild.id
                cooldown_key: str = f"{guild_id}_{user_id}"

                now: datetime = datetime.now()
                cooldown_time: timedelta = timedelta(minutes=5)

                if cooldown_key in self.everyone_cooldowns:
                    time_diff: timedelta = now - self.everyone_cooldowns[cooldown_key]
                    if time_diff < cooldown_time:
                        remaining: timedelta = cooldown_time - time_diff
                        minutes: int = int(remaining.total_seconds() / 60) + 1
                        await interaction.response.send_message(
                            f"❌ Você deve aguardar **{minutes} minutos** antes de usar @everyone novamente.\n"
                            f"⏰ **Proteção Anti-Spam** ativada.",
                            ephemeral=True,
                        )
                        return

                self.everyone_cooldowns[cooldown_key] = now

            # 🛡️ VERIFICAR PERMISSÕES DO BOT NO CANAL
            bot_permissions: discord.Permissions = canal.permissions_for(interaction.guild.me)
            if not bot_permissions.send_messages or not bot_permissions.view_channel:
                await interaction.response.send_message(
                    f"❌ Não tenho permissão para enviar mensagens em {canal.mention}.\n"
                    f"**Permissões necessárias**: Ver Canal, Enviar Mensagens",
                    ephemeral=True,
                )
                return

            # 🎨 VALIDAÇÃO DE COR HEX
            if cor and not re.match(r"^#[0-9a-fA-F]{6}$", cor):
                cor = "#0099ff"  # Cor padrão se inválida

            # 🖼️ VALIDAÇÃO DE URL DA IMAGEM
            if imagem:
                if not (imagem.startswith("http://") or imagem.startswith("https://")):
                    await interaction.response.send_message(
                        "❌ URL da imagem deve começar com http:// ou https://", ephemeral=True
                    )
                    return

            # 📝 PREPARAR CONTEÚDO DA MENÇÃO
            content: str = ""
            allowed_mentions: discord.AllowedMentions = discord.AllowedMentions.none()

            if everyone:
                content = "@everyone"
                allowed_mentions = discord.AllowedMentions(everyone=True)
            elif mencionar:
                content = mencionar.mention
                allowed_mentions = discord.AllowedMentions(roles=[mencionar])

            # 📬 PREPARAR MENSAGEM
            if embed_mode:
                # 🎨 CRIAR EMBED PROFISSIONAL
                embed: discord.Embed = discord.Embed(
                    description=mensagem,
                    color=int(cor.replace("#", ""), 16) if cor else 0x0099FF,
                    timestamp=datetime.now(),
                )

                if titulo:
                    embed.title = titulo

                if imagem:
                    embed.set_image(url=imagem)

                embed.set_footer(
                    text=f"Anúncio por {interaction.user.display_name}",
                    icon_url=interaction.user.display_avatar.url,
                )

                # Adicionar indicador de urgência se @everyone
                if everyone:
                    embed.add_field(
                        name="📢 Anúncio Importante",
                        value="Este anúncio foi enviado para todos os membros do servidor.",
                        inline=False,
                    )

                await canal.send(content=content, embed=embed, allowed_mentions=allowed_mentions)
            else:
                # 📝 MENSAGEM SIMPLES
                final_message: str = mensagem
                if titulo:
                    final_message = f"**{titulo}**\n\n{mensagem}"

                full_content: str = f"{content}\n\n{final_message}" if content else final_message

                await canal.send(content=full_content, allowed_mentions=allowed_mentions)

            # ✅ CONFIRMAÇÃO DE SUCESSO
            success_embed: discord.Embed = discord.Embed(
                color=0x00FF00,
                title="✅ Anúncio Enviado",
                description=f"Anúncio enviado com sucesso para {canal.mention}!",
                timestamp=datetime.now(),
            )

            # Adicionar detalhes do anúncio
            success_embed.add_field(
                name="📊 Detalhes",
                value=f"**Tipo**: {'Embed' if embed_mode else 'Texto'}\n"
                f"**Menções**: {'@everyone' if everyone else mencionar.mention if mencionar else 'Nenhuma'}\n"
                f"**Canal**: {canal.mention}",
                inline=False,
            )

            await interaction.response.send_message(embed=success_embed, ephemeral=True)

            # 📊 LOG DA AÇÃO (se canal de log existir)
            await self._log_announce_action(interaction, canal, embed_mode, everyone, mencionar)

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Não tenho permissão para enviar mensagens no canal especificado.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Erro no comando announce: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Ocorreu um erro ao enviar o anúncio. Tente novamente.", ephemeral=True
                )
            except:
                await interaction.followup.send(
                    "❌ Ocorreu um erro ao enviar o anúncio. Tente novamente.", ephemeral=True
                )

    async def _log_announce_action(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        embed_mode: bool | None,
        everyone: bool | None,
        mencionar: discord.Role | None,
    ) -> None:
        """Log da ação de anúncio em canal de moderação"""
        try:
            # Procurar canal de logs
            log_channel: discord.TextChannel | None = None
            for channel in interaction.guild.text_channels:
                if channel.name.lower() in ["mod-logs", "logs", "audit-log", "moderacao"]:
                    log_channel = channel
                    break

            if not log_channel:
                return

            # Verificar permissões no canal de log
            if not log_channel.permissions_for(interaction.guild.me).send_messages:
                return

            # Criar embed de log
            log_embed: discord.Embed = discord.Embed(
                color=0xFFFF00, title="📢 Anúncio Enviado", timestamp=datetime.now()
            )

            log_embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user}`",
                inline=True,
            )
            log_embed.add_field(name="📍 Canal", value=canal.mention, inline=True)
            log_embed.add_field(
                name="🎨 Tipo", value="Embed" if embed_mode else "Texto", inline=True
            )

            mention_info: str = "Nenhuma"
            if everyone:
                mention_info = "@everyone ⚠️"
            elif mencionar:
                mention_info = mencionar.mention

            log_embed.add_field(name="📢 Menções", value=mention_info, inline=True)
            log_embed.add_field(name="🏛️ Servidor", value=interaction.guild.name, inline=True)
            log_embed.add_field(name="🆔 User ID", value=f"`{interaction.user.id}`", inline=True)

            await log_channel.send(embed=log_embed)

        except Exception as e:
            print(f"❌ Erro ao registrar log do anúncio: {e}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Announce(bot))
