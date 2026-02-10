"""
Suggestions Data Module - Sistema de sugestões
"""

import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


async def initialize_suggestions_tables():
    """Inicializar tabelas de sugestões"""
    try:
        # Tabela principal de sugestões
        await database.run("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                message_id TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                votes_up INTEGER DEFAULT 0,
                votes_down INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                reviewed_at DATETIME,
                reviewed_by TEXT,
                review_reason TEXT
            )
        """)

        # Tabela de votos em sugestões
        await database.run("""
            CREATE TABLE IF NOT EXISTS suggestion_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suggestion_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                vote_type TEXT NOT NULL CHECK(vote_type IN ('up', 'down')),
                voted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (suggestion_id) REFERENCES suggestions (id) ON DELETE CASCADE,
                UNIQUE(suggestion_id, user_id)
            )
        """)

        # Tabela de configuração de sugestões
        await database.run("""
            CREATE TABLE IF NOT EXISTS suggestion_config (
                guild_id TEXT PRIMARY KEY,
                enabled BOOLEAN DEFAULT 1,
                suggestion_channel_id TEXT,
                review_channel_id TEXT,
                auto_react BOOLEAN DEFAULT 1,
                up_emoji TEXT DEFAULT '👍',
                down_emoji TEXT DEFAULT '👎',
                dm_user BOOLEAN DEFAULT 1,
                anonymous_suggestions BOOLEAN DEFAULT 0,
                cooldown_minutes INTEGER DEFAULT 5,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        print("✅ Tabelas de sugestões inicializadas")

    except Exception as e:
        print(f"❌ Erro inicializando tabelas sugestões: {e}")


async def get_suggestion_config(guild_id: int) -> dict | None:
    """Buscar configuração de sugestões"""
    try:
        result = await database.fetchone(
            "SELECT * FROM suggestion_config WHERE guild_id = ?", (str(guild_id),)
        )

        if result:
            return dict(result)

        # Configuração padrão
        return {
            "enabled": True,
            "suggestion_channel_id": None,
            "review_channel_id": None,
            "auto_react": True,
            "up_emoji": "👍",
            "down_emoji": "👎",
            "dm_user": True,
            "anonymous_suggestions": False,
            "cooldown_minutes": 5,
        }

    except Exception as e:
        print(f"❌ Erro buscando config sugestões: {e}")
        return None


async def save_suggestion_config(guild_id: int, config: dict) -> bool:
    """Salvar configuração de sugestões"""
    try:
        await database.run(
            """INSERT OR REPLACE INTO suggestion_config 
               (guild_id, enabled, suggestion_channel_id, review_channel_id, auto_react,
                up_emoji, down_emoji, dm_user, anonymous_suggestions, cooldown_minutes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(guild_id),
                config.get("enabled", True),
                config.get("suggestion_channel_id"),
                config.get("review_channel_id"),
                config.get("auto_react", True),
                config.get("up_emoji", "👍"),
                config.get("down_emoji", "👎"),
                config.get("dm_user", True),
                config.get("anonymous_suggestions", False),
                config.get("cooldown_minutes", 5),
            ),
        )

        return True

    except Exception as e:
        print(f"❌ Erro salvando config sugestões: {e}")
        return False


async def create_suggestion(
    guild_id: int, channel_id: int, message_id: int, user_id: int, content: str
) -> int:
    """Criar nova sugestão"""
    try:
        result = await database.run(
            """INSERT INTO suggestions 
               (guild_id, channel_id, message_id, user_id, content)
               VALUES (?, ?, ?, ?, ?)""",
            (str(guild_id), str(channel_id), str(message_id), str(user_id), content),
        )

        return result.lastrowid if hasattr(result, "lastrowid") else 0

    except Exception as e:
        print(f"❌ Erro criando sugestão: {e}")
        return 0


async def get_suggestion(suggestion_id: int = None, message_id: int = None) -> dict | None:
    """Buscar sugestão por ID ou message_id"""
    try:
        if suggestion_id:
            query = "SELECT * FROM suggestions WHERE id = ?"
            params = (suggestion_id,)
        elif message_id:
            query = "SELECT * FROM suggestions WHERE message_id = ?"
            params = (str(message_id),)
        else:
            return None

        result = await database.fetchone(query, params)

        return dict(result) if result else None

    except Exception as e:
        print(f"❌ Erro buscando sugestão: {e}")
        return None


async def add_suggestion_vote(suggestion_id: int, user_id: int, vote_type: str) -> bool:
    """Adicionar voto à sugestão"""
    try:
        # Remover voto anterior se existir
        await database.run(
            "DELETE FROM suggestion_votes WHERE suggestion_id = ? AND user_id = ?",
            (suggestion_id, str(user_id)),
        )

        # Adicionar novo voto
        await database.run(
            "INSERT INTO suggestion_votes (suggestion_id, user_id, vote_type) VALUES (?, ?, ?)",
            (suggestion_id, str(user_id), vote_type),
        )

        # Atualizar contadores na sugestão
        await update_suggestion_votes(suggestion_id)

        return True

    except Exception as e:
        print(f"❌ Erro adicionando voto: {e}")
        return False


async def remove_suggestion_vote(suggestion_id: int, user_id: int) -> bool:
    """Remover voto da sugestão"""
    try:
        await database.run(
            "DELETE FROM suggestion_votes WHERE suggestion_id = ? AND user_id = ?",
            (suggestion_id, str(user_id)),
        )

        # Atualizar contadores
        await update_suggestion_votes(suggestion_id)

        return True

    except Exception as e:
        print(f"❌ Erro removendo voto: {e}")
        return False


async def update_suggestion_votes(suggestion_id: int) -> bool:
    """Atualizar contadores de votos da sugestão"""
    try:
        # Contar votos positivos
        result_up = await database.fetchone(
            "SELECT COUNT(*) as count FROM suggestion_votes WHERE suggestion_id = ? AND vote_type = 'up'",
            (suggestion_id,),
        )
        votes_up = result_up["count"] if result_up else 0

        # Contar votos negativos
        result_down = await database.fetchone(
            "SELECT COUNT(*) as count FROM suggestion_votes WHERE suggestion_id = ? AND vote_type = 'down'",
            (suggestion_id,),
        )
        votes_down = result_down["count"] if result_down else 0

        # Atualizar sugestão
        await database.run(
            "UPDATE suggestions SET votes_up = ?, votes_down = ? WHERE id = ?",
            (votes_up, votes_down, suggestion_id),
        )

        return True

    except Exception as e:
        print(f"❌ Erro atualizando votos: {e}")
        return False


async def review_suggestion(
    suggestion_id: int, reviewer_id: int, status: str, reason: str = None
) -> bool:
    """Revisar sugestão (aprovar/rejeitar)"""
    try:
        await database.run(
            """UPDATE suggestions 
               SET status = ?, reviewed_at = ?, reviewed_by = ?, review_reason = ?
               WHERE id = ?""",
            (
                status,
                datetime.datetime.utcnow().isoformat(),
                str(reviewer_id),
                reason,
                suggestion_id,
            ),
        )

        return True

    except Exception as e:
        print(f"❌ Erro revisando sugestão: {e}")
        return False


async def get_user_suggestions(guild_id: int, user_id: int, limit: int = 10) -> list[dict]:
    """Buscar sugestões do usuário"""
    try:
        result = await database.fetchall(
            """SELECT * FROM suggestions 
               WHERE guild_id = ? AND user_id = ? 
               ORDER BY created_at DESC LIMIT ?""",
            (str(guild_id), str(user_id), limit),
        )

        return [dict(row) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando sugestões do usuário: {e}")
        return []


async def get_guild_suggestions(guild_id: int, status: str = None, limit: int = 50) -> list[dict]:
    """Buscar sugestões do servidor"""
    try:
        if status:
            query = """SELECT * FROM suggestions 
                      WHERE guild_id = ? AND status = ? 
                      ORDER BY created_at DESC LIMIT ?"""
            params = (str(guild_id), status, limit)
        else:
            query = """SELECT * FROM suggestions 
                      WHERE guild_id = ? 
                      ORDER BY created_at DESC LIMIT ?"""
            params = (str(guild_id), limit)

        result = await database.fetchall(query, params)

        return [dict(row) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando sugestões do servidor: {e}")
        return []


async def delete_suggestion(suggestion_id: int) -> bool:
    """Deletar sugestão"""
    try:
        await database.run("DELETE FROM suggestions WHERE id = ?", (suggestion_id,))

        return True

    except Exception as e:
        print(f"❌ Erro deletando sugestão: {e}")
        return False


async def get_user_vote(suggestion_id: int, user_id: int) -> str | None:
    """Buscar voto do usuário na sugestão"""
    try:
        result = await database.fetchone(
            "SELECT vote_type FROM suggestion_votes WHERE suggestion_id = ? AND user_id = ?",
            (suggestion_id, str(user_id)),
        )

        return result["vote_type"] if result else None

    except Exception as e:
        print(f"❌ Erro buscando voto do usuário: {e}")
        return None


async def get_suggestion_stats(guild_id: int) -> dict:
    """Buscar estatísticas de sugestões"""
    try:
        result = await database.fetchall(
            "SELECT status, COUNT(*) as count FROM suggestions WHERE guild_id = ? GROUP BY status",
            (str(guild_id),),
        )

        stats = {"total": 0, "pending": 0, "approved": 0, "rejected": 0}

        for row in result:
            stats[row["status"]] = row["count"]
            stats["total"] += row["count"]

        return stats

    except Exception as e:
        print(f"❌ Erro buscando estatísticas: {e}")
        return {"total": 0, "pending": 0, "approved": 0, "rejected": 0}
