"""
Sistema de Tickets - Criar Ticket
Comando para criar e gerenciar sistema de tickets
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class TicketView(discord.ui.View):
    """Interface persistente para criar tickets"""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📩 Criar Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="create_ticket_button",
    )
    async def create_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            # 🔍 VERIFICAR SE JÁ TEM TICKET ABERTO
            existing_ticket: discord.TextChannel | None = None
            for channel in interaction.guild.text_channels:
                if channel.name.startswith("ticket-") and str(interaction.user.id) in channel.name:
                    existing_ticket = channel
                    break

            if existing_ticket:
                await interaction.response.send_message(
                    f"❌ Você já possui um ticket aberto: {existing_ticket.mention}\n"
                    f"**📱 Use apenas um ticket por vez.**",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # 🎫 CRIAR CANAL DO TICKET
            ticket_name: str = (
                f"ticket-{interaction.user.name.lower().replace(' ', '-')}-{interaction.user.id}"
            )

            # 🔐 CONFIGURAR PERMISSÕES
            overwrites: dict[discord.Role | discord.Member, discord.PermissionOverwrite] = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    read_messages=False
                ),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                    read_message_history=True,
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                    manage_messages=True,
                    add_reactions=True,
                    manage_channels=True,
                ),
            }

            # Adicionar permissões para admins
            for member in interaction.guild.members:
                if member.guild_permissions.administrator:
                    overwrites[member] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        attach_files=True,
                        embed_links=True,
                        manage_messages=True,
                    )

            # 📂 ENCONTRAR OU CRIAR CATEGORIA
            category: discord.CategoryChannel | None = None
            for cat in interaction.guild.categories:
                if "ticket" in cat.name.lower():
                    category = cat
                    break

            if not category:
                try:
                    category = await interaction.guild.create_category(
                        "🎫 Tickets",
                        overwrites={
                            interaction.guild.default_role: discord.PermissionOverwrite(
                                read_messages=False
                            )
                        },
                    )
                except discord.Forbidden:
                    pass

            # 🆕 CRIAR CANAL
            ticket_channel: discord.TextChannel = await interaction.guild.create_text_channel(
                name=ticket_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket de {interaction.user} • Criado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            )

            # 🎨 EMBED INICIAL DO TICKET
            ticket_embed: discord.Embed = discord.Embed(
                title="🎫 **TICKET CRIADO!**",
                description=f"Olá {interaction.user.mention}! Bem-vindo ao seu ticket de suporte.\n\n"
                f"📋 **Como funciona:**\n"
                f"• Descreva sua dúvida ou problema\n"
                f"• Nossa equipe responderá em breve\n"
                f"• Use o botão 🗑️ para fechar quando resolvido\n\n"
                f"🔔 **Status:** Aguardando resposta\n"
                f"⏰ **Criado:** <t:{int(datetime.now().timestamp())}:F>",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            ticket_embed.add_field(
                name="👤 Usuário",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            ticket_embed.add_field(
                name="📊 Informações",
                value=f"**Canal:** {ticket_channel.mention}\n"
                f"**ID:** `{ticket_channel.id}`\n"
                f"**Categoria:** {category.name if category else 'Sem categoria'}",
                inline=True,
            )

            ticket_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            ticket_embed.set_footer(
                text=f"Ticket #{ticket_channel.id} • Use /ticket-close para fechar",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            # 🎮 CRIAR VIEW DO TICKET
            ticket_control_view: TicketControlView = TicketControlView()

            # 📨 ENVIAR MENSAGEM INICIAL
            initial_message: discord.Message = await ticket_channel.send(
                f"🎫 **Ticket criado!** {interaction.user.mention}",
                embed=ticket_embed,
                view=ticket_control_view,
            )

            # 📌 PIN DA MENSAGEM
            try:
                await initial_message.pin()
            except:
                pass

            # 💾 SALVAR NO BANCO DE DADOS
            try:
                from ...utils.database import database

                await database.execute(
                    """INSERT INTO tickets 
                       (channel_id, user_id, guild_id, created_at, status, initial_message_id) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        str(ticket_channel.id),
                        str(interaction.user.id),
                        str(interaction.guild.id),
                        datetime.now().isoformat(),
                        "open",
                        str(initial_message.id),
                    ),
                )
            except Exception as e:
                print(f"❌ Erro ao salvar ticket no banco: {e}")

            # ✅ CONFIRMAÇÃO PARA O USUÁRIO
            await interaction.followup.send(
                f"✅ **Ticket criado com sucesso!**\n\n"
                f"📍 **Canal:** {ticket_channel.mention}\n"
                f"🎯 **Próximos passos:** Descreva seu problema no canal do ticket.\n"
                f"⏱️ **Tempo de resposta:** Normalmente até 24 horas.",
                ephemeral=True,
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Não tenho permissão para criar canais! Contate um administrador.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Erro ao criar ticket: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao criar ticket. Tente novamente ou contate um administrador.",
                    ephemeral=True,
                )
            except:
                pass


