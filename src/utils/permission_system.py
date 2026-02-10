"""
Sistema de Permissões Avançado v2.0
Gerencia permissões customizadas, cargos personalizados e integração com dashboard
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiosqlite

from . import json_utils

if TYPE_CHECKING:
    from collections.abc import Awaitable

    import discord


class AdvancedPermissionSystem:
    """Sistema avançado de permissões com suporte a dashboard"""

    def __init__(self) -> None:
        data_dir = Path(__file__).parent.parent / "data"
        self.db_path: str = str(data_dir / "advanced_permissions.db")
        self._cache: dict[str, Any] = {}
        self._initialized: bool = False

    async def initialize(self) -> None:
        """Inicializar sistema de permissões"""
        if self._initialized:
            return

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            # Configurações do servidor
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_config (
                    guild_id TEXT PRIMARY KEY,
                    admin_role_ids TEXT,
                    mod_role_ids TEXT,
                    dj_role_ids TEXT,
                    support_role_ids TEXT,
                    dashboard_enabled BOOLEAN DEFAULT 1,
                    require_roles_for_moderation BOOLEAN DEFAULT 1,
                    require_roles_for_music BOOLEAN DEFAULT 0,
                    custom_config JSON,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Permissões por comando
            await db.execute("""
                CREATE TABLE IF NOT EXISTS command_overrides (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    command_name TEXT NOT NULL,
                    allowed_roles TEXT,
                    denied_roles TEXT,
                    allowed_users TEXT,
                    denied_users TEXT,
                    admin_only BOOLEAN DEFAULT 0,
                    mod_only BOOLEAN DEFAULT 0,
                    enabled BOOLEAN DEFAULT 1,
                    UNIQUE(guild_id, command_name)
                )
            """)

            # Estatísticas para dashboard
            await db.execute("""
                CREATE TABLE IF NOT EXISTS command_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    command_name TEXT NOT NULL,
                    category TEXT,
                    success BOOLEAN DEFAULT 1,
                    execution_time REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.commit()

        self._initialized = True

    async def get_guild_config(self, guild_id: str) -> dict:
        """Obter configuração do servidor com cache"""
        if guild_id in self._cache:
            return self._cache[guild_id]

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()

                if row:
                    config = dict(row)
                    # Parse JSON fields
                    if config.get("custom_config"):
                        config["custom_config"] = json_utils.loads(config["custom_config"])
                    else:
                        config["custom_config"] = {}
                else:
                    # Criar config padrão
                    config = {
                        "guild_id": guild_id,
                        "admin_role_ids": "",
                        "mod_role_ids": "",
                        "dj_role_ids": "",
                        "support_role_ids": "",
                        "dashboard_enabled": True,
                        "require_roles_for_moderation": True,
                        "require_roles_for_music": False,
                        "custom_config": {},
                    }

                    await db.execute(
                        """
                        INSERT INTO guild_config (guild_id) VALUES (?)
                    """,
                        (guild_id,),
                    )
                    await db.commit()

                self._cache[guild_id] = config
                return config

    async def update_config(self, guild_id: str, **kwargs: Any) -> None:
        """Atualizar configuração do servidor"""
        async with aiosqlite.connect(self.db_path) as db:
            # Converter custom_config para JSON se presente
            if "custom_config" in kwargs:
                kwargs["custom_config"] = json_utils.dumps(kwargs["custom_config"])

            fields = ", ".join([f"{k} = ?" for k in kwargs])
            values = list(kwargs.values()) + [guild_id]

            await db.execute(
                f"""
                UPDATE guild_config
                SET {fields}, updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = ?
            """,
                values,
            )
            await db.commit()

        # Limpar cache
        if guild_id in self._cache:
            del self._cache[guild_id]

    async def has_permission(
        self,
        interaction: discord.Interaction,
        command_name: str,
        category: str | None = None,
        require_admin: bool = False,
        require_mod: bool = False,
    ) -> tuple[bool, str]:
        """
        Verificar se usuário tem permissão
        Retorna: (tem_permissão, mensagem)
        """
        user = interaction.user
        guild_id = str(interaction.guild.id)

        # Dono do servidor sempre tem permissão
        if interaction.guild.owner_id == user.id:
            return True, "Dono do servidor"

        # Admin do Discord sempre tem permissão
        if user.guild_permissions.administrator:
            return True, "Administrador do Discord"

        # Obter configuração
        config = await self.get_guild_config(guild_id)

        # Verificar override específico do comando
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM command_overrides
                WHERE guild_id = ? AND command_name = ?
            """,
                (guild_id, command_name),
            ) as cursor:
                override = await cursor.fetchone()

                if override:
                    # Comando desabilitado
                    if not override["enabled"]:
                        return False, "Comando desabilitado neste servidor"

                    # Usuários negados
                    if override["denied_users"]:
                        if str(user.id) in override["denied_users"].split(","):
                            return False, "Você está na lista de negados"

                    # Usuários permitidos (whitelist)
                    if override["allowed_users"]:
                        if str(user.id) in override["allowed_users"].split(","):
                            return True, "Usuário permitido"

                    # Cargos negados
                    if override["denied_roles"]:
                        denied = set(override["denied_roles"].split(","))
                        user_roles = {str(r.id) for r in user.roles}
                        if denied & user_roles:
                            return False, "Seu cargo está na lista de negados"

                    # Verificar requerimentos do override
                    if override["admin_only"]:
                        require_admin = True
                    if override["mod_only"]:
                        require_mod = True

                    # Cargos permitidos
                    if override["allowed_roles"]:
                        allowed = set(override["allowed_roles"].split(","))
                        user_roles = {str(r.id) for r in user.roles}
                        if allowed & user_roles:
                            return True, "Cargo permitido"

        # Verificar requisito de admin
        if require_admin:
            admin_roles = config.get("admin_role_ids", "").split(",")
            admin_roles = [r for r in admin_roles if r]

            if admin_roles:
                user_roles = {str(r.id) for r in user.roles}
                if not any(role_id in user_roles for role_id in admin_roles):
                    return False, "Requer cargo de administrador configurado"

        # Verificar requisito de moderador
        if require_mod:
            mod_roles = config.get("mod_role_ids", "").split(",")
            mod_roles = [r for r in mod_roles if r]

            if mod_roles:
                user_roles = {str(r.id) for r in user.roles}
                if not any(role_id in user_roles for role_id in mod_roles):
                    return False, "Requer cargo de moderador configurado"

        # Verificar requisitos de categoria
        if category == "moderation" and config.get("require_roles_for_moderation"):
            mod_roles = config.get("mod_role_ids", "").split(",")
            admin_roles = config.get("admin_role_ids", "").split(",")
            required_roles = [r for r in (mod_roles + admin_roles) if r]

            if required_roles:
                user_roles = {str(r.id) for r in user.roles}
                if not any(role_id in user_roles for role_id in required_roles):
                    return False, "Comandos de moderação requerem cargo configurado"

        if category == "music" and config.get("require_roles_for_music"):
            dj_roles = config.get("dj_role_ids", "").split(",")
            dj_roles = [r for r in dj_roles if r]

            if dj_roles:
                user_roles = {str(r.id) for r in user.roles}
                if not any(role_id in user_roles for role_id in dj_roles):
                    return False, "Comandos de música requerem cargo DJ configurado"

        return True, "Permissão concedida"

    async def log_command(
        self,
        guild_id: str,
        user_id: str,
        command_name: str,
        category: str,
        success: bool,
        execution_time: float = 0.0,
    ) -> None:
        """Registrar uso de comando para analytics"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO command_analytics
                (guild_id, user_id, command_name, category, success, execution_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (guild_id, user_id, command_name, category, success, execution_time),
            )
            await db.commit()

    async def get_analytics(
        self, guild_id: str, days: int = 7
    ) -> dict[str, Any]:
        """Obter analytics para dashboard"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Comandos mais usados
            async with db.execute(
                """
                SELECT command_name, category, COUNT(*) as count
                FROM command_analytics
                WHERE guild_id = ? 
                AND datetime(timestamp) > datetime('now', '-' || ? || ' days')
                GROUP BY command_name, category
                ORDER BY count DESC
                LIMIT 10
            """,
                (guild_id, days),
            ) as cursor:
                top_commands = [dict(row) async for row in cursor]

            # Taxa de sucesso
            async with db.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                FROM command_analytics
                WHERE guild_id = ?
                AND datetime(timestamp) > datetime('now', '-' || ? || ' days')
            """,
                (guild_id, days),
            ) as cursor:
                stats = await cursor.fetchone()
                success_rate = (
                    (dict(stats)["successful"] / dict(stats)["total"] * 100)
                    if dict(stats)["total"] > 0
                    else 0
                )

            return {
                "top_commands": top_commands,
                "success_rate": round(success_rate, 2),
                "total_commands": dict(stats)["total"],
            }


