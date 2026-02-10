"""
Antispam Data Module - Funções para manipular configuração anti-spam
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


async def save_antispam(guild_id: int, config: dict) -> bool:
    """Salvar configuração de anti-spam"""
    try:
        await database.run(
            """INSERT OR REPLACE INTO antispam_config 
               (guild_id, enabled, limite, intervalo, acao, warn_threshold, mute_threshold, kick_threshold, ban_threshold)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(guild_id),
                config.get("enabled", False),
                config.get("limite", 5),
                config.get("intervalo", 10),
                config.get("acao", "delete"),
                config.get("warn_threshold", 3),
                config.get("mute_threshold", 5),
                config.get("kick_threshold", 7),
                config.get("ban_threshold", 10),
            ),
        )
        return True

    except Exception as e:
        print(f"❌ Erro salvando config antispam: {e}")
        return False


async def get_antispam(guild_id: int) -> dict:
    """Buscar configuração de anti-spam"""
    try:
        result = await database.fetchone(
            "SELECT * FROM antispam_config WHERE guild_id = ?", (str(guild_id),)
        )

        if result:
            return {
                "enabled": bool(result["enabled"]),
                "limite": result["limite"],
                "intervalo": result["intervalo"],
                "acao": result["acao"],
                "warn_threshold": result["warn_threshold"],
                "mute_threshold": result["mute_threshold"],
                "kick_threshold": result["kick_threshold"],
                "ban_threshold": result["ban_threshold"],
            }

        return None

    except Exception as e:
        print(f"❌ Erro buscando config antispam: {e}")
        return None


async def delete_antispam(guild_id: int) -> bool:
    """Deletar configuração de anti-spam"""
    try:
        await database.run("DELETE FROM antispam_config WHERE guild_id = ?", (str(guild_id),))
        return True

    except Exception as e:
        print(f"❌ Erro deletando config antispam: {e}")
        return False


async def update_antispam_setting(guild_id: int, setting: str, value) -> bool:
    """Atualizar configuração específica de anti-spam"""
    try:
        # Verificar se a configuração existe
        existing = await get_antispam(guild_id)
        if not existing:
            # Criar configuração padrão
            default_config = {
                "enabled": False,
                "limite": 5,
                "intervalo": 10,
                "acao": "delete",
                "warn_threshold": 3,
                "mute_threshold": 5,
                "kick_threshold": 7,
                "ban_threshold": 10,
            }
            default_config[setting] = value
            return await save_antispam(guild_id, default_config)

        # Atualizar setting específico
        valid_settings = [
            "enabled",
            "limite",
            "intervalo",
            "acao",
            "warn_threshold",
            "mute_threshold",
            "kick_threshold",
            "ban_threshold",
        ]

        if setting not in valid_settings:
            return False

        await database.run(
            f"UPDATE antispam_config SET {setting} = ? WHERE guild_id = ?", (value, str(guild_id))
        )

        return True

    except Exception as e:
        print(f"❌ Erro atualizando setting antispam: {e}")
        return False


async def get_all_antispam_guilds() -> list:
    """Buscar todos os servidores com configuração de anti-spam"""
    try:
        result = await database.fetchall("SELECT guild_id FROM antispam_config WHERE enabled = 1")

        return [row["guild_id"] for row in result] if result else []

    except Exception as e:
        print(f"❌ Erro buscando guilds antispam: {e}")
        return []