class TicketControlView(discord.ui.View):
    """Interface de controle do ticket"""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🗑️ Fechar",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="close_ticket_button",
    )
    async def close_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            # 🛡️ VERIFICAR PERMISSÕES
            is_ticket_owner: bool = str(interaction.user.id) in interaction.channel.name
            is_admin: bool = interaction.user.guild_permissions.administrator
            is_manage_channels: bool = interaction.user.guild_permissions.manage_channels

            if not (is_ticket_owner or is_admin or is_manage_channels):
                await interaction.response.send_message(
                    "❌ Apenas o dono do ticket ou administradores podem fechá-lo!",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # 📝 CRIAR TRANSCRIPT SIMPLES
            transcript_data: list[dict[str, Any]] = []

            async for message in interaction.channel.history(limit=None, oldest_first=True):
                if not message.author.bot or message.embeds or message.attachments:
                    transcript_data.append(
                        {
                            "author": str(message.author),
                            "content": message.content,
                            "timestamp": message.created_at.isoformat(),
                            "attachments": [att.url for att in message.attachments],
                            "embeds": len(message.embeds) > 0,
                        }
                    )

            # 💾 SALVAR TRANSCRIPT
            transcript_filename: str = (
                f"ticket-{interaction.channel.name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            )

            # 🎨 EMBED DE FECHAMENTO
            close_embed: discord.Embed = discord.Embed(
                title="🔒 **TICKET FECHADO!**",
                description=f"Este ticket foi fechado por {interaction.user.mention}.\n\n"
                f"📊 **Estatísticas:**\n"
                f"• **Mensagens:** {len(transcript_data)}\n"
                f"• **Duração:** <t:{int(datetime.now().timestamp())}:R>\n"
                f"• **Fechado em:** <t:{int(datetime.now().timestamp())}:F>",
                color=0xFF0000,
                timestamp=datetime.now(),
            )

            close_embed.set_footer(
                text="Ticket será deletado em 10 segundos",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            # 📨 ENVIAR AVISO DE FECHAMENTO
            await interaction.followup.send(embed=close_embed)

            # 💾 ATUALIZAR BANCO DE DADOS
            try:
                from ...utils.database import database

                await database.execute(
                    "UPDATE tickets SET status = 'closed', closed_at = ?, closed_by = ? WHERE channel_id = ?",
                    (
                        datetime.now().isoformat(),
                        str(interaction.user.id),
                        str(interaction.channel.id),
                    ),
                )
            except Exception as e:
                print(f"❌ Erro ao atualizar ticket no banco: {e}")

            # ⏳ AGUARDAR E DELETAR
            await asyncio.sleep(10)
            await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user}")

        except Exception as e:
            print(f"❌ Erro ao fechar ticket: {e}")

    @discord.ui.button(
        label="📋 Transcript",
        style=discord.ButtonStyle.secondary,
        emoji="📄",
        custom_id="transcript_ticket_button",
    )
    async def create_transcript(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # 📝 CRIAR TRANSCRIPT DETALHADO
            transcript_lines: list[str] = []
            transcript_lines.append(f"# TRANSCRIPT DO TICKET: {interaction.channel.name}")
            transcript_lines.append(
                f"# Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            )
            transcript_lines.append(f"# Por: {interaction.user}")
            transcript_lines.append("=" * 50)
            transcript_lines.append("")

            message_count: int = 0
            async for message in interaction.channel.history(limit=None, oldest_first=True):
                if message.author.bot and not message.embeds and not message.content.strip():
                    continue

                message_count += 1
                timestamp: str = message.created_at.strftime("%d/%m/%Y %H:%M:%S")
                transcript_lines.append(f"[{timestamp}] {message.author}: {message.content}")

                if message.attachments:
                    for attachment in message.attachments:
                        transcript_lines.append(f"    📎 Anexo: {attachment.url}")

                if message.embeds:
                    transcript_lines.append(f"    📋 Embed: {len(message.embeds)} embed(s)")

                transcript_lines.append("")

            transcript_lines.append("=" * 50)
            transcript_lines.append(f"Total de mensagens: {message_count}")

            # 💾 CRIAR ARQUIVO
            transcript_content: str = "\n".join(transcript_lines)

            # 📁 CRIAR ARQUIVO TEMPORÁRIO
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".txt", encoding="utf-8"
            ) as f:
                f.write(transcript_content)
                temp_file_path: str = f.name

            # 📨 ENVIAR ARQUIVO
            with open(temp_file_path, "rb") as f:
                file: discord.File = discord.File(
                    f,
                    filename=f"transcript-{interaction.channel.name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt",
                )

                transcript_embed: discord.Embed = discord.Embed(
                    title="📋 Transcript Gerado!",
                    description=f"**Canal:** {interaction.channel.mention}\n"
                    f"**Mensagens:** {message_count}\n"
                    f"**Gerado por:** {interaction.user.mention}\n"
                    f"**Data:** <t:{int(datetime.now().timestamp())}:F>",
                    color=0x2F3136,
                    timestamp=datetime.now(),
                )

                await interaction.followup.send(
                    embed=transcript_embed, file=file, ephemeral=True
                )

            # 🗑️ LIMPAR ARQUIVO TEMPORÁRIO
            os.unlink(temp_file_path)

        except Exception as e:
            print(f"❌ Erro ao criar transcript: {e}")
            await interaction.followup.send(
                "❌ Erro ao gerar transcript. Tente novamente.", ephemeral=True
            )


class TicketCreate(commands.Cog):
    """Sistema de criação e setup de tickets"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(
        name="ticket-setup", description="🎫 Configurar sistema de tickets no canal"
    )
    @app_commands.describe(
        titulo="Título da mensagem de criação de tickets",
        descricao="Descrição/instruções para os usuários",
    )
    async def ticket_setup(
        self,
        interaction: discord.Interaction,
        titulo: str | None = None,
        descricao: str | None = None,
    ) -> None:
        """Configura sistema de tickets com painel embed"""
        try:
            # 🛡️ VERIFICAR PERMISSÕES
            if not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para configurar tickets. **Necessário**: Gerenciar Canais",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # 🎨 CONFIGURAR MENSAGEM
            title: str = titulo or "🎫 **SISTEMA DE TICKETS**"
            description: str = descricao or (
                "Precisa de ajuda? Crie um ticket de suporte!\n\n"
                "🎯 **Como funciona:**\n"
                "• Clique no botão 📩 **Criar Ticket**\n"
                "• Um canal privado será criado para você\n"
                "• Descreva sua dúvida ou problema\n"
                "• Nossa equipe responderá em breve\n\n"
                "⚠️ **Regras:**\n"
                "• Use apenas para assuntos importantes\n"
                "• Seja educado e respeitoso\n"
                "• Aguarde nossa resposta\n"
                "• Feche o ticket quando resolvido"
            )

            # 📋 EMBED PRINCIPAL
            setup_embed: discord.Embed = discord.Embed(
                title=title, description=description, color=0x2F3136, timestamp=datetime.now()
            )

            setup_embed.add_field(
                name="📞 Suporte Disponível",
                value="Segunda a Sexta: 24h\nFim de semana: Resposta em até 48h",
                inline=True,
            )

            setup_embed.add_field(
                name="⏱️ Tempo de Resposta",
                value="Normal: Até 24 horas\nUrgente: Até 6 horas",
                inline=True,
            )

            setup_embed.add_field(
                name="🎯 Tipos de Suporte",
                value="• Dúvidas gerais\n• Problemas técnicos\n• Reportar bugs\n• Sugestões",
                inline=False,
            )

            setup_embed.set_footer(
                text=f"Sistema configurado por {interaction.user} • Clique no botão abaixo",
                icon_url=interaction.user.display_avatar.url,
            )

            if interaction.guild.icon:
                setup_embed.set_thumbnail(url=interaction.guild.icon.url)

            # 🎮 CRIAR VIEW PERSISTENTE
            view: TicketView = TicketView()

            # 📨 ENVIAR MENSAGEM DE SETUP
            await interaction.channel.send(embed=setup_embed, view=view)

            # ✅ CONFIRMAÇÃO
            success_embed: discord.Embed = discord.Embed(
                title="✅ Sistema de Tickets Configurado!",
                description=f"O sistema foi instalado no canal {interaction.channel.mention}",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="🎯 Próximos passos",
                value="• Os usuários podem clicar no botão para criar tickets\n"
                "• Canais serão criados automaticamente\n"
                "• Use `/ticket-list` para gerenciar tickets",
                inline=False,
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando ticket-setup: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao configurar sistema de tickets. Tente novamente.",
                    ephemeral=True,
                )
            except:
                pass


async def setup(bot: commands.Bot) -> None:
    """Carrega o cog e views persistentes"""
    await bot.add_cog(TicketCreate(bot))

    # Adicionar views persistentes
    bot.add_view(TicketView())
    bot.add_view(TicketControlView())
