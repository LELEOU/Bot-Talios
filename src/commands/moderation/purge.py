"""
Comando Purge - Moderation
Sistema completo de limpeza de mensagens
"""

import asyncio
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands


class PurgeCommand(commands.Cog):
    """Sistema de limpeza de mensagens"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="purge", description="Deleta múltiplas mensagens de um canal")
    @app_commands.describe(
        quantidade="Quantidade de mensagens (1-100)",
        usuario="Deletar apenas mensagens de um usuário específico",
        canal="Canal para limpar (padrão: canal atual)",
        motivo="Motivo da limpeza",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def purge(
        self,
        interaction: discord.Interaction,
        quantidade: app_commands.Range[int, 1, 100],
        usuario: discord.User | None = None,
        canal: discord.TextChannel | None = None,
        motivo: str = "Não especificado",
    ):
        """Limpar mensagens de um canal"""

        # Verificar permissões do usuário
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Você não tem permissão para gerenciar mensagens.", ephemeral=True
            )
            return

        # Usar canal atual se não especificado
        target_channel = canal or interaction.channel

        # Verificar se é um canal de texto
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em canais de texto.", ephemeral=True
            )
            return

        # Verificar permissões do bot no canal
        bot_perms = target_channel.permissions_for(interaction.guild.me)
        if not (bot_perms.manage_messages and bot_perms.read_message_history):
            await interaction.response.send_message(
                "❌ Não tenho permissão para gerenciar mensagens neste canal.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Buscar mensagens
            messages = []
            async for message in target_channel.history(limit=quantidade):
                messages.append(message)

            if not messages:
                await interaction.followup.send(
                    "❌ Nenhuma mensagem encontrada para deletar.", ephemeral=True
                )
                return

            # Filtrar por usuário se especificado
            if usuario:
                messages = [msg for msg in messages if msg.author.id == usuario.id]

                if not messages:
                    await interaction.followup.send(
                        f"❌ Nenhuma mensagem de {usuario.mention} encontrada.", ephemeral=True
                    )
                    return

            # Separar mensagens por idade (Discord não permite bulk delete de mensagens > 14 dias)
            now = discord.utils.utcnow()
            two_weeks_ago = now - timedelta(days=14)

            recent_messages = [msg for msg in messages if msg.created_at > two_weeks_ago]
            old_messages = [msg for msg in messages if msg.created_at <= two_weeks_ago]

            deleted_count = 0

            # Deletar mensagens recentes em bulk
            if recent_messages:
                if len(recent_messages) == 1:
                    # Uma mensagem - deletar individualmente
                    await recent_messages[0].delete()
                    deleted_count = 1
                else:
                    # Múltiplas mensagens - bulk delete
                    deleted = await target_channel.delete_messages(recent_messages)
                    deleted_count = len(
                        recent_messages
                    )  # bulk_delete não retorna count em discord.py

            # Deletar mensagens antigas individualmente
            if old_messages:
                for message in old_messages:
                    try:
                        await message.delete()
                        deleted_count += 1
                        # Rate limit para evitar spam
                        await asyncio.sleep(0.5)
                    except discord.NotFound:
                        # Mensagem já foi deletada
                        pass
                    except discord.Forbidden:
                        # Sem permissão para deletar esta mensagem
                        pass
                    except Exception as e:
                        print(f"Erro deletando mensagem antiga: {e}")

            # Criar embed de resultado
            embed = discord.Embed(
                title="🧹 Mensagens Deletadas",
                description=f"**{deleted_count}** mensagens foram deletadas com sucesso.",
                color=0xFF9900,
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(name="📊 Quantidade", value=str(deleted_count), inline=True)
            embed.add_field(name="📍 Canal", value=target_channel.mention, inline=True)
            embed.add_field(name="👮 Moderador", value=interaction.user.mention, inline=True)

            if usuario:
                embed.add_field(name="👤 Usuário Filtrado", value=usuario.mention, inline=True)

            if old_messages:
                embed.add_field(
                    name="⚠️ Aviso",
                    value=f"{len(old_messages)} mensagens antigas foram deletadas individualmente.",
                    inline=False,
                )

            embed.add_field(name="📝 Motivo", value=motivo, inline=False)

            # Informações adicionais
            if len(messages) != deleted_count:
                failed_count = len(messages) - deleted_count
                embed.add_field(
                    name="❌ Falhas",
                    value=f"{failed_count} mensagens não puderam ser deletadas",
                    inline=True,
                )

            embed.set_footer(
                text=f"Executado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

            # Log da ação no canal de moderação
            log_channels = ["mod-logs", "logs", "moderation", "moderacao"]
            log_channel = None

            for channel_name in log_channels:
                log_channel = discord.utils.get(interaction.guild.channels, name=channel_name)
                if log_channel and log_channel != target_channel:
                    break

            if log_channel and isinstance(log_channel, discord.TextChannel):
                log_embed = discord.Embed(
                    title="🧹 Purge Executado", color=0xFF9900, timestamp=discord.utils.utcnow()
                )

                log_embed.add_field(name="📍 Canal", value=target_channel.mention, inline=True)
                log_embed.add_field(name="👮 Moderador", value=str(interaction.user), inline=True)
                log_embed.add_field(
                    name="🗑️ Mensagens Deletadas", value=str(deleted_count), inline=True
                )

                if usuario:
                    log_embed.add_field(name="👤 Usuário Filtrado", value=str(usuario), inline=True)

                log_embed.add_field(name="📝 Motivo", value=motivo, inline=False)

                # Estatísticas adicionais
                if recent_messages or old_messages:
                    stats_text = []
                    if recent_messages:
                        stats_text.append(f"Recentes: {len(recent_messages)}")
                    if old_messages:
                        stats_text.append(f"Antigas: {len(old_messages)}")

                    log_embed.add_field(
                        name="📊 Detalhes", value=" | ".join(stats_text), inline=False
                    )

                await log_channel.send(embed=log_embed)

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Não tenho permissão para deletar mensagens neste canal.", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao deletar mensagens: `{e!s}`", ephemeral=True
            )

    @app_commands.command(name="purge-bots", description="Remove mensagens de bots")
    @app_commands.describe(
        quantidade="Quantidade de mensagens para verificar (1-100)",
        canal="Canal para limpar (padrão: canal atual)",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def purge_bots(
        self,
        interaction: discord.Interaction,
        quantidade: app_commands.Range[int, 1, 100] = 50,
        canal: discord.TextChannel | None = None,
    ):
        """Remover mensagens de bots"""

        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Você não tem permissão para gerenciar mensagens.", ephemeral=True
            )
            return

        target_channel = canal or interaction.channel

        await interaction.response.defer(ephemeral=True)

        try:
            bot_messages = []
            async for message in target_channel.history(limit=quantidade):
                if message.author.bot:
                    bot_messages.append(message)

            if not bot_messages:
                await interaction.followup.send(
                    "❌ Nenhuma mensagem de bot encontrada.", ephemeral=True
                )
                return

            # Deletar mensagens de bots
            deleted_count = 0
            for message in bot_messages:
                try:
                    await message.delete()
                    deleted_count += 1
                    await asyncio.sleep(0.3)  # Rate limit
                except:
                    pass

            embed = discord.Embed(
                title="🤖 Mensagens de Bots Removidas",
                description=f"**{deleted_count}** mensagens de bots foram deletadas.",
                color=0x00FF00,
                timestamp=discord.utils.utcnow(),
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: `{e!s}`", ephemeral=True)


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(PurgeCommand(bot))
