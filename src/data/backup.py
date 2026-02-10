"""
Backup Data Module - Sistema de backup de configurações
"""

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


async def initialize_backup_tables():
    """Inicializar tabelas de backup"""
    try:
        # Tabela de backups
        await database.run("""
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                backup_name TEXT NOT NULL,
                backup_data TEXT NOT NULL,
                backup_size INTEGER DEFAULT 0,
                created_by TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                UNIQUE(guild_id, backup_name)
            )
        """)

        # Tabela de histórico de restore
        await database.run("""
            CREATE TABLE IF NOT EXISTS backup_restore_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_id INTEGER NOT NULL,
                restored_by TEXT NOT NULL,
                restored_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT 0,
                error_message TEXT,
                FOREIGN KEY (backup_id) REFERENCES backups (id) ON DELETE CASCADE
            )
        """)

        print("✅ Tabelas de backup inicializadas")

    except Exception as e:
        print(f"❌ Erro inicializando tabelas backup: {e}")


async def create_backup(
    guild_id: int, backup_name: str, backup_data: dict, created_by: int, description: str = None
) -> int:
    """Criar novo backup"""
    try:
        backup_json = json.dumps(backup_data, indent=2)
        backup_size = len(backup_json.encode("utf-8"))

        result = await database.run(
            """INSERT OR REPLACE INTO backups 
               (guild_id, backup_name, backup_data, backup_size, created_by, description)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (str(guild_id), backup_name, backup_json, backup_size, str(created_by), description),
        )

        return result.lastrowid if hasattr(result, "lastrowid") else 0

    except Exception as e:
        print(f"❌ Erro criando backup: {e}")
        return 0


async def get_backup(guild_id: int, backup_name: str) -> dict | None:
    """Buscar backup específico"""
    try:
        result = await database.fetchone(
            "SELECT * FROM backups WHERE guild_id = ? AND backup_name = ?",
            (str(guild_id), backup_name),
        )

        if result:
            backup = dict(result)
            backup["backup_data"] = json.loads(backup["backup_data"])
            return backup

        return None

    except Exception as e:
        print(f"❌ Erro buscando backup: {e}")
        return None


async def get_backup_by_id(backup_id: int) -> dict | None:
    """Buscar backup por ID"""
    try:
        result = await database.fetchone("SELECT * FROM backups WHERE id = ?", (backup_id,))

        if result:
            backup = dict(result)
            backup["backup_data"] = json.loads(backup["backup_data"])
            return backup

        return None

    except Exception as e:
        print(f"❌ Erro buscando backup por ID: {e}")
        return None


async def list_backups(guild_id: int, limit: int = 10) -> list[dict]:
    """Listar backups do servidor"""
    try:
        result = await database.fetchall(
            """SELECT id, guild_id, backup_name, backup_size, created_by, 
                      created_at, description
               FROM backups WHERE guild_id = ? 
               ORDER BY created_at DESC LIMIT ?""",
            (str(guild_id), limit),
        )

        return [dict(row) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro listando backups: {e}")
        return []


async def delete_backup(guild_id: int, backup_name: str) -> bool:
    """Deletar backup"""
    try:
        await database.run(
            "DELETE FROM backups WHERE guild_id = ? AND backup_name = ?",
            (str(guild_id), backup_name),
        )

        return True

    except Exception as e:
        print(f"❌ Erro deletando backup: {e}")
        return False


async def log_backup_restore(
    backup_id: int, restored_by: int, success: bool, error_message: str = None
) -> bool:
    """Registrar tentativa de restore"""
    try:
        await database.run(
            """INSERT INTO backup_restore_history 
               (backup_id, restored_by, success, error_message)
               VALUES (?, ?, ?, ?)""",
            (backup_id, str(restored_by), success, error_message),
        )

        return True

    except Exception as e:
        print(f"❌ Erro registrando restore: {e}")
        return False


async def get_restore_history(guild_id: int, limit: int = 20) -> list[dict]:
    """Buscar histórico de restores"""
    try:
        result = await database.fetchall(
            """SELECT rh.*, b.backup_name, b.guild_id
               FROM backup_restore_history rh
               JOIN backups b ON rh.backup_id = b.id
               WHERE b.guild_id = ?
               ORDER BY rh.restored_at DESC LIMIT ?""",
            (str(guild_id), limit),
        )

        return [dict(row) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando histórico de restore: {e}")
        return []


async def get_backup_stats(guild_id: int) -> dict:
    """Buscar estatísticas de backups"""
    try:
        # Contar backups
        result = await database.fetchone(
            "SELECT COUNT(*) as count, SUM(backup_size) as total_size FROM backups WHERE guild_id = ?",
            (str(guild_id),),
        )

        count = result["count"] if result else 0
        total_size = result["total_size"] if result else 0

        # Backup mais recente
        recent_result = await database.fetchone(
            "SELECT created_at FROM backups WHERE guild_id = ? ORDER BY created_at DESC LIMIT 1",
            (str(guild_id),),
        )

        last_backup = recent_result["created_at"] if recent_result else None

        # Restores bem-sucedidos
        restore_result = await database.fetchone(
            """SELECT COUNT(*) as total, 
                      SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
               FROM backup_restore_history rh
               JOIN backups b ON rh.backup_id = b.id
               WHERE b.guild_id = ?""",
            (str(guild_id),),
        )

        total_restores = restore_result["total"] if restore_result else 0
        successful_restores = restore_result["successful"] if restore_result else 0

        return {
            "total_backups": count,
            "total_size_bytes": total_size or 0,
            "total_size_mb": round((total_size or 0) / (1024 * 1024), 2),
            "last_backup": last_backup,
            "total_restores": total_restores,
            "successful_restores": successful_restores,
            "failed_restores": total_restores - successful_restores,
        }

    except Exception as e:
        print(f"❌ Erro buscando estatísticas backup: {e}")
        return {
            "total_backups": 0,
            "total_size_bytes": 0,
            "total_size_mb": 0,
            "last_backup": None,
            "total_restores": 0,
            "successful_restores": 0,
            "failed_restores": 0,
        }


async def cleanup_old_backups(guild_id: int, keep_count: int = 5) -> int:
    """Limpar backups antigos, mantendo apenas os mais recentes"""
    try:
        # Buscar backups para manter
        keep_result = await database.fetchall(
            "SELECT id FROM backups WHERE guild_id = ? ORDER BY created_at DESC LIMIT ?",
            (str(guild_id), keep_count),
        )

        if not keep_result:
            return 0

        keep_ids = [str(row["id"]) for row in keep_result]
        placeholders = ",".join(["?"] * len(keep_ids))

        # Deletar backups antigos
        result = await database.run(
            f"DELETE FROM backups WHERE guild_id = ? AND id NOT IN ({placeholders})",
            [str(guild_id)] + keep_ids,
        )

        return result.rowcount if hasattr(result, "rowcount") else 0

    except Exception as e:
        print(f"❌ Erro limpando backups antigos: {e}")
        return 0


async def export_backup_data(guild_id: int, backup_name: str) -> str | None:
    """Exportar dados do backup como JSON"""
    try:
        backup = await get_backup(guild_id, backup_name)
        if not backup:
            return None

        export_data = {
            "backup_info": {
                "name": backup["backup_name"],
                "created_at": backup["created_at"],
                "created_by": backup["created_by"],
                "description": backup.get("description"),
                "guild_id": backup["guild_id"],
            },
            "data": backup["backup_data"],
        }

        return json.dumps(export_data, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"❌ Erro exportando backup: {e}")
        return None


async def import_backup_data(
    guild_id: int, backup_json: str, imported_by: int, new_name: str = None
) -> int | None:
    """Importar dados de backup de JSON"""
    try:
        import_data = json.loads(backup_json)

        # Validar estrutura
        if "backup_info" not in import_data or "data" not in import_data:
            raise ValueError("Formato de backup inválido")

        backup_info = import_data["backup_info"]
        backup_data = import_data["data"]

        # Usar nome fornecido ou nome original com sufixo
        backup_name = new_name or f"{backup_info.get('name', 'imported')}_imported"

        # Criar backup importado
        backup_id = await create_backup(
            guild_id=guild_id,
            backup_name=backup_name,
            backup_data=backup_data,
            created_by=imported_by,
            description=f"Importado de backup: {backup_info.get('name', 'desconhecido')}",
        )

        return backup_id

    except Exception as e:
        print(f"❌ Erro importando backup: {e}")
        return None
