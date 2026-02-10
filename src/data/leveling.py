"""
Leveling Data Module - Funções para sistema de leveling/XP
"""

import math
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


async def initialize_leveling_tables():
    """Inicializar tabelas de leveling"""
    try:
        # Tabela de XP dos usuários
        await database.run("""
            CREATE TABLE IF NOT EXISTS user_levels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                xp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 1,
                total_messages INTEGER NOT NULL DEFAULT 0,
                last_message DATETIME,
                UNIQUE(guild_id, user_id)
            )
        """)

        # Tabela de configuração de leveling
        await database.run("""
            CREATE TABLE IF NOT EXISTS leveling_config (
                guild_id TEXT PRIMARY KEY,
                enabled BOOLEAN DEFAULT 1,
                xp_per_message INTEGER DEFAULT 15,
                xp_cooldown INTEGER DEFAULT 60,
                level_up_channel_id TEXT,
                level_up_message TEXT DEFAULT 'Parabéns {user}! Você subiu para o level {level}!',
                announce_level_up BOOLEAN DEFAULT 1,
                ignore_bots BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de recompensas por level
        await database.run("""
            CREATE TABLE IF NOT EXISTS level_rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                level INTEGER NOT NULL,
                role_id TEXT,
                role_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, level)
            )
        """)

        print("✅ Tabelas de leveling inicializadas")

    except Exception as e:
        print(f"❌ Erro inicializando tabelas leveling: {e}")


def calculate_level_from_xp(xp: int) -> int:
    """Calcular level baseado no XP"""
    if xp < 0:
        return 1

    # Fórmula: level = √(xp / 100) + 1
    level = math.floor(math.sqrt(xp / 100)) + 1
    return max(1, level)


def calculate_xp_for_level(level: int) -> int:
    """Calcular XP necessário para um level"""
    if level <= 1:
        return 0

    # Fórmula inversa: xp = (level - 1)² * 100
    return (level - 1) ** 2 * 100


def get_xp_for_next_level(current_xp: int) -> tuple:
    """Calcular XP necessário para próximo level"""
    current_level = calculate_level_from_xp(current_xp)
    next_level = current_level + 1

    xp_needed = calculate_xp_for_level(next_level)
    xp_progress = current_xp - calculate_xp_for_level(current_level)
    xp_required = xp_needed - calculate_xp_for_level(current_level)

    return xp_progress, xp_required, next_level


async def get_leveling_config(guild_id: int) -> dict | None:
    """Buscar configuração de leveling do servidor"""
    try:
        result = await database.fetchone(
            "SELECT * FROM leveling_config WHERE guild_id = ?", (str(guild_id),)
        )

        if result:
            return dict(result)

        # Retornar configuração padrão se não existir
        return {
            "enabled": True,
            "xp_per_message": 15,
            "xp_cooldown": 60,
            "level_up_channel_id": None,
            "level_up_message": "Parabéns {user}! Você subiu para o level {level}!",
            "announce_level_up": True,
            "ignore_bots": True,
        }

    except Exception as e:
        print(f"❌ Erro buscando config leveling: {e}")
        return None


async def save_leveling_config(guild_id: int, config: dict) -> bool:
    """Salvar configuração de leveling"""
    try:
        await database.run(
            """INSERT OR REPLACE INTO leveling_config 
               (guild_id, enabled, xp_per_message, xp_cooldown, level_up_channel_id, 
                level_up_message, announce_level_up, ignore_bots)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(guild_id),
                config.get("enabled", True),
                config.get("xp_per_message", 15),
                config.get("xp_cooldown", 60),
                config.get("level_up_channel_id"),
                config.get("level_up_message", "Parabéns {user}! Você subiu para o level {level}!"),
                config.get("announce_level_up", True),
                config.get("ignore_bots", True),
            ),
        )

        return True

    except Exception as e:
        print(f"❌ Erro salvando config leveling: {e}")
        return False


async def get_user_level(guild_id: int, user_id: int) -> dict | None:
    """Buscar level do usuário"""
    try:
        result = await database.fetchone(
            "SELECT * FROM user_levels WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id)),
        )

        if result:
            user_data = dict(result)
            # Recalcular level baseado no XP atual
            correct_level = calculate_level_from_xp(user_data["xp"])

            if correct_level != user_data["level"]:
                # Atualizar level correto
                await database.run(
                    "UPDATE user_levels SET level = ? WHERE guild_id = ? AND user_id = ?",
                    (correct_level, str(guild_id), str(user_id)),
                )
                user_data["level"] = correct_level

            return user_data

        return None

    except Exception as e:
        print(f"❌ Erro buscando level do usuário: {e}")
        return None


