"""
Sistema de Comunicação Avançado
Comandos Say e Post com proteções e logs
"""

from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands


class CommunicationSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mention_cooldowns = {}

    @app_commands.command(name="say", description="💬 Fazer o bot enviar uma mensagem")
    @app_commands.describe(
        mensagem="Mensagem para o bot enviar",
        canal="Canal onde enviar (padrão: canal atual)",
        embed="Enviar como embed",
        responder="ID da mensagem para responder",
    )
    async def say(
        self,
        interaction: discord.Interaction,
        mensagem: str,
        canal: discord.TextChannel | None = None,
        embed: bool = False,
        responder: str | None = None,
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message(
                    "❌ **Permissão Insuficiente**\n"
                    "Você precisa da permissão `Gerenciar Mensagens` para usar este comando.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            target_channel = canal or interaction.channel

            # Verificar se é um canal de texto
            if not isinstance(target_channel, discord.TextChannel):
                await interaction.followup.send(
                    "❌ **Canal Inválido**\nEste comando só funciona em canais de texto.",
                    ephemeral=True,
                )
                return

            # Proteção contra @everyone/@here
            has_everyone = "@everyone" in mensagem or "@here" in mensagem
            if has_everyone:
                if not interaction.user.guild_permissions.mention_everyone:
                    await interaction.followup.send(
                        "❌ **Menção Não Permitida**\n"
                        "Você não tem permissão para mencionar @everyone/@here.\n"
                        "Use o comando `/announce` para anúncios com menções.",
                        ephemeral=True,
                    )
                    return

                # Cooldown para menções especiais (3 minutos)
                cooldown_key = f"say_{interaction.user.id}"
                now = datetime.now()

                if cooldown_key in self.mention_cooldowns:
                    last_used = self.mention_cooldowns[cooldown_key]
                    cooldown_time = timedelta(minutes=3)

                    if now - last_used < cooldown_time:
                        remaining = cooldown_time - (now - last_used)
                        minutes_left = int(remaining.total_seconds() / 60) + 1

                        await interaction.followup.send(
                            f"❌ **Cooldown de Menções**\n"
                            f"Aguarde **{minutes_left} minutos** antes de mencionar everyone/here novamente.",
                            ephemeral=True,
                        )
                        return

                self.mention_cooldowns[cooldown_key] = now

            # Verificar permissões do bot no canal
            bot_perms = target_channel.permissions_for(interaction.guild.me)
            if not (bot_perms.send_messages and bot_perms.view_channel):
                await interaction.followup.send(
                    f"❌ **Sem Permissões**\n"
                    f"Não tenho permissão para enviar mensagens em {target_channel.mention}.",
                    ephemeral=True,
                )
                return

            # Verificar tamanho da mensagem
            if len(mensagem) > 2000 and not embed:
                await interaction.followup.send(
                    "❌ **Mensagem Muito Longa**\n"
                    f"Mensagem tem {len(mensagem)} caracteres (máximo: 2000).\n"
                    "Use a opção `embed: True` ou reduza o texto.",
                    ephemeral=True,
                )
                return

            # Verificar mensagem para responder
            reply_message = None
            if responder:
                try:
                    reply_message = await target_channel.fetch_message(int(responder))
                except (ValueError, discord.NotFound):
                    await interaction.followup.send(
                        "❌ **Mensagem para Resposta Inválida**\n"
                        "ID da mensagem não encontrado ou inválido.",
                        ephemeral=True,
                    )
                    return
                except discord.Forbidden:
                    await interaction.followup.send(
                        "❌ **Sem Permissão**\nNão consegui acessar a mensagem para responder.",
                        ephemeral=True,
                    )
                    return

            # Preparar conteúdo da mensagem
            try:
                if embed:
                    # Criar embed
                    message_embed = discord.Embed(
                        description=mensagem, color=0x0099FF, timestamp=datetime.now()
                    )

                    # Adicionar informações se for resposta
                    if reply_message:
                        message_embed.set_author(
                            name=f"Em resposta a {reply_message.author.display_name}",
                            icon_url=reply_message.author.display_avatar.url,
                        )

                    # Configurar menções permitidas
                    allowed_mentions = discord.AllowedMentions(
                        everyone=has_everyone and "@everyone" in mensagem,
                        here=has_everyone and "@here" in mensagem,
                        users=True,
                        roles=True,
                    )

                    sent_message = await target_channel.send(
                        embed=message_embed,
                        reference=reply_message,
                        allowed_mentions=allowed_mentions,
                    )

                else:
                    # Enviar como texto simples
                    allowed_mentions = discord.AllowedMentions(
                        everyone=has_everyone and "@everyone" in mensagem,
                        here=has_everyone and "@here" in mensagem,
                        users=True,
                        roles=True,
                    )

                    sent_message = await target_channel.send(
                        content=mensagem, reference=reply_message, allowed_mentions=allowed_mentions
                    )

            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ **Erro de Permissão**\n"
                    "Não consegui enviar a mensagem. Verifique as permissões do bot.",
                    ephemeral=True,
                )
                return
            except Exception as e:
                print(f"❌ Erro ao enviar mensagem via say: {e}")
                await interaction.followup.send(
                    "❌ **Erro do Sistema**\nOcorreu um erro ao enviar a mensagem.", ephemeral=True
                )
                return

            # Embed de confirmação
            success_embed = discord.Embed(
                title="✅ **MENSAGEM ENVIADA**",
                description=f"Mensagem enviada com sucesso{'!' if target_channel == interaction.channel else f' para {target_channel.mention}!'}",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="📊 Detalhes",
                value=f"**Canal:** {target_channel.mention}\n"
                f"**Tipo:** {'Embed' if embed else 'Texto simples'}\n"
                f"**Resposta:** {'Sim' if reply_message else 'Não'}\n"
                f"**Menções:** {'Sim' if has_everyone else 'Não'}\n"
                f"**ID da Mensagem:** `{sent_message.id}`",
                inline=False,
            )

            # Prévia do conteúdo
            preview_content = mensagem[:150] + "..." if len(mensagem) > 150 else mensagem
            success_embed.add_field(name="👁️ Prévia", value=f"```{preview_content}```", inline=False)

            # Link direto
            message_link = f"https://discord.com/channels/{interaction.guild.id}/{target_channel.id}/{sent_message.id}"
            success_embed.add_field(
                name="🔗 Link Direto", value=f"[Ir para mensagem]({message_link})", inline=False
            )

            success_embed.set_footer(
                text=f"Enviado por {interaction.user}", icon_url=interaction.user.display_avatar.url
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

            # Log administrativo
            await self._log_say_command(
                interaction, target_channel, mensagem, embed, has_everyone, sent_message
            )

        except Exception as e:
            print(f"❌ Erro no comando say: {e}")
            try:
                await interaction.followup.send(
                    "❌ **Erro Crítico**\nOcorreu um erro inesperado ao processar o comando.",
                    ephemeral=True,
                )
            except:
                try:
                    await interaction.response.send_message(
                        "❌ Erro ao processar comando.", ephemeral=True
                    )
                except:
                    pass

    @app_commands.command(name="post", description="📌 Postar mensagem simples em um canal")
    @app_commands.describe(
        mensagem="Mensagem para postar", canal="Canal onde postar (padrão: canal atual)"
    )
    async def post(
        self,
        interaction: discord.Interaction,
        mensagem: str,
        canal: discord.TextChannel | None = None,
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message(
                    "❌ **Permissão Insuficiente**\n"
                    "Você precisa da permissão `Gerenciar Mensagens` para usar este comando.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            target_channel = canal or interaction.channel

            # Verificar se é um canal de texto
            if not isinstance(target_channel, discord.TextChannel):
                await interaction.followup.send(
                    "❌ **Canal Inválido**\nEste comando só funciona em canais de texto.",
                    ephemeral=True,
                )
                return

            # Verificar permissões do bot
            bot_perms = target_channel.permissions_for(interaction.guild.me)
            if not (bot_perms.send_messages and bot_perms.view_channel):
                await interaction.followup.send(
                    f"❌ **Sem Permissões**\n"
                    f"Não tenho permissão para enviar mensagens em {target_channel.mention}.",
                    ephemeral=True,
                )
                return

            # Verificar tamanho da mensagem
            if len(mensagem) > 2000:
                await interaction.followup.send(
                    f"❌ **Mensagem Muito Longa**\n"
                    f"Mensagem tem {len(mensagem)} caracteres (máximo: 2000).\n"
                    "Reduza o texto ou use o comando `/say` com embed.",
                    ephemeral=True,
                )
                return

            try:
                # Enviar mensagem simples
                sent_message = await target_channel.send(content=mensagem)

            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ **Erro de Permissão**\n"
                    "Não consegui enviar a mensagem. Verifique as permissões do bot.",
                    ephemeral=True,
                )
                return
            except Exception as e:
                print(f"❌ Erro ao enviar post: {e}")
                await interaction.followup.send(
                    "❌ **Erro do Sistema**\nOcorreu um erro ao enviar a mensagem.", ephemeral=True
                )
                return

            # Embed de confirmação
            success_embed = discord.Embed(
                title="✅ **MENSAGEM POSTADA**",
                description=f"Mensagem postada com sucesso{'!' if target_channel == interaction.channel else f' em {target_channel.mention}!'}",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="📊 Detalhes",
                value=f"**Canal:** {target_channel.mention}\n"
                f"**Caracteres:** {len(mensagem)}\n"
                f"**ID da Mensagem:** `{sent_message.id}`",
                inline=False,
            )

            # Prévia do conteúdo
            preview_content = mensagem[:200] + "..." if len(mensagem) > 200 else mensagem
            success_embed.add_field(
                name="👁️ Conteúdo", value=f"```{preview_content}```", inline=False
            )

            # Link direto
            message_link = f"https://discord.com/channels/{interaction.guild.id}/{target_channel.id}/{sent_message.id}"
            success_embed.add_field(
                name="🔗 Link Direto", value=f"[Ir para mensagem]({message_link})", inline=False
            )

            success_embed.set_footer(
                text=f"Postado por {interaction.user}", icon_url=interaction.user.display_avatar.url
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando post: {e}")
            try:
                await interaction.followup.send(
                    "❌ **Erro Crítico**\nOcorreu um erro inesperado ao processar o comando.",
                    ephemeral=True,
                )
            except:
                try:
                    await interaction.response.send_message(
                        "❌ Erro ao processar comando.", ephemeral=True
                    )
                except:
                    pass

    async def _log_say_command(
        self, interaction, channel, message, is_embed, has_mentions, sent_message
    ):
        """Log do comando say"""
        try:
            # Procurar canal de logs
            log_channel = None
            for channel_name in ["mod-logs", "logs", "audit-logs", "moderacao"]:
                log_channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
                if log_channel and log_channel != channel:
                    break

            if not log_channel:
                return

            # Verificar permissões
            if not log_channel.permissions_for(interaction.guild.me).send_messages:
                return

            # Criar embed de log
            log_embed = discord.Embed(
                title="💬 **COMANDO SAY USADO**", color=0x0099FF, timestamp=datetime.now()
            )

            log_embed.add_field(
                name="👤 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user} ({interaction.user.id})`",
                inline=True,
            )

            log_embed.add_field(
                name="📍 Canal de Destino",
                value=f"{channel.mention}\n`#{channel.name}`",
                inline=True,
            )

            log_embed.add_field(
                name="⚙️ Configurações",
                value=f"**Tipo:** {'Embed' if is_embed else 'Texto'}\n"
                f"**Menções:** {'Sim' if has_mentions else 'Não'}\n"
                f"**Caracteres:** {len(message)}",
                inline=False,
            )

            # Prévia do conteúdo
            content_preview = message[:400] + "..." if len(message) > 400 else message
            log_embed.add_field(name="📄 Conteúdo", value=f"```{content_preview}```", inline=False)

            # Link direto
            message_link = f"https://discord.com/channels/{interaction.guild.id}/{channel.id}/{sent_message.id}"
            log_embed.add_field(
                name="🔗 Link",
                value=f"[Ir para mensagem]({message_link}) | ID: `{sent_message.id}`",
                inline=False,
            )

            log_embed.set_footer(
                text=f"Sistema de Logs • {interaction.guild.name}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            await log_channel.send(embed=log_embed)

        except Exception as e:
            print(f"❌ Erro no log do comando say: {e}")


async def setup(bot):
    await bot.add_cog(CommunicationSystem(bot))
