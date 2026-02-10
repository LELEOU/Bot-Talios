"""
Comando Say - Communication
Faz o bot enviar mensagens com proteções avançadas
"""

import time

import discord
from discord import app_commands
from discord.ext import commands


class SayCommand(commands.Cog):
    """Sistema de comunicação via bot"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.mention_cooldowns = {}  # Cooldown para mentions @everyone/@here

    def check_mention_cooldown(self, user_id: int) -> int | None:
        """Verificar cooldown para mentions"""
        cooldown_key = f"say_mention_{user_id}"
        cooldown_time = 3 * 60  # 3 minutos

        if cooldown_key in self.mention_cooldowns:
            time_passed = time.time() - self.mention_cooldowns[cooldown_key]
            if time_passed < cooldown_time:
                return int(cooldown_time - time_passed)

        return None

    def set_mention_cooldown(self, user_id: int):
        """Definir cooldown para mentions"""
        cooldown_key = f"say_mention_{user_id}"
        self.mention_cooldowns[cooldown_key] = time.time()

    @app_commands.command(name="say", description="Faz o bot falar algo")
    @app_commands.describe(
        mensagem="Mensagem para o bot enviar",
        canal="Canal para enviar a mensagem (padrão: atual)",
        embed="Enviar como embed",
        responder="ID da mensagem para responder",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def say(
        self,
        interaction: discord.Interaction,
        mensagem: str,
        canal: discord.TextChannel | None = None,
        embed: bool = False,
        responder: str | None = None,
    ):
        """Fazer o bot enviar uma mensagem"""

        await interaction.response.defer(ephemeral=True)

        # Verificar permissões
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.followup.send("❌ Você não tem permissão para usar este comando.")
            return

        target_channel = canal or interaction.channel

        # Verificar se bot pode enviar mensagens no canal
        bot_perms = target_channel.permissions_for(interaction.guild.me)
        if not (bot_perms.send_messages and bot_perms.view_channel):
            await interaction.followup.send(
                "❌ Não tenho permissão para enviar mensagens neste canal."
            )
            return

        # Proteção contra @everyone/@here
        has_everyone_mention = "@everyone" in mensagem or "@here" in mensagem

        if has_everyone_mention:
            if not interaction.user.guild_permissions.mention_everyone:
                await interaction.followup.send(
                    "❌ Você não tem permissão para mencionar @everyone/@here. Use o comando `/announce` se necessário."
                )
                return

            # Verificar cooldown
            cooldown_remaining = self.check_mention_cooldown(interaction.user.id)
            if cooldown_remaining:
                minutes_left = cooldown_remaining // 60 + 1
                await interaction.followup.send(
                    f"❌ Aguarde **{minutes_left} minutos** antes de mencionar everyone/here novamente."
                )
                return

            # Aplicar cooldown
            self.set_mention_cooldown(interaction.user.id)

        # Verificar comprimento da mensagem
        if len(mensagem) > 2000 and not embed:
            await interaction.followup.send("❌ Mensagem muito longa! Use embed ou reduza o texto.")
            return

        try:
            # Preparar opções da mensagem
            message_kwargs = {}

            if embed:
                embed_obj = discord.Embed(
                    description=mensagem, color=0x0099FF, timestamp=discord.utils.utcnow()
                )
                message_kwargs["embed"] = embed_obj
            else:
                message_kwargs["content"] = mensagem

            # Configurar allowed_mentions
            if has_everyone_mention:
                message_kwargs["allowed_mentions"] = discord.AllowedMentions(
                    everyone=True, here=True
                )
            else:
                message_kwargs["allowed_mentions"] = discord.AllowedMentions(users=True, roles=True)

            # Lidar com reply se especificado
            if responder:
                try:
                    # Tentar converter para int se for numérico
                    if responder.isdigit():
                        reply_message = await target_channel.fetch_message(int(responder))
                        message_kwargs["reference"] = reply_message
                    else:
                        await interaction.followup.send("❌ ID da mensagem deve ser numérico.")
                        return

                except discord.NotFound:
                    await interaction.followup.send("❌ Mensagem para responder não encontrada.")
                    return
                except discord.HTTPException:
                    await interaction.followup.send("❌ ID da mensagem inválido.")
                    return

            # Enviar a mensagem
            sent_message = await target_channel.send(**message_kwargs)

            # Confirmação
            confirm_text = "✅ Mensagem enviada"
            if target_channel != interaction.channel:
                confirm_text += f" para {target_channel.mention}"
            confirm_text += "!"

            # Adicionar informações extras na confirmação
            confirm_embed = discord.Embed(
                title="📨 Mensagem Enviada", color=0x00FF00, timestamp=discord.utils.utcnow()
            )

            confirm_embed.add_field(name="📍 Canal", value=target_channel.mention, inline=True)

            confirm_embed.add_field(
                name="📝 Tipo", value="Embed" if embed else "Texto", inline=True
            )

            confirm_embed.add_field(
                name="🔗 Link", value=f"[Ir para mensagem]({sent_message.jump_url})", inline=True
            )

            if responder:
                confirm_embed.add_field(name="↩️ Respondendo", value=f"ID: {responder}", inline=True)

            if has_everyone_mention:
                confirm_embed.add_field(
                    name="⚠️ Aviso", value="Mensagem com @everyone/@here", inline=True
                )

            # Preview da mensagem (primeiras linhas)
            preview = mensagem[:200] + ("..." if len(mensagem) > 200 else "")
            confirm_embed.add_field(name="👁️ Preview", value=f"```{preview}```", inline=False)

            await interaction.followup.send(embed=confirm_embed)

            # Log da ação
            log_channels = ["mod-logs", "logs", "moderation", "moderacao"]
            log_channel = None

            for channel_name in log_channels:
                log_channel = discord.utils.get(interaction.guild.channels, name=channel_name)
                if log_channel and log_channel != target_channel:
                    break

            if log_channel and isinstance(log_channel, discord.TextChannel):
                log_embed = discord.Embed(
                    title="📢 Comando Say Usado", color=0x0099FF, timestamp=discord.utils.utcnow()
                )

                log_embed.add_field(name="👮 Moderador", value=str(interaction.user), inline=True)

                log_embed.add_field(name="📍 Canal", value=target_channel.mention, inline=True)

                log_embed.add_field(
                    name="📝 Tipo", value="Embed" if embed else "Texto", inline=True
                )

                # Conteúdo (limitado)
                content_preview = mensagem[:1000] + ("..." if len(mensagem) > 1000 else "")
                log_embed.add_field(
                    name="📄 Conteúdo", value=f"```{content_preview}```", inline=False
                )

                log_embed.add_field(
                    name="🔗 Link",
                    value=f"[Ir para mensagem]({sent_message.jump_url})",
                    inline=True,
                )

                if has_everyone_mention:
                    log_embed.add_field(
                        name="⚠️ Observação", value="Contém @everyone/@here", inline=True
                    )

                await log_channel.send(embed=log_embed)

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Não tenho permissão para enviar mensagens neste canal."
            )
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Erro ao enviar mensagem: `{e!s}`")
        except Exception as e:
            await interaction.followup.send(f"❌ Erro inesperado: `{e!s}`")

    @app_commands.command(name="edit", description="Edita uma mensagem do bot")
    @app_commands.describe(
        message_id="ID da mensagem para editar",
        nova_mensagem="Nova mensagem",
        canal="Canal onde está a mensagem (padrão: atual)",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def edit_message(
        self,
        interaction: discord.Interaction,
        message_id: str,
        nova_mensagem: str,
        canal: discord.TextChannel | None = None,
    ):
        """Editar uma mensagem do bot"""

        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.", ephemeral=True
            )
            return

        target_channel = canal or interaction.channel

        try:
            # Buscar a mensagem
            if not message_id.isdigit():
                await interaction.response.send_message(
                    "❌ ID da mensagem deve ser numérico.", ephemeral=True
                )
                return

            message = await target_channel.fetch_message(int(message_id))

            # Verificar se a mensagem é do bot
            if message.author != self.bot.user:
                await interaction.response.send_message(
                    "❌ Só posso editar minhas próprias mensagens!", ephemeral=True
                )
                return

            # Editar a mensagem
            if message.embeds:
                # Se era um embed, manter como embed
                embed = discord.Embed(
                    description=nova_mensagem, color=0x0099FF, timestamp=discord.utils.utcnow()
                )
                await message.edit(content=None, embed=embed)
            else:
                # Se era texto normal, manter como texto
                await message.edit(content=nova_mensagem)

            embed = discord.Embed(
                title="✅ Mensagem Editada",
                description="Mensagem editada com sucesso!",
                color=0x00FF00,
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(
                name="🔗 Link", value=f"[Ir para mensagem]({message.jump_url})", inline=True
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except discord.NotFound:
            await interaction.response.send_message("❌ Mensagem não encontrada.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao editar mensagem: `{e!s}`", ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(SayCommand(bot))
