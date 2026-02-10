"""
Creator Leaves Handler - Gerencia quando criador de ticket sai
Trata situações quando criador de ticket deixa o servidor
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import database


class CreatorLeavesHandler(commands.Cog):
    """Handler para quando criador de ticket sai do servidor"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Executado quando membro sai do servidor"""
        try:
            # Verificar se o membro tem tickets ativos
            tickets = await self.get_user_active_tickets(member.guild.id, member.id)

            for ticket in tickets:
                await self.handle_creator_left_ticket(ticket, member)

        except Exception as e:
            print(f"❌ Erro no creator leaves handler: {e}")

    async def get_user_active_tickets(self, guild_id: int, user_id: int) -> list:
        """Buscar tickets ativos do usuário"""
        try:
            result = await database.fetchall(
                """SELECT * FROM tickets 
                   WHERE guild_id = ? AND creator_id = ? AND status = 'open'""",
                (str(guild_id), str(user_id)),
            )
            return result or []

        except Exception as e:
            print(f"❌ Erro buscando tickets do usuário: {e}")
            return []

    async def handle_creator_left_ticket(self, ticket: dict, member: discord.Member):
        """Tratar ticket quando criador sai"""
        try:
            # Buscar canal do ticket
            channel = self.bot.get_channel(int(ticket["channel_id"]))
            if not channel:
                return

            # Buscar configuração de tickets
            config = await self.get_ticket_config(member.guild.id)

            # Criar embed de notificação
            embed = discord.Embed(
                title="👋 Criador do Ticket Saiu",
                description=f"O criador deste ticket **{member}** saiu do servidor.",
                color=0xFF9900,
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(name="👤 Usuário", value=f"**{member}** (`{member.id}`)", inline=True)

            embed.add_field(name="🎫 Ticket", value=f"#{channel.name}", inline=True)

            embed.add_field(
                name="📅 Criado em",
                value=f"<t:{int(discord.utils.parse_time(ticket['created_at']).timestamp())}:R>",
                inline=True,
            )

            # Determinar ação baseada na configuração
            action = config.get("creator_leaves_action", "notify")

            if action == "close":
                embed.add_field(
                    name="⚡ Ação", value="🔒 Ticket será fechado automaticamente", inline=False
                )

                # Fechar ticket automaticamente
                await self.auto_close_ticket(ticket, channel, member)

            elif action == "transfer":
                # Transferir para staff
                staff_role_id = config.get("staff_role_id")
                if staff_role_id:
                    staff_role = member.guild.get_role(int(staff_role_id))
                    if staff_role:
                        embed.add_field(
                            name="⚡ Ação",
                            value=f"📋 Ticket transferido para {staff_role.mention}",
                            inline=False,
                        )

                        await self.transfer_ticket_to_staff(ticket, channel, staff_role)
            else:
                # Apenas notificar
                embed.add_field(
                    name="⚡ Ação",
                    value="📢 Equipe notificada - Ticket permanece aberto",
                    inline=False,
                )

            # Enviar notificação no canal do ticket
            await channel.send(embed=embed)

            # Notificar staff se configurado
            await self.notify_staff(member.guild, config, ticket, member, action)

        except Exception as e:
            print(f"❌ Erro tratando saída do criador: {e}")

    async def get_ticket_config(self, guild_id: int) -> dict:
        """Buscar configuração de tickets"""
        try:
            result = await database.fetchone(
                "SELECT * FROM ticket_config WHERE guild_id = ?", (str(guild_id),)
            )

            if result:
                return {
                    "creator_leaves_action": result.get("creator_leaves_action", "notify"),
                    "staff_role_id": result.get("staff_role_id"),
                    "log_channel_id": result.get("log_channel_id"),
                    "auto_close_time": result.get("auto_close_time", 24),  # horas
                }

            return {}

        except Exception as e:
            print(f"❌ Erro buscando config de tickets: {e}")
            return {}

    async def auto_close_ticket(
        self, ticket: dict, channel: discord.TextChannel, member: discord.Member
    ):
        """Fechar ticket automaticamente"""
        try:
            # Atualizar status no banco
            await database.run(
                "UPDATE tickets SET status = 'closed', closed_by = ?, closed_at = ? WHERE id = ?",
                ("system", discord.utils.utcnow().isoformat(), ticket["id"]),
            )

            # Criar transcript se necessário
            await self.create_ticket_transcript(ticket, channel, "Criador saiu do servidor")

            # Aguardar um pouco antes de deletar
            await channel.send(
                "🔒 Este ticket será fechado em 30 segundos devido à saída do criador...",
                delete_after=30,
            )

            await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=30))

            # Deletar canal
            await channel.delete(reason="Ticket fechado - criador saiu do servidor")

        except Exception as e:
            print(f"❌ Erro fechando ticket automaticamente: {e}")

    async def transfer_ticket_to_staff(
        self, ticket: dict, channel: discord.TextChannel, staff_role: discord.Role
    ):
        """Transferir ticket para equipe"""
        try:
            # Atualizar permissões do canal
            await channel.set_permissions(
                staff_role, read_messages=True, send_messages=True, view_channel=True
            )

            # Atualizar banco de dados
            await database.run(
                "UPDATE tickets SET assigned_to = ? WHERE id = ?",
                (str(staff_role.id), ticket["id"]),
            )

            # Mencionar equipe
            await channel.send(
                f"📋 {staff_role.mention} Este ticket foi transferido para vocês devido à saída do criador."
            )

        except Exception as e:
            print(f"❌ Erro transferindo ticket: {e}")

    async def notify_staff(
        self, guild: discord.Guild, config: dict, ticket: dict, member: discord.Member, action: str
    ):
        """Notificar equipe sobre saída do criador"""
        try:
            log_channel_id = config.get("log_channel_id")
            if not log_channel_id:
                return

            log_channel = guild.get_channel(int(log_channel_id))
            if not log_channel:
                return

            embed = discord.Embed(
                title="⚠️ Alerta - Criador de Ticket Saiu",
                color=0xFF9900,
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(name="👤 Usuário", value=f"**{member}**\\n`{member.id}`", inline=True)

            embed.add_field(name="🎫 Ticket", value=f"<#{ticket['channel_id']}>", inline=True)

            embed.add_field(
                name="⚡ Ação Tomada",
                value={
                    "close": "🔒 Fechado automaticamente",
                    "transfer": "📋 Transferido para staff",
                    "notify": "📢 Apenas notificado",
                }.get(action, "Desconhecida"),
                inline=True,
            )

            embed.set_footer(text=f"Ticket ID: {ticket['id']}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro notificando staff: {e}")

    async def create_ticket_transcript(
        self, ticket: dict, channel: discord.TextChannel, reason: str
    ):
        """Criar transcript do ticket"""
        try:
            # Implementar geração de transcript
            # Por simplicidade, vamos apenas salvar informações básicas
            transcript_data = {
                "ticket_id": ticket["id"],
                "channel_id": ticket["channel_id"],
                "creator_id": ticket["creator_id"],
                "closed_reason": reason,
                "closed_at": discord.utils.utcnow().isoformat(),
                "message_count": len(await channel.history(limit=None).flatten()),
            }

            await database.run(
                """INSERT INTO ticket_transcripts 
                   (ticket_id, channel_id, creator_id, closed_reason, closed_at, transcript_data) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    ticket["id"],
                    ticket["channel_id"],
                    ticket["creator_id"],
                    reason,
                    transcript_data["closed_at"],
                    str(transcript_data),
                ),
            )

        except Exception as e:
            print(f"❌ Erro criando transcript: {e}")


async def setup(bot):
    """Setup function para carregar o cog"""
    await bot.add_cog(CreatorLeavesHandler(bot))
