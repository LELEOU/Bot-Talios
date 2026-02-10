"""
Handler de Tickets - Sistema completo
Gerencia criação, fechamento, transcrições
"""

import io
import sys
from datetime import datetime
from pathlib import Path

import discord

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import database


class TicketHandler:
    """Handler completo para sistema de tickets"""

    def __init__(self, bot):
        self.bot = bot

    async def create_ticket(
        self, interaction: discord.Interaction, category_name: str = None, reason: str = None
    ):
        """Criar novo ticket"""
        try:
            guild = interaction.guild
            user = interaction.user

            # Verificar se usuário já tem ticket aberto
            existing_ticket = await database.get_user_open_ticket(str(guild.id), str(user.id))

            if existing_ticket:
                channel = guild.get_channel(int(existing_ticket["channel_id"]))
                if channel:
                    return await interaction.response.send_message(
                        f"❌ Você já possui um ticket aberto: {channel.mention}", ephemeral=True
                    )

            # Buscar ou criar categoria
            if category_name:
                category = discord.utils.get(guild.categories, name=category_name)
            else:
                category = discord.utils.get(guild.categories, name="🎫 Tickets")

            if not category:
                category = await guild.create_category("🎫 Tickets")

            # Criar canal do ticket
            ticket_number = await database.get_next_ticket_number(str(guild.id))

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                    add_reactions=True,
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    attach_files=True,
                    embed_links=True,
                    add_reactions=True,
                ),
            }

            # Adicionar roles de staff
            staff_roles = await self.get_staff_roles(guild)
            for role in staff_roles:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    attach_files=True,
                    embed_links=True,
                )

            channel_name = f"ticket-{ticket_number:04d}"

            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket de {user.display_name} - #{ticket_number}",
            )

            # Salvar no banco de dados
            ticket_id = await database.create_ticket(
                str(guild.id),
                str(user.id),
                str(ticket_channel.id),
                reason or "Suporte geral",
                ticket_number,
            )

            # Criar embed de boas-vindas
            embed = discord.Embed(
                title=f"🎫 Ticket #{ticket_number:04d}",
                description=f"Olá {user.mention}! Bem-vindo ao seu ticket de suporte.\\n\\n"
                "Nossa equipe irá ajudá-lo em breve. Por favor, descreva seu problema detalhadamente.",
                color=0x00FF00,
            )

            if reason:
                embed.add_field(name="📋 Motivo", value=reason, inline=False)

            embed.add_field(
                name="ℹ️ Instruções",
                value="• Explique sua situação claramente\\n"
                "• Seja paciente, responderemos em breve\\n"
                "• Use o botão abaixo para fechar o ticket",
                inline=False,
            )

            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"Criado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}")

            # Criar botões do ticket
            view = TicketView(self.bot)

            # Enviar mensagem inicial
            message = await ticket_channel.send(
                content=f"🎫 **Novo Ticket** | {user.mention}", embed=embed, view=view
            )

            # Fixar mensagem inicial
            await message.pin()

            # Notificar staff se configurado
            await self.notify_staff(guild, ticket_channel, user, reason)

            # Responder à interação
            await interaction.response.send_message(
                f"✅ Ticket criado com sucesso: {ticket_channel.mention}", ephemeral=True
            )

            return ticket_channel

        except Exception as e:
            print(f"❌ Erro criando ticket: {e}")
            await interaction.response.send_message(
                "❌ Erro ao criar ticket. Tente novamente.", ephemeral=True
            )
            return None

    async def close_ticket(self, interaction: discord.Interaction, reason: str = None):
        """Fechar ticket atual"""
        try:
            channel = interaction.channel

            # Verificar se é um canal de ticket
            ticket_data = await database.get_ticket_by_channel_id(str(channel.id))

            if not ticket_data:
                return await interaction.response.send_message(
                    "❌ Este não é um canal de ticket válido!", ephemeral=True
                )

            if ticket_data["status"] == "closed":
                return await interaction.response.send_message(
                    "❌ Este ticket já está fechado!", ephemeral=True
                )

            # Verificar permissões
            user = interaction.user
            ticket_owner = interaction.guild.get_member(int(ticket_data["user_id"]))

            if user != ticket_owner and not user.guild_permissions.manage_channels:
                return await interaction.response.send_message(
                    "❌ Você não tem permissão para fechar este ticket!", ephemeral=True
                )

            # Confirmar fechamento
            embed = discord.Embed(
                title="🔒 Fechar Ticket",
                description="Tem certeza de que deseja fechar este ticket?\\n\\n"
                "⚠️ **Esta ação não pode ser desfeita!**\\n"
                "Uma transcrição será salva automaticamente.",
                color=0xFF6600,
            )

            view = ConfirmCloseView(self.bot, reason)

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro fechando ticket: {e}")

    async def delete_ticket(
        self, channel: discord.TextChannel, closed_by: discord.Member, reason: str = None
    ):
        """Deletar ticket e criar transcrição"""
        try:
            # Buscar dados do ticket
            ticket_data = await database.get_ticket_by_channel_id(str(channel.id))

            if not ticket_data:
                return

            # Gerar transcrição
            transcript = await self.generate_transcript(channel, ticket_data)

            # Salvar transcrição no banco
            transcript_id = await database.save_ticket_transcript(
                ticket_data["ticket_id"],
                transcript,
                str(closed_by.id),
                reason or "Não especificado",
            )

            # Atualizar status do ticket
            await database.update_ticket_status(
                str(channel.id), "closed", str(closed_by.id), reason or "Ticket fechado"
            )

            # Enviar transcrição para o usuário (DM)
            ticket_owner = channel.guild.get_member(int(ticket_data["user_id"]))
            if ticket_owner:
                try:
                    await self.send_transcript_to_user(ticket_owner, ticket_data, transcript)
                except:
                    pass  # Ignorar se não conseguir enviar DM

            # Log do fechamento
            await self.log_ticket_closure(channel.guild, ticket_data, closed_by, reason)

            # Deletar canal
            await channel.delete(reason=f"Ticket fechado por {closed_by}")

            print(f"✅ Ticket #{ticket_data['ticket_number']} fechado por {closed_by}")

        except Exception as e:
            print(f"❌ Erro deletando ticket: {e}")

    async def generate_transcript(self, channel: discord.TextChannel, ticket_data: dict):
        """Gerar transcrição completa do ticket"""
        try:
            transcript_lines = []

            # Cabeçalho
            transcript_lines.append(
                f"=== TRANSCRIÇÃO DO TICKET #{ticket_data['ticket_number']:04d} ==="
            )
            transcript_lines.append(f"Servidor: {channel.guild.name}")
            transcript_lines.append(f"Canal: #{channel.name}")
            transcript_lines.append(
                f"Criado por: {channel.guild.get_member(int(ticket_data['user_id']))}"
            )
            transcript_lines.append(f"Criado em: {ticket_data['created_at']}")
            transcript_lines.append(f"Motivo: {ticket_data['reason']}")
            transcript_lines.append("=" * 50)
            transcript_lines.append("")

            # Buscar mensagens do canal
            messages = []
            async for message in channel.history(limit=None, oldest_first=True):
                messages.append(message)

            # Processar mensagens
            for message in messages:
                timestamp = message.created_at.strftime("%d/%m/%Y %H:%M:%S")
                author = f"{message.author.display_name} ({message.author.id})"

                transcript_lines.append(f"[{timestamp}] {author}:")

                if message.content:
                    # Quebrar linhas longas
                    content_lines = message.content.split("\\n")
                    for line in content_lines:
                        transcript_lines.append(f"  {line}")

                # Anexos
                if message.attachments:
                    transcript_lines.append(f"  [ANEXOS: {len(message.attachments)}]")
                    for attachment in message.attachments:
                        transcript_lines.append(f"    - {attachment.filename} ({attachment.url})")

                # Embeds
                if message.embeds:
                    transcript_lines.append(f"  [EMBEDS: {len(message.embeds)}]")
                    for embed in message.embeds:
                        if embed.title:
                            transcript_lines.append(f"    Título: {embed.title}")
                        if embed.description:
                            transcript_lines.append(f"    Descrição: {embed.description}")

                # Reações
                if message.reactions:
                    reactions = ", ".join(
                        [f"{reaction.emoji} ({reaction.count})" for reaction in message.reactions]
                    )
                    transcript_lines.append(f"  [REAÇÕES: {reactions}]")

                transcript_lines.append("")

            # Rodapé
            transcript_lines.append("=" * 50)
            transcript_lines.append(
                f"Transcrição gerada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            )

            return "\\n".join(transcript_lines)

        except Exception as e:
            print(f"❌ Erro gerando transcrição: {e}")
            return f"Erro ao gerar transcrição: {e}"

    async def send_transcript_to_user(
        self, user: discord.Member, ticket_data: dict, transcript: str
    ):
        """Enviar transcrição para o usuário via DM"""
        try:
            embed = discord.Embed(
                title=f"🎫 Transcrição do Ticket #{ticket_data['ticket_number']:04d}",
                description="Seu ticket foi fechado. Aqui está a transcrição completa.",
                color=0x0099FF,
            )

            embed.add_field(
                name="📋 Informações",
                value=f"**Servidor:** {user.guild.name}\\n"
                f"**Motivo:** {ticket_data['reason']}\\n"
                f"**Criado em:** {ticket_data['created_at']}",
                inline=False,
            )

            # Criar arquivo de transcrição
            transcript_file = discord.File(
                io.StringIO(transcript),
                filename=f"ticket_{ticket_data['ticket_number']:04d}_transcript.txt",
            )

            await user.send(embed=embed, file=transcript_file)

        except Exception as e:
            print(f"❌ Erro enviando transcrição: {e}")

    async def notify_staff(
        self,
        guild: discord.Guild,
        ticket_channel: discord.TextChannel,
        user: discord.Member,
        reason: str,
    ):
        """Notificar staff sobre novo ticket"""
        try:
            settings = await database.get_guild_settings(str(guild.id))

            if not settings or not settings.get("ticket_notifications", True):
                return

            # Buscar canal de notificações
            notification_channel_id = settings.get("ticket_notifications_channel_id")
            if notification_channel_id:
                notification_channel = guild.get_channel(int(notification_channel_id))
                if notification_channel:
                    embed = discord.Embed(
                        title="🎫 Novo Ticket Criado",
                        description=f"**Usuário:** {user.mention}\\n"
                        f"**Canal:** {ticket_channel.mention}\\n"
                        f"**Motivo:** {reason or 'Não especificado'}",
                        color=0x00FF00,
                        timestamp=datetime.now(),
                    )

                    embed.set_thumbnail(url=user.display_avatar.url)

                    # Mencionar roles de staff
                    staff_roles = await self.get_staff_roles(guild)
                    mentions = " ".join(
                        [role.mention for role in staff_roles[:3]]
                    )  # Máximo 3 roles

                    await notification_channel.send(
                        content=mentions if mentions else None, embed=embed
                    )

        except Exception as e:
            print(f"❌ Erro notificando staff: {e}")

    async def get_staff_roles(self, guild: discord.Guild):
        """Buscar roles de staff configuradas"""
        try:
            settings = await database.get_guild_settings(str(guild.id))

            staff_roles = []

            if settings and settings.get("staff_role_ids"):
                for role_id in settings["staff_role_ids"]:
                    role = guild.get_role(int(role_id))
                    if role:
                        staff_roles.append(role)

            # Fallback para roles padrão
            if not staff_roles:
                default_staff_names = ["Staff", "Moderator", "Admin", "Suporte", "Helper"]
                for name in default_staff_names:
                    role = discord.utils.get(guild.roles, name=name)
                    if role:
                        staff_roles.append(role)

            return staff_roles

        except Exception as e:
            print(f"❌ Erro buscando roles de staff: {e}")
            return []

    async def log_ticket_closure(
        self, guild: discord.Guild, ticket_data: dict, closed_by: discord.Member, reason: str
    ):
        """Logar fechamento do ticket"""
        try:
            settings = await database.get_guild_settings(str(guild.id))

            if not settings or not settings.get("ticket_logs_channel_id"):
                return

            log_channel = guild.get_channel(int(settings["ticket_logs_channel_id"]))
            if not log_channel:
                return

            ticket_owner = guild.get_member(int(ticket_data["user_id"]))

            embed = discord.Embed(
                title=f"🔒 Ticket #{ticket_data['ticket_number']:04d} Fechado",
                color=0xFF6600,
                timestamp=datetime.now(),
            )

            embed.add_field(
                name="Usuário",
                value=ticket_owner.mention if ticket_owner else "Usuário não encontrado",
                inline=True,
            )
            embed.add_field(name="Fechado por", value=closed_by.mention, inline=True)
            embed.add_field(name="Motivo Original", value=ticket_data["reason"], inline=False)
            embed.add_field(name="Motivo do Fechamento", value=reason, inline=False)
            embed.add_field(name="Criado em", value=ticket_data["created_at"], inline=True)

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro logando fechamento: {e}")


class TicketView(discord.ui.View):
    """View com botões para ticket"""

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="🔒 Fechar", style=discord.ButtonStyle.danger, custom_id="ticket_close"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        handler = TicketHandler(self.bot)
        await handler.close_ticket(interaction)

    @discord.ui.button(
        label="📋 Adicionar Usuário",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_add_user",
    )
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Implementar modal para adicionar usuário
        await interaction.response.send_message(
            "Funcionalidade em desenvolvimento!", ephemeral=True
        )


class ConfirmCloseView(discord.ui.View):
    """View de confirmação para fechamento"""

    def __init__(self, bot, reason: str = None):
        super().__init__(timeout=60)
        self.bot = bot
        self.reason = reason

    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.danger)
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        handler = TicketHandler(self.bot)
        await interaction.response.send_message("🔒 Fechando ticket...", ephemeral=True)
        await handler.delete_ticket(interaction.channel, interaction.user, self.reason)

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fechamento cancelado.", ephemeral=True)
        self.stop()
