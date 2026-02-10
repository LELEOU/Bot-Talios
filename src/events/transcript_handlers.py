"""
Transcript Handlers - Sistema de transcrições de tickets
"""

import io
import json
import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class TranscriptHandlers(commands.Cog):
    """Handlers para sistema de transcrições"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Registrar mensagem deletada para transcripts"""
        if not message.guild:
            return

        # Verificar se é canal de ticket
        if await self.is_ticket_channel(message.channel.id):
            await self.log_deleted_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Registrar mensagem editada para transcripts"""
        if not before.guild:
            return

        # Verificar se é canal de ticket
        if await self.is_ticket_channel(before.channel.id):
            await self.log_updated_message(before, after)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Registrar nova mensagem para transcripts"""
        if message.author.bot or not message.guild:
            return

        # Verificar se é canal de ticket
        if await self.is_ticket_channel(message.channel.id):
            await self.log_new_message(message)

    async def is_ticket_channel(self, channel_id: int) -> bool:
        """Verificar se canal é de ticket"""
        try:
            result = await database.fetchone(
                "SELECT id FROM tickets WHERE channel_id = ? AND status IN ('open', 'pending')",
                (str(channel_id),),
            )
            return result is not None

        except Exception as e:
            print(f"❌ Erro verificando canal de ticket: {e}")
            return False

    async def log_new_message(self, message: discord.Message):
        """Registrar nova mensagem"""
        try:
            # Preparar dados da mensagem
            message_data = {
                "id": str(message.id),
                "author_id": str(message.author.id),
                "author_name": str(message.author),
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
                "attachments": [
                    {"filename": att.filename, "url": att.url, "size": att.size}
                    for att in message.attachments
                ],
                "embeds": [embed.to_dict() for embed in message.embeds],
                "type": "new",
            }

            # Salvar no banco
            await database.run(
                """INSERT INTO transcript_messages 
                   (channel_id, message_id, author_id, content, message_data, timestamp, action_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(message.channel.id),
                    str(message.id),
                    str(message.author.id),
                    message.content,
                    json.dumps(message_data),
                    message.created_at.isoformat(),
                    "new",
                ),
            )

        except Exception as e:
            print(f"❌ Erro registrando nova mensagem: {e}")

    async def log_deleted_message(self, message: discord.Message):
        """Registrar mensagem deletada"""
        try:
            message_data = {
                "id": str(message.id),
                "author_id": str(message.author.id),
                "author_name": str(message.author),
                "content": message.content,
                "original_timestamp": message.created_at.isoformat(),
                "deleted_timestamp": discord.utils.utcnow().isoformat(),
                "attachments": [
                    {"filename": att.filename, "url": att.url, "size": att.size}
                    for att in message.attachments
                ],
                "embeds": [embed.to_dict() for embed in message.embeds],
                "type": "deleted",
            }

            await database.run(
                """INSERT INTO transcript_messages 
                   (channel_id, message_id, author_id, content, message_data, timestamp, action_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(message.channel.id),
                    str(message.id),
                    str(message.author.id),
                    message.content,
                    json.dumps(message_data),
                    discord.utils.utcnow().isoformat(),
                    "deleted",
                ),
            )

        except Exception as e:
            print(f"❌ Erro registrando mensagem deletada: {e}")

    async def log_updated_message(self, before: discord.Message, after: discord.Message):
        """Registrar mensagem editada"""
        try:
            message_data = {
                "id": str(after.id),
                "author_id": str(after.author.id),
                "author_name": str(after.author),
                "content_before": before.content,
                "content_after": after.content,
                "original_timestamp": before.created_at.isoformat(),
                "edited_timestamp": after.edited_at.isoformat()
                if after.edited_at
                else discord.utils.utcnow().isoformat(),
                "attachments_before": [
                    {"filename": att.filename, "url": att.url, "size": att.size}
                    for att in before.attachments
                ],
                "attachments_after": [
                    {"filename": att.filename, "url": att.url, "size": att.size}
                    for att in after.attachments
                ],
                "type": "edited",
            }

            await database.run(
                """INSERT INTO transcript_messages 
                   (channel_id, message_id, author_id, content, message_data, timestamp, action_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(after.channel.id),
                    str(after.id),
                    str(after.author.id),
                    f"ANTES: {before.content}\\nDEPOIS: {after.content}",
                    json.dumps(message_data),
                    discord.utils.utcnow().isoformat(),
                    "edited",
                ),
            )

        except Exception as e:
            print(f"❌ Erro registrando mensagem editada: {e}")

    async def generate_ticket_transcript(self, ticket_id: int, format_type: str = "html") -> str:
        """Gerar transcript completo do ticket"""
        try:
            # Buscar dados do ticket
            ticket = await database.fetchone("SELECT * FROM tickets WHERE id = ?", (ticket_id,))

            if not ticket:
                return None

            # Buscar mensagens do transcript
            messages = await database.fetchall(
                "SELECT * FROM transcript_messages WHERE channel_id = ? ORDER BY timestamp",
                (ticket["channel_id"],),
            )

            if format_type == "html":
                return await self.generate_html_transcript(ticket, messages)
            if format_type == "txt":
                return await self.generate_text_transcript(ticket, messages)
            if format_type == "json":
                return await self.generate_json_transcript(ticket, messages)

            return None

        except Exception as e:
            print(f"❌ Erro gerando transcript: {e}")
            return None

    async def generate_html_transcript(self, ticket: dict, messages: list) -> str:
        """Gerar transcript em formato HTML"""
        try:
            guild = self.bot.get_guild(int(ticket["guild_id"]))
            guild_name = guild.name if guild else "Servidor Desconhecido"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Transcript - Ticket #{ticket["id"]}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                    .header {{ background-color: #7289da; color: white; padding: 20px; border-radius: 5px; }}
                    .message {{ margin: 10px 0; padding: 10px; background-color: white; border-radius: 5px; }}
                    .message.deleted {{ background-color: #ffebee; border-left: 4px solid #f44336; }}
                    .message.edited {{ background-color: #fff3e0; border-left: 4px solid #ff9800; }}
                    .author {{ font-weight: bold; color: #7289da; }}
                    .timestamp {{ font-size: 0.8em; color: #666; }}
                    .content {{ margin: 5px 0; }}
                    .attachment {{ background-color: #e8f5e8; padding: 5px; margin: 5px 0; border-radius: 3px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Transcript - Ticket #{ticket["id"]}</h1>
                    <p>Servidor: {guild_name}</p>
                    <p>Criador: <@{ticket["creator_id"]}></p>
                    <p>Criado em: {ticket["created_at"]}</p>
                    <p>Status: {ticket["status"]}</p>
                </div>
            """

            for msg in messages:
                try:
                    msg_data = json.loads(msg["message_data"]) if msg["message_data"] else {}

                    css_class = ""
                    if msg["action_type"] == "deleted":
                        css_class = "deleted"
                    elif msg["action_type"] == "edited":
                        css_class = "edited"

                    author_name = msg_data.get("author_name", "Usuário Desconhecido")
                    timestamp = msg_data.get("timestamp", msg["timestamp"])

                    html_content += f"""
                    <div class="message {css_class}">
                        <div class="author">{author_name}</div>
                        <div class="timestamp">{timestamp}</div>
                        <div class="content">{msg["content"]}</div>
                    """

                    # Anexos
                    attachments = msg_data.get("attachments", [])
                    for att in attachments:
                        html_content += f'<div class="attachment">📎 {att["filename"]} ({att["size"]} bytes)</div>'

                    html_content += "</div>"

                except Exception as e:
                    print(f"❌ Erro processando mensagem no transcript: {e}")
                    continue

            html_content += """
                </body>
            </html>
            """

            return html_content

        except Exception as e:
            print(f"❌ Erro gerando HTML transcript: {e}")
            return None

    async def generate_text_transcript(self, ticket: dict, messages: list) -> str:
        """Gerar transcript em formato texto"""
        try:
            guild = self.bot.get_guild(int(ticket["guild_id"]))
            guild_name = guild.name if guild else "Servidor Desconhecido"

            content = f"""
===== TRANSCRIPT - TICKET #{ticket["id"]} =====
Servidor: {guild_name}
Criador: {ticket["creator_id"]}
Criado em: {ticket["created_at"]}
Status: {ticket["status"]}
================================================

"""

            for msg in messages:
                try:
                    msg_data = json.loads(msg["message_data"]) if msg["message_data"] else {}
                    author_name = msg_data.get("author_name", "Usuário Desconhecido")
                    timestamp = msg_data.get("timestamp", msg["timestamp"])

                    prefix = ""
                    if msg["action_type"] == "deleted":
                        prefix = "[DELETADA] "
                    elif msg["action_type"] == "edited":
                        prefix = "[EDITADA] "

                    content += f"[{timestamp}] {prefix}{author_name}: {msg['content']}\\n"

                    # Anexos
                    attachments = msg_data.get("attachments", [])
                    for att in attachments:
                        content += f"    📎 Anexo: {att['filename']}\\n"

                except Exception as e:
                    print(f"❌ Erro processando mensagem no transcript texto: {e}")
                    continue

            return content

        except Exception as e:
            print(f"❌ Erro gerando texto transcript: {e}")
            return None

    async def generate_json_transcript(self, ticket: dict, messages: list) -> str:
        """Gerar transcript em formato JSON"""
        try:
            transcript_data = {
                "ticket": dict(ticket),
                "messages": [],
                "generated_at": discord.utils.utcnow().isoformat(),
                "message_count": len(messages),
            }

            for msg in messages:
                try:
                    msg_data = json.loads(msg["message_data"]) if msg["message_data"] else {}
                    transcript_data["messages"].append(
                        {
                            "id": msg["message_id"],
                            "author_id": msg["author_id"],
                            "content": msg["content"],
                            "timestamp": msg["timestamp"],
                            "action_type": msg["action_type"],
                            "data": msg_data,
                        }
                    )
                except Exception as e:
                    print(f"❌ Erro processando mensagem no JSON transcript: {e}")
                    continue

            return json.dumps(transcript_data, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"❌ Erro gerando JSON transcript: {e}")
            return None

    async def save_transcript_file(self, ticket_id: int, format_type: str = "html") -> discord.File:
        """Salvar transcript como arquivo"""
        try:
            content = await self.generate_ticket_transcript(ticket_id, format_type)
            if not content:
                return None

            # Determinar extensão
            extension = {"html": "html", "txt": "txt", "json": "json"}.get(format_type, "txt")
            filename = f"ticket_{ticket_id}_transcript.{extension}"

            # Criar arquivo em memória
            file_data = io.BytesIO(content.encode("utf-8"))

            return discord.File(file_data, filename=filename)

        except Exception as e:
            print(f"❌ Erro salvando arquivo transcript: {e}")
            return None


async def setup(bot):
    await bot.add_cog(TranscriptHandlers(bot))
