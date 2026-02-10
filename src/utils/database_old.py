"""
Sistema de Banco de Dados SQLite para o Bot Discord
Gerenciamento completo de todas as tabelas e operações de banco
"""

from __future__ import annotations

import os
from typing import Any

import aiosqlite


class Database:
    def __init__(self) -> None:
        self.db_path: str | None = None
        self.connection: aiosqlite.Connection | None = None

    async def init(self) -> None:
        """Inicializar conexão e criar tabelas necessárias"""
        # Criar diretório data se não existir
        data_dir: str = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        os.makedirs(data_dir, exist_ok=True)

        self.db_path = os.path.join(data_dir, "bot.db")

        # Criar tabelas
        await self.create_tables()
        print("✅ Database SQLite inicializado com sucesso!")

    async def get_connection(self) -> aiosqlite.Connection:
        """Obter conexão com o banco"""
        return await aiosqlite.connect(self.db_path)

    async def create_tables(self) -> None:
        """Criar todas as tabelas necessárias"""
        async with await self.get_connection() as db:
            # Sistema de tickets
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    closed_at DATETIME,
                    status TEXT DEFAULT 'open',
                    reason TEXT,
                    closed_by TEXT
                )
            """)

            # Sistema de leveling
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_levels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 0,
                    messages INTEGER DEFAULT 0,
                    last_message DATETIME,
                    UNIQUE(guild_id, user_id)
                )
            """)

            # Sistema de avisos/warns
            await db.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    moderator_id TEXT NOT NULL,
                    reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    active INTEGER DEFAULT 1
                )
            """)

            # Sistema de casos de moderação
            await db.execute("""
                CREATE TABLE IF NOT EXISTS moderation_cases (
                    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    moderator_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    duration TEXT,
                    active INTEGER DEFAULT 1
                )
            """)

            # Sistema de configurações do servidor
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id TEXT PRIMARY KEY,
                    welcome_channel TEXT,
                    log_channel TEXT,
                    mod_channel TEXT,
                    antispam_enabled INTEGER DEFAULT 0,
                    leveling_enabled INTEGER DEFAULT 1,
                    settings_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Sistema de giveaways
            await db.execute("""
                CREATE TABLE IF NOT EXISTS giveaways (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    host_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    winners INTEGER DEFAULT 1,
                    end_time DATETIME NOT NULL,
                    ended INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Sistema de roles temporários
            await db.execute("""
                CREATE TABLE IF NOT EXISTS temp_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role_id TEXT NOT NULL,
                    expires_at DATETIME NOT NULL,
                    reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Sistema de sticky messages
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sticky_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    message_content TEXT NOT NULL,
                    embed_json TEXT,
                    active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Sistema de suggestions
            await db.execute("""
                CREATE TABLE IF NOT EXISTS suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    suggestion TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    votes_up INTEGER DEFAULT 0,
                    votes_down INTEGER DEFAULT 0,
                    message_id TEXT,
                    channel_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Sistema de backup
            await db.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    restored_at DATETIME
                )
            """)

            await db.commit()

    async def get(self, query: str, params: tuple = ()) -> dict[str, Any] | None:
        """Executar query SELECT e retornar um resultado"""
        async with await self.get_connection() as db, db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if row:
                # Converter para dict
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row, strict=False))
            return None

    async def get_all(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Executar query SELECT e retornar todos os resultados"""
        async with await self.get_connection() as db, db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            if rows:
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row, strict=False)) for row in rows]
            return []

    async def run(self, query: str, params: tuple = ()) -> None:
        """Executar query INSERT/UPDATE/DELETE"""
        async with await self.get_connection() as db:
            await db.execute(query, params)
            await db.commit()

    async def run_many(self, query: str, params_list: list[tuple]) -> None:
        """Executar múltiplas queries do mesmo tipo"""
        async with await self.get_connection() as db:
            await db.executemany(query, params_list)
            await db.commit()

    # Métodos específicos para diferentes sistemas

    async def add_warning(self, guild_id: str, user_id: str, moderator_id: str, reason: str | None = None) -> None:
        """Adicionar aviso a um usuário"""
        await self.run(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, reason),
        )

    async def get_user_warnings(self, guild_id: str, user_id: str) -> list[dict[str, Any]]:
        """Obter avisos de um usuário"""
        return await self.get_all(
            "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? AND active = 1 ORDER BY created_at DESC",
            (guild_id, user_id),
        )

    async def add_moderation_case(
        self, guild_id: str, user_id: str, moderator_id: str, action: str, reason: str | None = None
    ) -> int | None:
        """Adicionar caso de moderação"""
        await self.run(
            "INSERT INTO moderation_cases (guild_id, user_id, moderator_id, action, reason) VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, action, reason),
        )

        # Retornar o case_id
        result = await self.get("SELECT last_insert_rowid() as case_id")
        return result["case_id"] if result else None

    async def get_guild_settings(self, guild_id: str) -> dict[str, Any] | None:
        """Obter configurações do servidor"""
        return await self.get("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,))

    async def update_guild_settings(self, guild_id: str, **kwargs: Any) -> None:
        """Atualizar configurações do servidor"""
        if not kwargs:
            return

        # Verificar se existe
        existing = await self.get_guild_settings(guild_id)
        if not existing:
            await self.run("INSERT INTO guild_settings (guild_id) VALUES (?)", (guild_id,))

        # Atualizar campos
        set_clause: str = ", ".join([f"{key} = ?" for key in kwargs])
        values: list[Any] = list(kwargs.values()) + [guild_id]

        await self.run(
            f"UPDATE guild_settings SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE guild_id = ?",
            tuple(values),
        )


# Instância global do banco de dados
database = Database()
