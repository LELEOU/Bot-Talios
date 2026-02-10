"""
Giveaways Data Module - Funções para manipular giveaways
"""

import datetime
import json
import random
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


async def initialize_giveaway_tables():
    """Inicializar tabelas de giveaway"""
    try:
        # Tabela principal de giveaways
        await database.run("""
            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                message_id TEXT NOT NULL UNIQUE,
                prize TEXT NOT NULL,
                winners INTEGER NOT NULL DEFAULT 1,
                end_time TEXT NOT NULL,
                creator_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                requirements TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de participantes dos giveaways
        await database.run("""
            CREATE TABLE IF NOT EXISTS giveaway_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                giveaway_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (giveaway_id) REFERENCES giveaways (id) ON DELETE CASCADE,
                UNIQUE(giveaway_id, user_id)
            )
        """)

        print("✅ Tabelas de giveaway inicializadas")

    except Exception as e:
        print(f"❌ Erro inicializando tabelas giveaway: {e}")


async def create_giveaway(
    guild_id: int,
    channel_id: int,
    message_id: int,
    prize: str,
    winners: int,
    end_time: datetime.datetime,
    creator_id: int,
    requirements: dict = None,
) -> int:
    """Criar novo giveaway"""
    try:
        result = await database.run(
            """INSERT INTO giveaways 
               (guild_id, channel_id, message_id, prize, winners, end_time, creator_id, requirements)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(guild_id),
                str(channel_id),
                str(message_id),
                prize,
                winners,
                end_time.isoformat(),
                str(creator_id),
                json.dumps(requirements) if requirements else None,
            ),
        )

        return result.lastrowid if hasattr(result, "lastrowid") else 0

    except Exception as e:
        print(f"❌ Erro criando giveaway: {e}")
        return 0


async def get_giveaway(giveaway_id: int = None, message_id: int = None) -> dict:
    """Buscar giveaway por ID ou message_id"""
    try:
        if giveaway_id:
            query = "SELECT * FROM giveaways WHERE id = ?"
            params = (giveaway_id,)
        elif message_id:
            query = "SELECT * FROM giveaways WHERE message_id = ?"
            params = (str(message_id),)
        else:
            return None

        result = await database.fetchone(query, params)

        if result:
            giveaway = dict(result)
            if giveaway.get("requirements"):
                giveaway["requirements"] = json.loads(giveaway["requirements"])
            return giveaway

        return None

    except Exception as e:
        print(f"❌ Erro buscando giveaway: {e}")
        return None


async def get_active_giveaways(guild_id: int = None) -> list:
    """Buscar giveaways ativos"""
    try:
        if guild_id:
            query = "SELECT * FROM giveaways WHERE guild_id = ? AND status = 'active'"
            params = (str(guild_id),)
        else:
            query = "SELECT * FROM giveaways WHERE status = 'active'"
            params = ()

        result = await database.fetchall(query, params)

        giveaways = []
        for row in result:
            giveaway = dict(row)
            if giveaway.get("requirements"):
                giveaway["requirements"] = json.loads(giveaway["requirements"])
            giveaways.append(giveaway)

        return giveaways

    except Exception as e:
        print(f"❌ Erro buscando giveaways ativos: {e}")
        return []


async def get_expired_giveaways() -> list:
    """Buscar giveaways que expiraram"""
    try:
        now = datetime.datetime.utcnow().isoformat()

        result = await database.fetchall(
            "SELECT * FROM giveaways WHERE status = 'active' AND end_time <= ?", (now,)
        )

        giveaways = []
        for row in result:
            giveaway = dict(row)
            if giveaway.get("requirements"):
                giveaway["requirements"] = json.loads(giveaway["requirements"])
            giveaways.append(giveaway)

        return giveaways

    except Exception as e:
        print(f"❌ Erro buscando giveaways expirados: {e}")
        return []


async def add_giveaway_entry(giveaway_id: int, user_id: int) -> bool:
    """Adicionar participante ao giveaway"""
    try:
        await database.run(
            "INSERT OR IGNORE INTO giveaway_entries (giveaway_id, user_id) VALUES (?, ?)",
            (giveaway_id, str(user_id)),
        )

        return True

    except Exception as e:
        print(f"❌ Erro adicionando entrada no giveaway: {e}")
        return False


async def remove_giveaway_entry(giveaway_id: int, user_id: int) -> bool:
    """Remover participante do giveaway"""
    try:
        await database.run(
            "DELETE FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?",
            (giveaway_id, str(user_id)),
        )

        return True

    except Exception as e:
        print(f"❌ Erro removendo entrada do giveaway: {e}")
        return False


async def get_giveaway_entries(giveaway_id: int) -> list:
    """Buscar participantes do giveaway"""
    try:
        result = await database.fetchall(
            "SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?", (giveaway_id,)
        )

        return [int(row["user_id"]) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando entradas do giveaway: {e}")
        return []


async def get_giveaway_entry_count(giveaway_id: int) -> int:
    """Contar participantes do giveaway"""
    try:
        result = await database.fetchone(
            "SELECT COUNT(*) as count FROM giveaway_entries WHERE giveaway_id = ?", (giveaway_id,)
        )

        return result["count"] if result else 0

    except Exception as e:
        print(f"❌ Erro contando entradas do giveaway: {e}")
        return 0


async def select_giveaway_winners(giveaway_id: int, winner_count: int) -> list:
    """Selecionar vencedores aleatórios do giveaway"""
    try:
        entries = await get_giveaway_entries(giveaway_id)

        if not entries:
            return []

        # Selecionar vencedores aleatórios
        winner_count = min(winner_count, len(entries))
        winners = random.sample(entries, winner_count)

        return winners

    except Exception as e:
        print(f"❌ Erro selecionando vencedores: {e}")
        return []


async def end_giveaway(giveaway_id: int, winners: list = None) -> bool:
    """Finalizar giveaway"""
    try:
        await database.run("UPDATE giveaways SET status = 'ended' WHERE id = ?", (giveaway_id,))

        # Salvar vencedores se fornecidos
        if winners:
            for winner_id in winners:
                await database.run(
                    """INSERT INTO giveaway_winners (giveaway_id, user_id, selected_at)
                       VALUES (?, ?, ?)""",
                    (giveaway_id, str(winner_id), datetime.datetime.utcnow().isoformat()),
                )

        return True

    except Exception as e:
        print(f"❌ Erro finalizando giveaway: {e}")
        return False


async def cancel_giveaway(giveaway_id: int) -> bool:
    """Cancelar giveaway"""
    try:
        await database.run("UPDATE giveaways SET status = 'cancelled' WHERE id = ?", (giveaway_id,))

        return True

    except Exception as e:
        print(f"❌ Erro cancelando giveaway: {e}")
        return False


async def delete_giveaway(giveaway_id: int) -> bool:
    """Deletar giveaway completamente"""
    try:
        # Deletar entradas primeiro (CASCADE deve fazer isso automaticamente)
        await database.run("DELETE FROM giveaway_entries WHERE giveaway_id = ?", (giveaway_id,))

        # Deletar giveaway
        await database.run("DELETE FROM giveaways WHERE id = ?", (giveaway_id,))

        return True

    except Exception as e:
        print(f"❌ Erro deletando giveaway: {e}")
        return False


async def user_joined_giveaway(giveaway_id: int, user_id: int) -> bool:
    """Verificar se usuário já participou do giveaway"""
    try:
        result = await database.fetchone(
            "SELECT id FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?",
            (giveaway_id, str(user_id)),
        )

        return result is not None

    except Exception as e:
        print(f"❌ Erro verificando participação no giveaway: {e}")
        return False
