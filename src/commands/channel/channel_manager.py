"""
Sistema de Gerenciamento de Canais
Lock e unlock de canais com logs avançados
"""

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class ChannelManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="channel-lock", description="🔒 Trancar canal para impedir mensagens"
    )
    @app_commands.describe(
        canal="Canal para trancar (padrão: canal atual)", motivo="Motivo do travamento"
    )
    async def channel_lock(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel | None = None,
        motivo: str | None = "Não especificado",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message(
                    "❌ **Permissão Insuficiente**\nVocê não tem permissão para gerenciar canais.",
                    ephemeral=True,
                )
                return

            target_channel = canal or interaction.channel

            # Verificar se é um canal de texto válido
            if not isinstance(target_channel, discord.TextChannel):
                await interaction.response.send_message(
                    "❌ **Canal Inválido**\nEste comando só pode ser usado em canais de texto.",
                    ephemeral=True,
                )
                return

            # Verificar permissões do bot
            bot_perms = target_channel.permissions_for(interaction.guild.me)
            if not bot_perms.manage_channels:
                await interaction.response.send_message(
                    f"❌ **Permissão do Bot**\n"
                    f"Não tenho permissão para gerenciar o canal {target_channel.mention}.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Verificar se já está trancado
            everyone_role = interaction.guild.default_role
            current_overwrites = target_channel.overwrites_for(everyone_role)

            if current_overwrites.send_messages is False:
                await interaction.followup.send(
                    f"❌ **Canal Já Trancado**\nO canal {target_channel.mention} já está trancado.",
                    ephemeral=True,
                )
                return

            try:
                # Trancar canal
                await target_channel.set_permissions(
                    everyone_role,
                    send_messages=False,
                    reason=f"Canal trancado por {interaction.user} ({interaction.user.id}): {motivo}",
                )

            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ **Erro de Permissão**\n"
                    "Não consegui trancar o canal. Verifique as permissões.",
                    ephemeral=True,
                )
                return
            except Exception as e:
                print(f"❌ Erro ao trancar canal: {e}")
                await interaction.followup.send(
                    "❌ **Erro do Sistema**\nOcorreu um erro ao trancar o canal.", ephemeral=True
                )
                return

            # Embed de confirmação
            lock_embed = discord.Embed(
                title="🔒 **CANAL TRANCADO**",
                description=f"O canal {target_channel.mention} foi trancado com sucesso!",
                color=0xFF0000,
                timestamp=datetime.now(),
            )

            lock_embed.add_field(
                name="👤 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user}`",
                inline=True,
            )

            lock_embed.add_field(name="📝 Motivo", value=f"```{motivo}```", inline=True)

            lock_embed.add_field(
                name="📍 Canal Afetado",
                value=f"{target_channel.mention}\n`#{target_channel.name}`",
                inline=False,
            )

            # Efeitos do travamento
            lock_embed.add_field(
                name="🛡️ Efeitos",
                value="• Membros normais não podem enviar mensagens\n"
                "• Reações ainda são permitidas\n"
                "• Moderadores podem continuar enviando mensagens\n"
                "• Use `/channel-unlock` para destrancar",
                inline=False,
            )

            lock_embed.set_footer(
                text=f"Sistema de Canais • {interaction.guild.name}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            await interaction.followup.send(embed=lock_embed, ephemeral=True)

            # Mensagem no canal trancado
            if target_channel != interaction.channel:
                try:
                    channel_lock_message = discord.Embed(
                        title="🔒 **CANAL TEMPORARIAMENTE TRANCADO**",
                        description="Este canal foi temporariamente trancado pela moderação.",
                        color=0xFF6B6B,
                        timestamp=datetime.now(),
                    )

                    channel_lock_message.add_field(
                        name="📋 Informações",
                        value=f"**Motivo:** {motivo}\n"
                        f"**Moderador:** {interaction.user.mention}\n"
                        f"**Data:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
                        inline=False,
                    )

                    channel_lock_message.add_field(
                        name="ℹ️ O que isso significa?",
                        value="• Você não pode enviar mensagens temporariamente\n"
                        "• Ainda pode ler as mensagens anteriores\n"
                        "• A moderação destravará quando apropriado\n"
                        "• Entre em contato com a moderação se necessário",
                        inline=False,
                    )

                    await target_channel.send(embed=channel_lock_message)

                except discord.Forbidden:
                    pass  # Se não conseguir enviar, continua silenciosamente

            # Log administrativo
            await self._log_channel_action(
                interaction, target_channel, "TRANCADO", motivo, 0xFF0000
            )

        except Exception as e:
            print(f"❌ Erro no comando channel-lock: {e}")
            try:
                await interaction.followup.send(
                    "❌ **Erro Crítico**\nOcorreu um erro inesperado ao trancar o canal.",
                    ephemeral=True,
                )
            except:
                try:
                    await interaction.response.send_message(
                        "❌ Erro ao processar comando.", ephemeral=True
                    )
                except:
                    pass

    @app_commands.command(
        name="channel-unlock", description="🔓 Destrancar canal para permitir mensagens"
    )
    @app_commands.describe(
        canal="Canal para destrancar (padrão: canal atual)", motivo="Motivo do destravamento"
    )
    async def channel_unlock(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel | None = None,
        motivo: str | None = "Não especificado",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message(
                    "❌ **Permissão Insuficiente**\nVocê não tem permissão para gerenciar canais.",
                    ephemeral=True,
                )
                return

            target_channel = canal or interaction.channel

            # Verificar se é um canal de texto válido
            if not isinstance(target_channel, discord.TextChannel):
                await interaction.response.send_message(
                    "❌ **Canal Inválido**\nEste comando só pode ser usado em canais de texto.",
                    ephemeral=True,
                )
                return

            # Verificar permissões do bot
            bot_perms = target_channel.permissions_for(interaction.guild.me)
            if not bot_perms.manage_channels:
                await interaction.response.send_message(
                    f"❌ **Permissão do Bot**\n"
                    f"Não tenho permissão para gerenciar o canal {target_channel.mention}.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Verificar se está trancado
            everyone_role = interaction.guild.default_role
            current_overwrites = target_channel.overwrites_for(everyone_role)

            if current_overwrites.send_messages is not False:
                await interaction.followup.send(
                    f"❌ **Canal Não Trancado**\n"
                    f"O canal {target_channel.mention} não está trancado.",
                    ephemeral=True,
                )
                return

            try:
                # Destrancar canal (remover override)
                await target_channel.set_permissions(
                    everyone_role,
                    send_messages=None,  # Remove a override, volta ao padrão
                    reason=f"Canal destrancado por {interaction.user} ({interaction.user.id}): {motivo}",
                )

            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ **Erro de Permissão**\n"
                    "Não consegui destrancar o canal. Verifique as permissões.",
                    ephemeral=True,
                )
                return
            except Exception as e:
                print(f"❌ Erro ao destrancar canal: {e}")
                await interaction.followup.send(
                    "❌ **Erro do Sistema**\nOcorreu um erro ao destrancar o canal.", ephemeral=True
                )
                return

            # Embed de confirmação
            unlock_embed = discord.Embed(
                title="🔓 **CANAL DESTRANCADO**",
                description=f"O canal {target_channel.mention} foi destrancado com sucesso!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            unlock_embed.add_field(
                name="👤 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user}`",
                inline=True,
            )

            unlock_embed.add_field(name="📝 Motivo", value=f"```{motivo}```", inline=True)

            unlock_embed.add_field(
                name="📍 Canal Afetado",
                value=f"{target_channel.mention}\n`#{target_channel.name}`",
                inline=False,
            )

            # Efeitos do destravamento
            unlock_embed.add_field(
                name="✅ Efeitos",
                value="• Membros podem enviar mensagens novamente\n"
                "• Todas as funções normais do canal restauradas\n"
                "• Canal está totalmente funcional\n"
                "• Use `/channel-lock` para trancar novamente",
                inline=False,
            )

            unlock_embed.set_footer(
                text=f"Sistema de Canais • {interaction.guild.name}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            await interaction.followup.send(embed=unlock_embed, ephemeral=True)

            # Mensagem no canal destrancado
            if target_channel != interaction.channel:
                try:
                    channel_unlock_message = discord.Embed(
                        title="🔓 **CANAL DESTRANCADO**",
                        description="Este canal foi destrancado e está novamente disponível!",
                        color=0x00FF00,
                        timestamp=datetime.now(),
                    )

                    channel_unlock_message.add_field(
                        name="📋 Informações",
                        value=f"**Motivo:** {motivo}\n"
                        f"**Moderador:** {interaction.user.mention}\n"
                        f"**Data:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
                        inline=False,
                    )

                    channel_unlock_message.add_field(
                        name="✅ Você pode novamente:",
                        value="• Enviar mensagens normalmente\n"
                        "• Usar comandos do bot\n"
                        "• Participar de conversas\n"
                        "• Compartilhar mídias e links",
                        inline=False,
                    )

                    channel_unlock_message.add_field(
                        name="📋 Lembrete",
                        value="Mantenha o respeito e siga as regras do servidor!",
                        inline=False,
                    )

                    await target_channel.send(embed=channel_unlock_message)

                except discord.Forbidden:
                    pass  # Se não conseguir enviar, continua silenciosamente

            # Log administrativo
            await self._log_channel_action(
                interaction, target_channel, "DESTRANCADO", motivo, 0x00FF00
            )

        except Exception as e:
            print(f"❌ Erro no comando channel-unlock: {e}")
            try:
                await interaction.followup.send(
                    "❌ **Erro Crítico**\nOcorreu um erro inesperado ao destrancar o canal.",
                    ephemeral=True,
                )
            except:
                try:
                    await interaction.response.send_message(
                        "❌ Erro ao processar comando.", ephemeral=True
                    )
                except:
                    pass

    async def _log_channel_action(self, interaction, channel, action, reason, color):
        """Log de ações de canal"""
        try:
            # Procurar canal de logs
            log_channel = None
            for channel_name in ["mod-logs", "logs", "audit-logs", "moderacao"]:
                log_channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
                if log_channel:
                    break

            if not log_channel:
                return

            # Verificar permissões
            if not log_channel.permissions_for(interaction.guild.me).send_messages:
                return

            # Criar embed de log
            log_embed = discord.Embed(
                title=f"🔧 **CANAL {action}**", color=color, timestamp=datetime.now()
            )

            log_embed.add_field(
                name="👤 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user} ({interaction.user.id})`",
                inline=True,
            )

            log_embed.add_field(
                name="📍 Canal",
                value=f"{channel.mention}\n`#{channel.name} ({channel.id})`",
                inline=True,
            )

            log_embed.add_field(name="📝 Motivo", value=f"```{reason}```", inline=False)

            log_embed.add_field(
                name="🕐 Horário",
                value=f"{datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
                inline=True,
            )

            log_embed.set_footer(
                text=f"Sistema de Logs • {interaction.guild.name}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            await log_channel.send(embed=log_embed)

        except Exception as e:
            print(f"❌ Erro no log de canal: {e}")


async def setup(bot):
    await bot.add_cog(ChannelManager(bot))
