"""
Sistema de Banco de Dados SQLite para o Bot Discord
Gerenciamento completo de todas as tabelas e operações de banco
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiosqlite

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime


class Database:
    """Sistema de gerenciamento de banco de dados SQLite."""

    _initialized: bool = False

    def __init__(self) -> None:
        self.db_path: str | None = None
        self.connection: aiosqlite.Connection | None = None

    async def init(self) -> None:
        """Inicializar conexão e criar tabelas necessárias"""
        # Proteção contra inicialização múltipla
        if Database._initialized:
            print("✅ Database já estava inicializado")
            return

        try:
            # Criar diretório data se não existir
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(parents=True, exist_ok=True)

            self.db_path = str(data_dir / "bot.db")

            # Criar tabelas
            await self.create_tables()
            Database._initialized = True
            print("✅ Database SQLite inicializado com sucesso!")
        except Exception as e:
            if "threads can only be started once" in str(e):
                print("⚠️ Database já foi inicializado em outra instância")
                Database._initialized = True
            else:
                raise e

    async def get_connection(self) -> aiosqlite.Connection:
        """Obter conexão com o banco"""
        if not self.db_path:
            msg = "Database não inicializado"
            raise RuntimeError(msg)
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
                    total_xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 0,
                    messages_sent INTEGER DEFAULT 0,
                    last_xp_gain DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, user_id)
                )
            """)

            # Sistema de warnings
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER NOT NULL,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    moderator_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT,
                    duration TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, case_id)
                )
            """)

            # Configurações dos servidores
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT UNIQUE NOT NULL,
                    prefix TEXT DEFAULT '!',
                    welcome_channel TEXT,
                    log_channel TEXT,
                    moderation_enabled INTEGER DEFAULT 1,
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

            # Sistema de autorole
            await db.execute("""
                CREATE TABLE IF NOT EXISTS autorole_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    rule_id TEXT NOT NULL,
                    rule_name TEXT NOT NULL,
                    rule_data TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, rule_id)
                )
            """)

            await db.commit()

    async def get(self, query: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        """Executar query SELECT e retornar um resultado"""
        async with await self.get_connection() as db, db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if row:
                # Converter para dict
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row, strict=False))
            return None

    async def get_all(
        self, query: str, params: Sequence[Any] = ()
    ) -> list[dict[str, Any]]:
        """Executar query SELECT e retornar todos os resultados"""
        async with await self.get_connection() as db, db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            if rows:
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row, strict=False)) for row in rows]
            return []

    async def run(self, query: str, params: Sequence[Any] = ()) -> aiosqlite.Cursor:
        """Executar query INSERT/UPDATE/DELETE"""
        async with await self.get_connection() as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.lastrowid

    async def run_many(
        self, query: str, params_list: Sequence[Sequence[Any]]
    ) -> None:
        """Executar múltiplas queries do mesmo tipo"""
        async with await self.get_connection() as db:
            await db.executemany(query, params_list)
            await db.commit()

    # Aliases para compatibilidade com código existente
    async def fetchone(
        self, query: str, params: Sequence[Any] = ()
    ) -> dict[str, Any] | None:
        """Alias para get() - compatibilidade"""
        return await self.get(query, params)

    async def fetchall(
        self, query: str, params: Sequence[Any] = ()
    ) -> list[dict[str, Any]]:
        """Alias para get_all() - compatibilidade"""
        return await self.get_all(query, params)

    # Métodos específicos para diferentes sistemas

    async def add_warning(
        self,
        guild_id: str,
        user_id: str,
        moderator_id: str,
        reason: str | None = None,
    ) -> int:
        """Adicionar aviso a um usuário"""
        return await self.run(
            """INSERT INTO warnings
            (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)""",
            (guild_id, user_id, moderator_id, reason),
        )

    async def get_user_warnings(
        self, guild_id: str, user_id: str
    ) -> list[dict[str, Any]]:
        """Obter avisos de um usuário"""
        return await self.get_all(
            """SELECT * FROM warnings
            WHERE guild_id = ? AND user_id = ? AND active = 1
            ORDER BY created_at DESC""",
            (guild_id, user_id),
        )

    async def add_moderation_case(
        self,
        guild_id: str,
        user_id: str,
        moderator_id: str,
        action: str,
        reason: str | None = None,
    ) -> int:
        """Adicionar caso de moderação"""
        # Obter próximo case_id
        existing_cases = await self.get_all(
            """SELECT case_id FROM moderation_cases
            WHERE guild_id = ? ORDER BY case_id DESC LIMIT 1""",
            (guild_id,),
        )
        next_case_id = (existing_cases[0]["case_id"] + 1) if existing_cases else 1

        await self.run(
            """INSERT INTO moderation_cases
            (case_id, guild_id, user_id, moderator_id, action, reason)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (next_case_id, guild_id, user_id, moderator_id, action, reason),
        )

        return next_case_id

    async def get_guild_settings(self, guild_id: str) -> dict[str, Any] | None:
        """Obter configurações do servidor"""
        return await self.get(
            "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
        )

    async def update_guild_settings(self, guild_id: str, **kwargs: Any) -> None:
        """Atualizar configurações do servidor"""
        if not kwargs:
            return

        # Verificar se existe
        existing = await self.get_guild_settings(guild_id)
        if not existing:
            await self.run(
                "INSERT INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
            )

        # Atualizar campos
        set_clause = ", ".join([f"{key} = ?" for key in kwargs])
        values = [*list(kwargs.values()), guild_id]

        await self.run(
            f"""UPDATE guild_settings SET {set_clause},
            updated_at = CURRENT_TIMESTAMP WHERE guild_id = ?""",
            tuple(values),
        )

    async def add_xp(self, guild_id: str, user_id: str, xp_amount: int) -> int | None:
        """Adicionar XP a um usuário"""
        # Verificar se usuário já existe
        user_data = await self.get(
            "SELECT total_xp FROM user_levels WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )

        if user_data:
            new_xp = user_data["total_xp"] + xp_amount
            level = self._calculate_level(new_xp)
            await self.run(
                """UPDATE user_levels SET total_xp = ?, level = ?,
                messages_sent = messages_sent + 1,
                last_xp_gain = CURRENT_TIMESTAMP
                WHERE guild_id = ? AND user_id = ?""",
                (new_xp, level, guild_id, user_id),
            )
            return level

        # Criar novo registro
        level = self._calculate_level(xp_amount)
        await self.run(
            """INSERT INTO user_levels
            (guild_id, user_id, total_xp, level, messages_sent)
            VALUES (?, ?, ?, ?, 1)""",
            (guild_id, user_id, xp_amount, level),
        )
        return level

    def _calculate_level(self, total_xp: int) -> int:
        """Calcular nível baseado no XP total usando fórmula: level = floor(sqrt(xp / 100))"""
        return int(math.sqrt(total_xp / 100))

    async def get_user_level(self, guild_id: str, user_id: str) -> dict[str, Any] | None:
        """Obter dados de nível do usuário"""
        return await self.get(
            """SELECT * FROM user_levels
            WHERE guild_id = ? AND user_id = ?""",
            (guild_id, user_id),
        )

    async def get_leaderboard(
        self, guild_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Obter ranking de XP do servidor"""
        return await self.get_all(
            """SELECT * FROM user_levels
            WHERE guild_id = ? ORDER BY total_xp DESC LIMIT ?""",
            (guild_id, limit),
        )

    async def create_giveaway(
        self,
        guild_id: str,
        channel_id: str,
        message_id: str,
        host_id: str,
        title: str,
        winners: int,
        end_time: datetime,
    ) -> int:
        """Criar um giveaway"""
        return await self.run(
            """INSERT INTO giveaways
            (guild_id, channel_id, message_id, host_id, title, winners, end_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (guild_id, channel_id, message_id, host_id, title, winners, end_time),
        )

    async def get_active_giveaways(self, guild_id: str) -> list[dict[str, Any]]:
        """Obter giveaways ativos do servidor"""
        return await self.get_all(
            """SELECT * FROM giveaways
            WHERE guild_id = ? AND ended = 0 ORDER BY end_time ASC""",
            (guild_id,),
        )


# Instância global do banco de dados
database = Database()
