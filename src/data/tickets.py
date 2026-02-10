"""
Tickets Data Module - Funções para sistema de tickets
"""

import datetime
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


async def initialize_tickets_tables():
    """Inicializar tabelas de tickets"""
    try:
        # Tabela principal de tickets
        await database.run("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                category TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                closed_at DATETIME,
                closed_by TEXT,
                transcript_url TEXT,
                ticket_number INTEGER
            )
        """)

        # Tabela de configuração de tickets
        await database.run("""
            CREATE TABLE IF NOT EXISTS ticket_config (
                guild_id TEXT PRIMARY KEY,
                enabled BOOLEAN DEFAULT 1,
                category_id TEXT,
                support_role_id TEXT,
                log_channel_id TEXT,
                max_tickets INTEGER DEFAULT 3,
                ticket_name_format TEXT DEFAULT 'ticket-{user}-{number}',
                welcome_message TEXT,
                close_message TEXT,
                auto_close_hours INTEGER DEFAULT 0,
                transcript_enabled BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de categorias de tickets
        await database.run("""
            CREATE TABLE IF NOT EXISTS ticket_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                emoji TEXT,
                role_id TEXT,
                auto_close_hours INTEGER DEFAULT 0,
                welcome_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, name)
            )
        """)

        # Tabela de mensagens de transcript
        await database.run("""
            CREATE TABLE IF NOT EXISTS ticket_transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                message_id TEXT NOT NULL,
                author_id TEXT NOT NULL,
                author_name TEXT NOT NULL,
                content TEXT,
                attachments TEXT,
                embeds TEXT,
                timestamp DATETIME NOT NULL,
                FOREIGN KEY (ticket_id) REFERENCES tickets (id) ON DELETE CASCADE
            )
        """)

        print("✅ Tabelas de tickets inicializadas")

    except Exception as e:
        print(f"❌ Erro inicializando tabelas tickets: {e}")


async def get_ticket_config(guild_id: int) -> dict | None:
    """Buscar configuração de tickets do servidor"""
    try:
        result = await database.fetchone(
            "SELECT * FROM ticket_config WHERE guild_id = ?", (str(guild_id),)
        )

        if result:
            return dict(result)

        # Retornar configuração padrão
        return {
            "enabled": True,
            "category_id": None,
            "support_role_id": None,
            "log_channel_id": None,
            "max_tickets": 3,
            "ticket_name_format": "ticket-{user}-{number}",
            "welcome_message": "Olá! Seu ticket foi criado. Nossa equipe irá ajudá-lo em breve.",
            "close_message": "Ticket fechado. Obrigado por entrar em contato conosco!",
            "auto_close_hours": 0,
            "transcript_enabled": True,
        }

    except Exception as e:
        print(f"❌ Erro buscando config tickets: {e}")
        return None


async def save_ticket_config(guild_id: int, config: dict) -> bool:
    """Salvar configuração de tickets"""
    try:
        await database.run(
            """INSERT OR REPLACE INTO ticket_config 
               (guild_id, enabled, category_id, support_role_id, log_channel_id, 
                max_tickets, ticket_name_format, welcome_message, close_message, 
                auto_close_hours, transcript_enabled)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(guild_id),
                config.get("enabled", True),
                config.get("category_id"),
                config.get("support_role_id"),
                config.get("log_channel_id"),
                config.get("max_tickets", 3),
                config.get("ticket_name_format", "ticket-{user}-{number}"),
                config.get("welcome_message"),
                config.get("close_message"),
                config.get("auto_close_hours", 0),
                config.get("transcript_enabled", True),
            ),
        )

        return True

    except Exception as e:
        print(f"❌ Erro salvando config tickets: {e}")
        return False


async def create_ticket(guild_id: int, channel_id: int, user_id: int, category: str = None) -> int:
    """Criar novo ticket"""
    try:
        # Buscar próximo número do ticket
        result = await database.fetchone(
            "SELECT MAX(ticket_number) as max_num FROM tickets WHERE guild_id = ?", (str(guild_id),)
        )

        ticket_number = (result["max_num"] or 0) + 1 if result else 1

        # Criar ticket
        result = await database.run(
            """INSERT INTO tickets 
               (guild_id, channel_id, user_id, category, ticket_number)
               VALUES (?, ?, ?, ?, ?)""",
            (str(guild_id), str(channel_id), str(user_id), category, ticket_number),
        )

        return result.lastrowid if hasattr(result, "lastrowid") else 0

    except Exception as e:
        print(f"❌ Erro criando ticket: {e}")
        return 0


async def get_ticket(channel_id: int = None, ticket_id: int = None) -> dict | None:
    """Buscar ticket por canal ou ID"""
    try:
        if channel_id:
            query = "SELECT * FROM tickets WHERE channel_id = ?"
            params = (str(channel_id),)
        elif ticket_id:
            query = "SELECT * FROM tickets WHERE id = ?"
            params = (ticket_id,)
        else:
            return None

        result = await database.fetchone(query, params)

        return dict(result) if result else None

    except Exception as e:
        print(f"❌ Erro buscando ticket: {e}")
        return None


async def get_user_tickets(guild_id: int, user_id: int, status: str = "open") -> list[dict]:
    """Buscar tickets do usuário"""
    try:
        if status:
            query = "SELECT * FROM tickets WHERE guild_id = ? AND user_id = ? AND status = ?"
            params = (str(guild_id), str(user_id), status)
        else:
            query = "SELECT * FROM tickets WHERE guild_id = ? AND user_id = ?"
            params = (str(guild_id), str(user_id))

        result = await database.fetchall(query, params)

        return [dict(row) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando tickets do usuário: {e}")
        return []


async def close_ticket(channel_id: int, closed_by: int, transcript_url: str = None) -> bool:
    """Fechar ticket"""
    try:
        await database.run(
            """UPDATE tickets 
               SET status = 'closed', closed_at = ?, closed_by = ?, transcript_url = ?
               WHERE channel_id = ?""",
            (
                datetime.datetime.utcnow().isoformat(),
                str(closed_by),
                transcript_url,
                str(channel_id),
            ),
        )

        return True

    except Exception as e:
        print(f"❌ Erro fechando ticket: {e}")
        return False


async def delete_ticket(channel_id: int) -> bool:
    """Deletar ticket"""
    try:
        await database.run("DELETE FROM tickets WHERE channel_id = ?", (str(channel_id),))

        return True

    except Exception as e:
        print(f"❌ Erro deletando ticket: {e}")
        return False


async def get_ticket_categories(guild_id: int) -> list[dict]:
    """Buscar categorias de tickets"""
    try:
        result = await database.fetchall(
            "SELECT * FROM ticket_categories WHERE guild_id = ? ORDER BY name", (str(guild_id),)
        )

        return [dict(row) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando categorias de tickets: {e}")
        return []


async def add_ticket_category(
    guild_id: int, name: str, description: str = None, emoji: str = None, role_id: int = None
) -> bool:
    """Adicionar categoria de ticket"""
    try:
        await database.run(
            """INSERT OR REPLACE INTO ticket_categories 
               (guild_id, name, description, emoji, role_id)
               VALUES (?, ?, ?, ?, ?)""",
            (str(guild_id), name, description, emoji, str(role_id) if role_id else None),
        )

        return True

    except Exception as e:
        print(f"❌ Erro adicionando categoria de ticket: {e}")
        return False


async def remove_ticket_category(guild_id: int, name: str) -> bool:
    """Remover categoria de ticket"""
    try:
        await database.run(
            "DELETE FROM ticket_categories WHERE guild_id = ? AND name = ?", (str(guild_id), name)
        )

        return True

    except Exception as e:
        print(f"❌ Erro removendo categoria de ticket: {e}")
        return False


async def add_transcript_message(
    ticket_id: int,
    message_id: int,
    author_id: int,
    author_name: str,
    content: str,
    attachments: list = None,
    embeds: list = None,
) -> bool:
    """Adicionar mensagem ao transcript"""
    try:
        await database.run(
            """INSERT INTO ticket_transcripts 
               (ticket_id, message_id, author_id, author_name, content, attachments, embeds, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ticket_id,
                str(message_id),
                str(author_id),
                author_name,
                content,
                json.dumps(attachments) if attachments else None,
                json.dumps(embeds) if embeds else None,
                datetime.datetime.utcnow().isoformat(),
            ),
        )

        return True

    except Exception as e:
        print(f"❌ Erro adicionando mensagem ao transcript: {e}")
        return False


async def get_ticket_transcript(ticket_id: int) -> list[dict]:
    """Buscar transcript do ticket"""
    try:
        result = await database.fetchall(
            "SELECT * FROM ticket_transcripts WHERE ticket_id = ? ORDER BY timestamp", (ticket_id,)
        )

        messages = []
        for row in result:
            message = dict(row)
            if message.get("attachments"):
                message["attachments"] = json.loads(message["attachments"])
            if message.get("embeds"):
                message["embeds"] = json.loads(message["embeds"])
            messages.append(message)

        return messages

    except Exception as e:
        print(f"❌ Erro buscando transcript: {e}")
        return []


async def get_guild_tickets(guild_id: int, status: str = None, limit: int = 50) -> list[dict]:
    """Buscar tickets do servidor"""
    try:
        if status:
            query = "SELECT * FROM tickets WHERE guild_id = ? AND status = ? ORDER BY created_at DESC LIMIT ?"
            params = (str(guild_id), status, limit)
        else:
            query = "SELECT * FROM tickets WHERE guild_id = ? ORDER BY created_at DESC LIMIT ?"
            params = (str(guild_id), limit)

        result = await database.fetchall(query, params)

        return [dict(row) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando tickets do servidor: {e}")
        return []


async def get_ticket_stats(guild_id: int) -> dict:
    """Buscar estatísticas de tickets"""
    try:
        # Tickets por status
        result = await database.fetchall(
            "SELECT status, COUNT(*) as count FROM tickets WHERE guild_id = ? GROUP BY status",
            (str(guild_id),),
        )

        stats = {"total": 0, "open": 0, "closed": 0}

        for row in result:
            stats[row["status"]] = row["count"]
            stats["total"] += row["count"]

        return stats

    except Exception as e:
        print(f"❌ Erro buscando estatísticas de tickets: {e}")
        return {"total": 0, "open": 0, "closed": 0}
