"""
Logs Data Module - Sistema de logs de eventos
"""

import datetime
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


async def initialize_logs_tables():
    """Inicializar tabelas de logs"""
    try:
        # Tabela principal de logs
        await database.run("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                user_id TEXT,
                target_id TEXT,
                channel_id TEXT,
                message_id TEXT,
                data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de configuração de logs
        await database.run("""
            CREATE TABLE IF NOT EXISTS log_config (
                guild_id TEXT PRIMARY KEY,
                enabled BOOLEAN DEFAULT 1,
                log_channel_id TEXT,
                events_enabled TEXT DEFAULT '[]',
                ignore_bots BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Índices para performance
        await database.run(
            "CREATE INDEX IF NOT EXISTS idx_logs_guild_event ON logs(guild_id, event_type)"
        )
        await database.run("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")

        print("✅ Tabelas de logs inicializadas")

    except Exception as e:
        print(f"❌ Erro inicializando tabelas logs: {e}")


async def get_log_config(guild_id: int) -> dict | None:
    """Buscar configuração de logs"""
    try:
        result = await database.fetchone(
            "SELECT * FROM log_config WHERE guild_id = ?", (str(guild_id),)
        )

        if result:
            config = dict(result)
            config["events_enabled"] = json.loads(config.get("events_enabled", "[]"))
            return config

        # Configuração padrão
        return {
            "enabled": True,
            "log_channel_id": None,
            "events_enabled": [
                "message_delete",
                "message_edit",
                "member_join",
                "member_leave",
                "member_ban",
                "member_unban",
                "role_update",
                "channel_create",
                "channel_delete",
                "channel_update",
            ],
            "ignore_bots": True,
        }

    except Exception as e:
        print(f"❌ Erro buscando config logs: {e}")
        return None


async def save_log_config(guild_id: int, config: dict) -> bool:
    """Salvar configuração de logs"""
    try:
        await database.run(
            """INSERT OR REPLACE INTO log_config 
               (guild_id, enabled, log_channel_id, events_enabled, ignore_bots)
               VALUES (?, ?, ?, ?, ?)""",
            (
                str(guild_id),
                config.get("enabled", True),
                config.get("log_channel_id"),
                json.dumps(config.get("events_enabled", [])),
                config.get("ignore_bots", True),
            ),
        )

        return True

    except Exception as e:
        print(f"❌ Erro salvando config logs: {e}")
        return False


async def add_log_entry(
    guild_id: int,
    event_type: str,
    user_id: int = None,
    target_id: int = None,
    channel_id: int = None,
    message_id: int = None,
    data: dict = None,
) -> int:
    """Adicionar entrada de log"""
    try:
        result = await database.run(
            """INSERT INTO logs 
               (guild_id, event_type, user_id, target_id, channel_id, message_id, data)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                str(guild_id),
                event_type,
                str(user_id) if user_id else None,
                str(target_id) if target_id else None,
                str(channel_id) if channel_id else None,
                str(message_id) if message_id else None,
                json.dumps(data) if data else None,
            ),
        )

        return result.lastrowid if hasattr(result, "lastrowid") else 0

    except Exception as e:
        print(f"❌ Erro adicionando log: {e}")
        return 0


async def get_logs(
    guild_id: int, event_type: str = None, user_id: int = None, limit: int = 50, offset: int = 0
) -> list[dict]:
    """Buscar logs"""
    try:
        conditions = ["guild_id = ?"]
        params = [str(guild_id)]

        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)

        if user_id:
            conditions.append("user_id = ?")
            params.append(str(user_id))

        query = f"""SELECT * FROM logs 
                   WHERE {" AND ".join(conditions)}
                   ORDER BY timestamp DESC LIMIT ? OFFSET ?"""
        params.extend([limit, offset])

        result = await database.fetchall(query, params)

        logs = []
        for row in result:
            log_entry = dict(row)
            if log_entry.get("data"):
                log_entry["data"] = json.loads(log_entry["data"])
            logs.append(log_entry)

        return logs

    except Exception as e:
        print(f"❌ Erro buscando logs: {e}")
        return []


async def get_logs_by_date_range(
    guild_id: int,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    event_type: str = None,
    limit: int = 100,
) -> list[dict]:
    """Buscar logs por período"""
    try:
        conditions = ["guild_id = ?", "timestamp BETWEEN ? AND ?"]
        params = [str(guild_id), start_date.isoformat(), end_date.isoformat()]

        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)

        query = f"""SELECT * FROM logs 
                   WHERE {" AND ".join(conditions)}
                   ORDER BY timestamp DESC LIMIT ?"""
        params.append(limit)

        result = await database.fetchall(query, params)

        logs = []
        for row in result:
            log_entry = dict(row)
            if log_entry.get("data"):
                log_entry["data"] = json.loads(log_entry["data"])
            logs.append(log_entry)

        return logs

    except Exception as e:
        print(f"❌ Erro buscando logs por data: {e}")
        return []