# Singleton global
perm_system = AdvancedPermissionSystem()


def require_permission(
    category: str | None = None, admin: bool = False, mod: bool = False
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    Decorador para verificar permissões

    Uso:
    @require_permission(category="moderation", mod=True)
    @require_permission(admin=True)
    """

    def decorator(
        func: Callable[..., Awaitable[Any]]
    ) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(
            self: Any, interaction: discord.Interaction, *args: Any, **kwargs: Any
        ) -> Any:
            import time

            start_time = time.time()

            # Garantir que o sistema está inicializado
            if not perm_system._initialized:
                await perm_system.initialize()

            command_name = interaction.command.name if interaction.command else "unknown"

            # Verificar permissão
            has_perm, message = await perm_system.has_permission(
                interaction, command_name, category=category, require_admin=admin, require_mod=mod
            )

            if not has_perm:
                embed = discord.Embed(
                    title="🚫 Acesso Negado", description=f"**Motivo:** {message}", color=0xFF0000
                )
                embed.add_field(
                    name="💡 Como resolver?",
                    value=(
                        "• Peça a um administrador para configurar os cargos necessários\n"
                        "• Verifique se você possui as permissões adequadas\n"
                        "• Administradores podem usar a dashboard para gerenciar permissões"
                    ),
                    inline=False,
                )
                embed.set_footer(text=f"Comando: /{command_name}")

                await interaction.response.send_message(embed=embed, ephemeral=True)

                # Log de falha
                execution_time = time.time() - start_time
                await perm_system.log_command(
                    str(interaction.guild.id),
                    str(interaction.user.id),
                    command_name,
                    category or "unknown",
                    False,
                    execution_time,
                )
                return None

            # Executar comando
            try:
                result = await func(self, interaction, *args, **kwargs)

                # Log de sucesso
                execution_time = time.time() - start_time
                await perm_system.log_command(
                    str(interaction.guild.id),
                    str(interaction.user.id),
                    command_name,
                    category or "unknown",
                    True,
                    execution_time,
                )

                return result

            except Exception:
                # Log de erro
                execution_time = time.time() - start_time
                await perm_system.log_command(
                    str(interaction.guild.id),
                    str(interaction.user.id),
                    command_name,
                    category or "unknown",
                    False,
                    execution_time,
                )
                raise

        return wrapper

    return decorator
