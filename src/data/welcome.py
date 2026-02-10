"""
Welcome Data Module - Sistema de mensagens de boas-vindas
"""

import datetime
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


async def initialize_welcome_tables():
    """Inicializar tabelas de welcome"""
    try:
        # Tabela de configuração de welcome
        await database.run("""
            CREATE TABLE IF NOT EXISTS welcome_config (
                guild_id TEXT PRIMARY KEY,
                enabled BOOLEAN DEFAULT 1,
                welcome_channel_id TEXT,
                welcome_message TEXT DEFAULT 'Bem-vindo(a) ao servidor, {user}!',
                welcome_embed BOOLEAN DEFAULT 0,
                welcome_embed_data TEXT,
                goodbye_enabled BOOLEAN DEFAULT 0,
                goodbye_channel_id TEXT,
                goodbye_message TEXT DEFAULT 'Tchau, {user}! Esperamos te ver novamente.',
                dm_welcome BOOLEAN DEFAULT 0,
                dm_message TEXT DEFAULT 'Bem-vindo(a) ao {server}!',
                auto_role_enabled BOOLEAN DEFAULT 0,
                auto_roles TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de histórico de welcome
        await database.run("""
            CREATE TABLE IF NOT EXISTS welcome_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL CHECK(event_type IN ('join', 'leave')),
                message_sent BOOLEAN DEFAULT 0,
                dm_sent BOOLEAN DEFAULT 0,
                roles_assigned BOOLEAN DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        print("✅ Tabelas de welcome inicializadas")

    except Exception as e:
        print(f"❌ Erro inicializando tabelas welcome: {e}")


async def get_welcome_config(guild_id: int) -> dict | None:
    """Buscar configuração de welcome"""
    try:
        result = await database.fetchone(
            "SELECT * FROM welcome_config WHERE guild_id = ?", (str(guild_id),)
        )

        if result:
            config = dict(result)
            if config.get("welcome_embed_data"):
                config["welcome_embed_data"] = json.loads(config["welcome_embed_data"])
            if config.get("auto_roles"):
                config["auto_roles"] = json.loads(config["auto_roles"])
            return config

        # Configuração padrão
        return {
            "enabled": True,
            "welcome_channel_id": None,
            "welcome_message": "Bem-vindo(a) ao servidor, {user}!",
            "welcome_embed": False,
            "welcome_embed_data": None,
            "goodbye_enabled": False,
            "goodbye_channel_id": None,
            "goodbye_message": "Tchau, {user}! Esperamos te ver novamente.",
            "dm_welcome": False,
            "dm_message": "Bem-vindo(a) ao {server}!",
            "auto_role_enabled": False,
            "auto_roles": [],
        }

    except Exception as e:
        print(f"❌ Erro buscando config welcome: {e}")
        return None


async def save_welcome_config(guild_id: int, config: dict) -> bool:
    """Salvar configuração de welcome"""
    try:
        await database.run(
            """INSERT OR REPLACE INTO welcome_config 
               (guild_id, enabled, welcome_channel_id, welcome_message, welcome_embed, 
                welcome_embed_data, goodbye_enabled, goodbye_channel_id, goodbye_message,
                dm_welcome, dm_message, auto_role_enabled, auto_roles)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(guild_id),
                config.get("enabled", True),
                config.get("welcome_channel_id"),
                config.get("welcome_message", "Bem-vindo(a) ao servidor, {user}!"),
                config.get("welcome_embed", False),
                json.dumps(config.get("welcome_embed_data"))
                if config.get("welcome_embed_data")
                else None,
                config.get("goodbye_enabled", False),
                config.get("goodbye_channel_id"),
                config.get("goodbye_message", "Tchau, {user}! Esperamos te ver novamente."),
                config.get("dm_welcome", False),
                config.get("dm_message", "Bem-vindo(a) ao {server}!"),
                config.get("auto_role_enabled", False),
                json.dumps(config.get("auto_roles", [])) if config.get("auto_roles") else None,
            ),
        )

        return True

    except Exception as e:
        print(f"❌ Erro salvando config welcome: {e}")
        return False


async def log_welcome_event(
    guild_id: int,
    user_id: int,
    event_type: str,
    message_sent: bool = False,
    dm_sent: bool = False,
    roles_assigned: bool = False,
) -> bool:
    """Registrar evento de welcome/goodbye"""
    try:
        await database.run(
            """INSERT INTO welcome_history 
               (guild_id, user_id, event_type, message_sent, dm_sent, roles_assigned)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (str(guild_id), str(user_id), event_type, message_sent, dm_sent, roles_assigned),
        )

        return True

    except Exception as e:
        print(f"❌ Erro registrando evento welcome: {e}")
        return False


async def get_welcome_history(
    guild_id: int, user_id: int = None, event_type: str = None, limit: int = 50
) -> list[dict]:
    """Buscar histórico de eventos de welcome"""
    try:
        conditions = ["guild_id = ?"]
        params = [str(guild_id)]

        if user_id:
            conditions.append("user_id = ?")
            params.append(str(user_id))

        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)

        query = f"""SELECT * FROM welcome_history 
                   WHERE {" AND ".join(conditions)}
                   ORDER BY timestamp DESC LIMIT ?"""
        params.append(limit)

        result = await database.fetchall(query, params)

        return [dict(row) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando histórico welcome: {e}")
        return []


async def get_welcome_stats(guild_id: int, days: int = 30) -> dict:
    """Buscar estatísticas de welcome"""
    try:
        # Data de corte
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()

        # Estatísticas gerais
        result = await database.fetchall(
            """SELECT 
                   event_type,
                   COUNT(*) as count,
                   SUM(CASE WHEN message_sent = 1 THEN 1 ELSE 0 END) as messages_sent,
                   SUM(CASE WHEN dm_sent = 1 THEN 1 ELSE 0 END) as dms_sent,
                   SUM(CASE WHEN roles_assigned = 1 THEN 1 ELSE 0 END) as roles_assigned
               FROM welcome_history 
               WHERE guild_id = ? AND timestamp >= ?
               GROUP BY event_type""",
            (str(guild_id), cutoff_date),
        )

        stats = {
            "joins": {"count": 0, "messages_sent": 0, "dms_sent": 0, "roles_assigned": 0},
            "leaves": {"count": 0, "messages_sent": 0, "dms_sent": 0, "roles_assigned": 0},
            "total_joins": 0,
            "total_leaves": 0,
            "net_growth": 0,
        }

        for row in result:
            event_type = row["event_type"]
            if event_type == "join":
                stats["joins"] = {
                    "count": row["count"],
                    "messages_sent": row["messages_sent"],
                    "dms_sent": row["dms_sent"],
                    "roles_assigned": row["roles_assigned"],
                }
                stats["total_joins"] = row["count"]
            elif event_type == "leave":
                stats["leaves"] = {
                    "count": row["count"],
                    "messages_sent": row["messages_sent"],
                    "dms_sent": row["dms_sent"],
                    "roles_assigned": row["roles_assigned"],
                }
                stats["total_leaves"] = row["count"]

        stats["net_growth"] = stats["total_joins"] - stats["total_leaves"]

        return stats

    except Exception as e:
        print(f"❌ Erro buscando estatísticas welcome: {e}")
        return {
            "joins": {"count": 0, "messages_sent": 0, "dms_sent": 0, "roles_assigned": 0},
            "leaves": {"count": 0, "messages_sent": 0, "dms_sent": 0, "roles_assigned": 0},
            "total_joins": 0,
            "total_leaves": 0,
            "net_growth": 0,
        }


async def cleanup_old_welcome_history(days_old: int = 90) -> int:
    """Limpar histórico antigo de welcome"""
    try:
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days_old)).isoformat()

        result = await database.run(
            "DELETE FROM welcome_history WHERE timestamp < ?", (cutoff_date,)
        )

        return result.rowcount if hasattr(result, "rowcount") else 0

    except Exception as e:
        print(f"❌ Erro limpando histórico welcome: {e}")
        return 0


async def get_recent_joins(guild_id: int, hours: int = 24, limit: int = 10) -> list[dict]:
    """Buscar membros que entraram recentemente"""
    try:
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(hours=hours)).isoformat()

        result = await database.fetchall(
            """SELECT * FROM welcome_history 
               WHERE guild_id = ? AND event_type = 'join' AND timestamp >= ?
               ORDER BY timestamp DESC LIMIT ?""",
            (str(guild_id), cutoff_date, limit),
        )

        return [dict(row) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando entradas recentes: {e}")
        return []


async def get_recent_leaves(guild_id: int, hours: int = 24, limit: int = 10) -> list[dict]:
    """Buscar membros que saíram recentemente"""
    try:
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(hours=hours)).isoformat()

        result = await database.fetchall(
            """SELECT * FROM welcome_history 
               WHERE guild_id = ? AND event_type = 'leave' AND timestamp >= ?
               ORDER BY timestamp DESC LIMIT ?""",
            (str(guild_id), cutoff_date, limit),
        )

        return [dict(row) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando saídas recentes: {e}")
        return []