async def get_log_stats(guild_id: int, days: int = 7) -> dict:
    """Buscar estatísticas de logs"""
    try:
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()

        # Contagem por tipo de evento
        result = await database.fetchall(
            """SELECT event_type, COUNT(*) as count 
               FROM logs 
               WHERE guild_id = ? AND timestamp >= ?
               GROUP BY event_type
               ORDER BY count DESC""",
            (str(guild_id), cutoff_date),
        )

        event_stats = {row["event_type"]: row["count"] for row in result} if result else {}

        # Total de logs
        total_result = await database.fetchone(
            "SELECT COUNT(*) as total FROM logs WHERE guild_id = ? AND timestamp >= ?",
            (str(guild_id), cutoff_date),
        )

        total_logs = total_result["total"] if total_result else 0

        # Logs por dia
        daily_result = await database.fetchall(
            """SELECT DATE(timestamp) as date, COUNT(*) as count
               FROM logs 
               WHERE guild_id = ? AND timestamp >= ?
               GROUP BY DATE(timestamp)
               ORDER BY date DESC""",
            (str(guild_id), cutoff_date),
        )

        daily_stats = {row["date"]: row["count"] for row in daily_result} if daily_result else {}

        return {
            "total_logs": total_logs,
            "event_stats": event_stats,
            "daily_stats": daily_stats,
            "period_days": days,
        }

    except Exception as e:
        print(f"❌ Erro buscando estatísticas logs: {e}")
        return {"total_logs": 0, "event_stats": {}, "daily_stats": {}, "period_days": days}


async def cleanup_old_logs(guild_id: int, days_old: int = 90) -> int:
    """Limpar logs antigos"""
    try:
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days_old)).isoformat()

        result = await database.run(
            "DELETE FROM logs WHERE guild_id = ? AND timestamp < ?", (str(guild_id), cutoff_date)
        )

        return result.rowcount if hasattr(result, "rowcount") else 0

    except Exception as e:
        print(f"❌ Erro limpando logs antigos: {e}")
        return 0


async def search_logs(guild_id: int, search_term: str, limit: int = 50) -> list[dict]:
    """Buscar logs por termo"""
    try:
        # Buscar em dados JSON e IDs
        result = await database.fetchall(
            """SELECT * FROM logs 
               WHERE guild_id = ? AND (
                   data LIKE ? OR 
                   user_id LIKE ? OR 
                   target_id LIKE ? OR 
                   channel_id LIKE ? OR
                   message_id LIKE ?
               )
               ORDER BY timestamp DESC LIMIT ?""",
            (
                str(guild_id),
                f"%{search_term}%",
                f"%{search_term}%",
                f"%{search_term}%",
                f"%{search_term}%",
                f"%{search_term}%",
                limit,
            ),
        )

        logs = []
        for row in result:
            log_entry = dict(row)
            if log_entry.get("data"):
                log_entry["data"] = json.loads(log_entry["data"])
            logs.append(log_entry)

        return logs

    except Exception as e:
        print(f"❌ Erro buscando logs: {e}")
        return []


async def export_logs(
    guild_id: int,
    start_date: datetime.datetime = None,
    end_date: datetime.datetime = None,
    event_types: list[str] = None,
) -> str:
    """Exportar logs como JSON"""
    try:
        conditions = ["guild_id = ?"]
        params = [str(guild_id)]

        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date.isoformat())

        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date.isoformat())

        if event_types:
            placeholders = ",".join(["?" for _ in event_types])
            conditions.append(f"event_type IN ({placeholders})")
            params.extend(event_types)

        query = f"""SELECT * FROM logs 
                   WHERE {" AND ".join(conditions)}
                   ORDER BY timestamp ASC"""

        result = await database.fetchall(query, params)

        logs = []
        for row in result:
            log_entry = dict(row)
            if log_entry.get("data"):
                log_entry["data"] = json.loads(log_entry["data"])
            logs.append(log_entry)

        export_data = {
            "export_info": {
                "guild_id": str(guild_id),
                "exported_at": datetime.datetime.utcnow().isoformat(),
                "total_logs": len(logs),
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "event_types": event_types,
            },
            "logs": logs,
        }

        return json.dumps(export_data, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"❌ Erro exportando logs: {e}")
        return "{}"


async def get_user_activity_logs(guild_id: int, user_id: int, limit: int = 20) -> list[dict]:
    """Buscar logs de atividade de um usuário específico"""
    try:
        result = await database.fetchall(
            """SELECT * FROM logs 
               WHERE guild_id = ? AND (user_id = ? OR target_id = ?)
               ORDER BY timestamp DESC LIMIT ?""",
            (str(guild_id), str(user_id), str(user_id), limit),
        )

        logs = []
        for row in result:
            log_entry = dict(row)
            if log_entry.get("data"):
                log_entry["data"] = json.loads(log_entry["data"])
            logs.append(log_entry)

        return logs

    except Exception as e:
        print(f"❌ Erro buscando logs do usuário: {e}")
        return []
