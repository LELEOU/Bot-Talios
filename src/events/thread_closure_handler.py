"""
Thread Closure Handler - Gerencia fechamento de threads
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class ThreadClosureHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        """Executado quando thread é atualizada"""
        # Verificar se thread foi arquivada (fechada)
        if not before.archived and after.archived:
            await self.handle_thread_closure(after)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        """Executado quando thread é deletada"""
        await self.handle_thread_deletion(thread)

    async def handle_thread_closure(self, thread):
        """Tratar fechamento de thread"""
        try:
            # Verificar se é thread de ticket
            ticket_data = await database.fetchone(
                "SELECT * FROM tickets WHERE channel_id = ? AND type = 'thread'", (str(thread.id),)
            )

            if ticket_data:
                await self.handle_ticket_thread_closure(thread, ticket_data)
                return

            # Log geral de fechamento de thread
            await self.log_thread_closure(thread)

        except Exception as e:
            print(f"❌ Erro tratando fechamento de thread: {e}")

    async def handle_thread_deletion(self, thread):
        """Tratar deleção de thread"""
        try:
            # Log de deleção
            await self.log_thread_deletion(thread)

            # Limpar dados relacionados à thread
            await self.cleanup_thread_data(thread.id)

        except Exception as e:
            print(f"❌ Erro tratando deleção de thread: {e}")

    async def handle_ticket_thread_closure(self, thread, ticket_data):
        """Tratar fechamento de thread de ticket"""
        try:
            # Atualizar status do ticket
            await database.run(
                "UPDATE tickets SET status = 'closed', closed_at = ?, closed_by = ? WHERE id = ?",
                (discord.utils.utcnow().isoformat(), "system", ticket_data["id"]),
            )

            # Criar transcript se configurado
            await self.create_thread_transcript(thread, ticket_data)

            # Notificar criador se possível
            await self.notify_ticket_creator(thread, ticket_data)

            # Log específico do ticket
            await self.log_ticket_thread_closure(thread, ticket_data)

        except Exception as e:
            print(f"❌ Erro tratando fechamento de ticket thread: {e}")

    async def create_thread_transcript(self, thread, ticket_data):
        """Criar transcript da thread"""
        try:
            # Coletar mensagens da thread
            messages = []
            async for message in thread.history(limit=None, oldest_first=True):
                messages.append(
                    {
                        "author": str(message.author),
                        "content": message.content,
                        "timestamp": message.created_at.isoformat(),
                        "attachments": [att.url for att in message.attachments],
                    }
                )

            # Salvar transcript
            import json

            transcript_data = {
                "ticket_id": ticket_data["id"],
                "thread_id": str(thread.id),
                "thread_name": thread.name,
                "creator_id": ticket_data["creator_id"],
                "created_at": ticket_data["created_at"],
                "closed_at": discord.utils.utcnow().isoformat(),
                "message_count": len(messages),
                "messages": messages[:100],  # Limitar para não sobrecarregar
            }

            await database.run(
                """INSERT INTO ticket_transcripts 
                   (ticket_id, thread_id, creator_id, closed_at, transcript_data, message_count)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    ticket_data["id"],
                    str(thread.id),
                    ticket_data["creator_id"],
                    discord.utils.utcnow().isoformat(),
                    json.dumps(transcript_data),
                    len(messages),
                ),
            )

        except Exception as e:
            print(f"❌ Erro criando transcript: {e}")

    async def notify_ticket_creator(self, thread, ticket_data):
        """Notificar criador do ticket sobre fechamento"""
        try:
            creator = self.bot.get_user(int(ticket_data["creator_id"]))
            if not creator:
                return

            embed = discord.Embed(
                title="🎫 Ticket Fechado",
                description=f"Seu ticket **{thread.name}** foi fechado automaticamente.",
                color=0xFF9900,
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(name="📍 Servidor", value=thread.guild.name, inline=True)

            embed.add_field(
                name="📅 Aberto em",
                value=f"<t:{int(discord.utils.parse_time(ticket_data['created_at']).timestamp())}:R>",
                inline=True,
            )

            embed.add_field(
                name="📋 Motivo", value="Thread arquivada automaticamente", inline=False
            )

            embed.set_footer(text=f"ID do Ticket: {ticket_data['id']}")

            try:
                await creator.send(embed=embed)
            except discord.Forbidden:
                # Usuário não aceita DMs
                pass

        except Exception as e:
            print(f"❌ Erro notificando criador: {e}")

    async def log_thread_closure(self, thread):
        """Log de fechamento de thread"""
        try:
            log_channel = await self.get_log_channel(thread.guild.id)
            if not log_channel:
                return

            embed = discord.Embed(
                title="🧵 Thread Fechada", color=0xFF9900, timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="📝 Thread", value=f"**{thread.name}**\\n`{thread.id}`", inline=True
            )

            embed.add_field(
                name="📍 Canal Pai",
                value=thread.parent.mention if thread.parent else "Desconhecido",
                inline=True,
            )

            embed.add_field(
                name="👤 Criador",
                value=thread.owner.mention if thread.owner else "Desconhecido",
                inline=True,
            )

            embed.add_field(
                name="📅 Criada em",
                value=f"<t:{int(thread.created_at.timestamp())}:R>",
                inline=True,
            )

            # Contar mensagens se possível
            try:
                message_count = len([msg async for msg in thread.history(limit=None)])
                embed.add_field(name="💬 Mensagens", value=f"{message_count:,}", inline=True)
            except:
                pass

            embed.set_footer(text=f"Thread ID: {thread.id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro logando fechamento de thread: {e}")

    async def log_ticket_thread_closure(self, thread, ticket_data):
        """Log específico de fechamento de ticket thread"""
        try:
            log_channel = await self.get_log_channel(thread.guild.id)
            if not log_channel:
                return

            embed = discord.Embed(
                title="🎫 Ticket Thread Fechado", color=0xFF6600, timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="🎫 Ticket",
                value=f"**{thread.name}**\\n`ID: {ticket_data['id']}`",
                inline=True,
            )

            embed.add_field(name="👤 Criador", value=f"<@{ticket_data['creator_id']}>", inline=True)

            embed.add_field(
                name="📅 Aberto em",
                value=f"<t:{int(discord.utils.parse_time(ticket_data['created_at']).timestamp())}:R>",
                inline=True,
            )

            embed.add_field(
                name="📋 Motivo do Fechamento",
                value="Thread arquivada automaticamente",
                inline=False,
            )

            embed.set_footer(text=f"Thread ID: {thread.id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro logando fechamento de ticket thread: {e}")

    async def log_thread_deletion(self, thread):
        """Log de deleção de thread"""
        try:
            log_channel = await self.get_log_channel(thread.guild.id)
            if not log_channel:
                return

            embed = discord.Embed(
                title="🗑️ Thread Deletada", color=0xFF0000, timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="📝 Thread", value=f"**{thread.name}**\\n`{thread.id}`", inline=True
            )

            embed.add_field(
                name="📍 Canal Pai",
                value=thread.parent.mention if thread.parent else "Desconhecido",
                inline=True,
            )

            embed.add_field(
                name="👤 Criador",
                value=thread.owner.mention if thread.owner else "Desconhecido",
                inline=True,
            )

            embed.set_footer(text=f"Thread ID: {thread.id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro logando deleção de thread: {e}")

    async def cleanup_thread_data(self, thread_id):
        """Limpar dados relacionados à thread"""
        try:
            # Limpar tickets
            await database.run(
                "UPDATE tickets SET status = 'deleted' WHERE channel_id = ?", (str(thread_id),)
            )

            # Limpar outros dados relacionados se necessário

        except Exception as e:
            print(f"❌ Erro limpando dados da thread: {e}")

    async def get_log_channel(self, guild_id):
        """Buscar canal de log"""
        try:
            result = await database.fetchone(
                "SELECT log_channel_id FROM guild_settings WHERE guild_id = ?", (str(guild_id),)
            )

            if result and result.get("log_channel_id"):
                return self.bot.get_channel(int(result["log_channel_id"]))

            return None

        except Exception as e:
            print(f"❌ Erro buscando canal de log: {e}")
            return None


async def setup(bot):
    await bot.add_cog(ThreadClosureHandler(bot))