async def add_xp(guild_id: int, user_id: int, xp_amount: int) -> dict:
    """Adicionar XP ao usuário"""
    try:
        # Buscar dados atuais do usuário
        user_data = await get_user_level(guild_id, user_id)

        if user_data:
            # Atualizar XP existente
            new_xp = user_data["xp"] + xp_amount
            new_level = calculate_level_from_xp(new_xp)
            old_level = user_data["level"]

            await database.run(
                """UPDATE user_levels 
                   SET xp = ?, level = ?, total_messages = total_messages + 1, last_message = ?
                   WHERE guild_id = ? AND user_id = ?""",
                (new_xp, new_level, "now", str(guild_id), str(user_id)),
            )

            return {
                "xp": new_xp,
                "level": new_level,
                "old_level": old_level,
                "level_up": new_level > old_level,
                "total_messages": user_data["total_messages"] + 1,
            }
        # Criar novo registro
        initial_xp = xp_amount
        initial_level = calculate_level_from_xp(initial_xp)

        await database.run(
            """INSERT INTO user_levels 
                   (guild_id, user_id, xp, level, total_messages, last_message)
                   VALUES (?, ?, ?, ?, 1, ?)""",
            (str(guild_id), str(user_id), initial_xp, initial_level, "now"),
        )

        return {
            "xp": initial_xp,
            "level": initial_level,
            "old_level": 0,
            "level_up": initial_level > 1,
            "total_messages": 1,
        }

    except Exception as e:
        print(f"❌ Erro adicionando XP: {e}")
        return {"xp": 0, "level": 1, "old_level": 0, "level_up": False, "total_messages": 0}


async def set_user_xp(guild_id: int, user_id: int, xp: int) -> bool:
    """Definir XP do usuário"""
    try:
        level = calculate_level_from_xp(xp)

        await database.run(
            """INSERT OR REPLACE INTO user_levels 
               (guild_id, user_id, xp, level, total_messages, last_message)
               VALUES (?, ?, ?, ?, COALESCE((SELECT total_messages FROM user_levels WHERE guild_id = ? AND user_id = ?), 0), ?)""",
            (str(guild_id), str(user_id), xp, level, str(guild_id), str(user_id), "now"),
        )

        return True

    except Exception as e:
        print(f"❌ Erro definindo XP do usuário: {e}")
        return False


async def get_leaderboard(guild_id: int, limit: int = 10) -> list[dict]:
    """Buscar ranking de XP do servidor"""
    try:
        result = await database.fetchall(
            """SELECT * FROM user_levels 
               WHERE guild_id = ? 
               ORDER BY xp DESC, level DESC, total_messages DESC 
               LIMIT ?""",
            (str(guild_id), limit),
        )

        return [dict(row) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando leaderboard: {e}")
        return []


async def get_user_rank(guild_id: int, user_id: int) -> int:
    """Buscar posição do usuário no ranking"""
    try:
        result = await database.fetchall(
            "SELECT user_id FROM user_levels WHERE guild_id = ? ORDER BY xp DESC, level DESC",
            (str(guild_id),),
        )

        for i, row in enumerate(result):
            if row["user_id"] == str(user_id):
                return i + 1

        return 0

    except Exception as e:
        print(f"❌ Erro buscando rank do usuário: {e}")
        return 0


async def add_level_reward(guild_id: int, level: int, role_id: int, role_name: str) -> bool:
    """Adicionar recompensa por level"""
    try:
        await database.run(
            """INSERT OR REPLACE INTO level_rewards (guild_id, level, role_id, role_name)
               VALUES (?, ?, ?, ?)""",
            (str(guild_id), level, str(role_id), role_name),
        )

        return True

    except Exception as e:
        print(f"❌ Erro adicionando recompensa de level: {e}")
        return False


async def remove_level_reward(guild_id: int, level: int) -> bool:
    """Remover recompensa por level"""
    try:
        await database.run(
            "DELETE FROM level_rewards WHERE guild_id = ? AND level = ?", (str(guild_id), level)
        )

        return True

    except Exception as e:
        print(f"❌ Erro removendo recompensa de level: {e}")
        return False


async def get_level_rewards(guild_id: int, level: int = None) -> list[dict]:
    """Buscar recompensas de level"""
    try:
        if level:
            query = "SELECT * FROM level_rewards WHERE guild_id = ? AND level = ?"
            params = (str(guild_id), level)
        else:
            query = "SELECT * FROM level_rewards WHERE guild_id = ? ORDER BY level ASC"
            params = (str(guild_id),)

        result = await database.fetchall(query, params)

        return [dict(row) for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando recompensas de level: {e}")
        return []


async def reset_user_level(guild_id: int, user_id: int) -> bool:
    """Resetar level do usuário"""
    try:
        await database.run(
            "DELETE FROM user_levels WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id)),
        )

        return True

    except Exception as e:
        print(f"❌ Erro resetando level do usuário: {e}")
        return False


async def reset_guild_levels(guild_id: int) -> bool:
    """Resetar todos os levels do servidor"""
    try:
        await database.run("DELETE FROM user_levels WHERE guild_id = ?", (str(guild_id),))

        return True

    except Exception as e:
        print(f"❌ Erro resetando levels do servidor: {e}")
        return False
