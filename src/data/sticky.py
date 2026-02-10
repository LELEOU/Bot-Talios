"""
Sticky Messages Data Module - Sistema de mensagens fixas
"""

import datetime
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


async def initialize_sticky_tables():
    """Inicializar tabelas de sticky messages"""
    try:
        # Tabela principal de sticky messages
        await database.run("""
            CREATE TABLE IF NOT EXISTS sticky_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL UNIQUE,
                content TEXT NOT NULL,
                embed_data TEXT,
                current_message_id TEXT,
                enabled BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de histórico de sticky messages
        await database.run("""
            CREATE TABLE IF NOT EXISTS sticky_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sticky_id INTEGER NOT NULL,
                old_message_id TEXT,
                new_message_id TEXT,
                trigger_user_id TEXT,
                trigger_message_id TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sticky_id) REFERENCES sticky_messages (id) ON DELETE CASCADE
            )
        """)

        print("✅ Tabelas de sticky messages inicializadas")

    except Exception as e:
        print(f"❌ Erro inicializando tabelas sticky: {e}")


async def create_sticky_message(
    guild_id: int, channel_id: int, content: str, embed_data: dict = None
) -> int:
    """Criar nova sticky message"""
    try:
        result = await database.run(
            """INSERT OR REPLACE INTO sticky_messages 
               (guild_id, channel_id, content, embed_data, enabled)
               VALUES (?, ?, ?, ?, 1)""",
            (
                str(guild_id),
                str(channel_id),
                content,
                json.dumps(embed_data) if embed_data else None,
            ),
        )

        return result.lastrowid if hasattr(result, "lastrowid") else 0

    except Exception as e:
        print(f"❌ Erro criando sticky message: {e}")
        return 0


async def get_sticky_message(channel_id: int) -> dict | None:
    """Buscar sticky message do canal"""
    try:
        result = await database.fetchone(
            "SELECT * FROM sticky_messages WHERE channel_id = ? AND enabled = 1", (str(channel_id),)
        )

        if result:
            sticky = dict(result)
            if sticky.get("embed_data"):
                sticky["embed_data"] = json.loads(sticky["embed_data"])
            return sticky

        return None

    except Exception as e:
        print(f"❌ Erro buscando sticky message: {e}")
        return None


async def update_sticky_message(
    channel_id: int, content: str = None, embed_data: dict = None, message_id: int = None
) -> bool:
    """Atualizar sticky message"""
    try:
        updates = []
        params = []

        if content is not None:
            updates.append("content = ?")
            params.append(content)

        if embed_data is not None:
            updates.append("embed_data = ?")
            params.append(json.dumps(embed_data) if embed_data else None)

        if message_id is not None:
            updates.append("current_message_id = ?")
            params.append(str(message_id))

        updates.append("updated_at = ?")
        params.append(datetime.datetime.utcnow().isoformat())

        params.append(str(channel_id))

        query = f"UPDATE sticky_messages SET {', '.join(updates)} WHERE channel_id = ?"

        await database.run(query, params)

        return True

    except Exception as e:
        print(f"❌ Erro atualizando sticky message: {e}")
        return False


async def update_sticky_message_id(
    channel_id: int,
    old_message_id: int,
    new_message_id: int,
    trigger_user_id: int = None,
    trigger_message_id: int = None,
) -> bool:
    """Atualizar ID da mensagem sticky e salvar histórico"""
    try:
        # Buscar sticky atual
        sticky = await get_sticky_message(channel_id)
        if not sticky:
            return False

        # Atualizar message ID
        await database.run(
            "UPDATE sticky_messages SET current_message_id = ?, updated_at = ? WHERE channel_id = ?",
            (str(new_message_id), datetime.datetime.utcnow().isoformat(), str(channel_id)),
        )

        # Salvar no histórico
        await database.run(
            """INSERT INTO sticky_history 
               (sticky_id, old_message_id, new_message_id, trigger_user_id, trigger_message_id)
               VALUES (?, ?, ?, ?, ?)""",
            (
                sticky["id"],
                str(old_message_id) if old_message_id else None,
                str(new_message_id),
                str(trigger_user_id) if trigger_user_id else None,
                str(trigger_message_id) if trigger_message_id else None,
            ),
        )

        return True

    except Exception as e:
        print(f"❌ Erro atualizando ID sticky message: {e}")
        return False


async def delete_sticky_message(channel_id: int) -> bool:
    """Deletar sticky message"""
    try:
        await database.run("DELETE FROM sticky_messages WHERE channel_id = ?", (str(channel_id),))

        return True

    except Exception as e:
        print(f"❌ Erro deletando sticky message: {e}")
        return False


async def enable_sticky_message(channel_id: int, enabled: bool = True) -> bool:
    """Habilitar/desabilitar sticky message"""
    try:
        await database.run(
            "UPDATE sticky_messages SET enabled = ?, updated_at = ? WHERE channel_id = ?",
            (enabled, datetime.datetime.utcnow().isoformat(), str(channel_id)),
        )

        return True

    except Exception as e:
        print(f"❌ Erro habilitando/desabilitando sticky: {e}")
        return False


async def get_guild_sticky_messages(guild_id: int, enabled_only: bool = True) -> list[dict]:
    """Buscar todas sticky messages do servidor"""
    try:
        if enabled_only:
            query = "SELECT * FROM sticky_messages WHERE guild_id = ? AND enabled = 1"
            params = (str(guild_id),)
        else:
            query = "SELECT * FROM sticky_messages WHERE guild_id = ?"
            params = (str(guild_id),)

        result = await database.fetchall(query, params)

        stickies = []
        for row in result:
            sticky = dict(row)
            if sticky.get("embed_data"):
                sticky["embed_data"] = json.loads(sticky["embed_data"])
            stickies.append(sticky)

        return stickies

    except Exception as e:
        print(f"❌ Erro buscando sticky messages do servidor: {e}")
        return []


async def get_sticky_history(channel_id: int, limit: int = 10) -> list[dict]:
    """Buscar histórico de atualizações da sticky message"""
    try:
        result = await database.fetchall(
            """SELECT h.* FROM sticky_history h
               JOIN sticky_messages s ON h.sticky_id = s.id
               WHERE s.channel_id = ?
               ORDER BY h.updated_at DESC LIMIT ?""",
            (str(channel_id), limit),
        )

        return [dict(row) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando histórico sticky: {e}")
        return []


async def cleanup_old_sticky_history(days_old: int = 30) -> int:
    """Limpar histórico antigo de sticky messages"""
    try:
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days_old)).isoformat()

        result = await database.run(
            "DELETE FROM sticky_history WHERE updated_at < ?", (cutoff_date,)
        )

        return result.rowcount if hasattr(result, "rowcount") else 0

    except Exception as e:
        print(f"❌ Erro limpando histórico sticky: {e}")
        return 0


async def get_sticky_stats(guild_id: int) -> dict:
    """Buscar estatísticas de sticky messages"""
    try:
        # Contar sticky messages
        result = await database.fetchone(
            "SELECT COUNT(*) as total, SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled FROM sticky_messages WHERE guild_id = ?",
            (str(guild_id),),
        )

        total = result["total"] if result else 0
        enabled = result["enabled"] if result else 0

        # Contar atualizações recentes (últimas 24h)
        recent_date = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).isoformat()

        recent_result = await database.fetchone(
            """SELECT COUNT(*) as recent_updates FROM sticky_history h
               JOIN sticky_messages s ON h.sticky_id = s.id
               WHERE s.guild_id = ? AND h.updated_at > ?""",
            (str(guild_id), recent_date),
        )

        recent_updates = recent_result["recent_updates"] if recent_result else 0

        return {
            "total": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "recent_updates_24h": recent_updates,
        }

    except Exception as e:
        print(f"❌ Erro buscando estatísticas sticky: {e}")
        return {"total": 0, "enabled": 0, "disabled": 0, "recent_updates_24h": 0}
