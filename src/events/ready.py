"""
Event handler para quando o bot fica pronto - VERSÃO COMPLETA
"""

import asyncio
import sys
from pathlib import Path

import discord
from discord.ext import commands

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import database


class Ready(commands.Cog):
    """Event handler para bot ready"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Executado quando o bot fica pronto"""
        try:
            # Inicializar cooldowns se não existir
            if not hasattr(self.bot, "cooldowns"):
                self.bot.cooldowns = {}

            print(f"🤖 Bot logado como {self.bot.user}!")
            print(f"📊 Servindo {len(self.bot.guilds)} servidores")
            print(f"👥 Atendendo {len(self.bot.users)} usuários")

            # Definir status do bot
            activity = discord.Activity(
                type=discord.ActivityType.watching, name="Moderando servidores"
            )
            await self.bot.change_presence(activity=activity)

            # Inicializar banco de dados
            await self._initialize_database()

            # Sincronizar comandos slash
            await self._sync_commands()

            # Carregar dados persistentes
            await self._load_persistent_data()

            print("✅ Bot totalmente inicializado!")

        except Exception as e:
            print(f"❌ Erro na inicialização: {e}")

    async def _initialize_database(self):
        """Inicializar todas as tabelas do banco de dados"""
        try:
            await database.connect()
            await database.create_tables()
            print("✅ Sistema de banco de dados inicializado")
        except Exception as e:
            print(f"❌ Erro inicializando database: {e}")

    async def _sync_commands(self):
        """Sincronizar comandos slash"""
        try:
            # Em desenvolvimento, sincronizar globalmente
            # Em produção, sincronizar por guild para ser mais rápido
            if hasattr(self.bot, "testing_guild_id"):
                guild = discord.Object(id=self.bot.testing_guild_id)
                self.bot.tree.copy_global_to(guild=guild)
                await self.bot.tree.sync(guild=guild)
                print("✅ Comandos sincronizados no servidor de teste")
            else:
                await self.bot.tree.sync()
                print("✅ Comandos slash sincronizados globalmente!")

        except Exception as e:
            print(f"❌ Erro sincronizando comandos: {e}")

    async def _load_persistent_data(self):
        """Carregar dados persistentes como sticky messages, etc"""
        try:
            # Carregar sticky messages ativas
            sticky_messages = await database.get_all_sticky_messages()
            if not hasattr(self.bot, "sticky_messages"):
                self.bot.sticky_messages = {}

            for sticky in sticky_messages:
                if sticky["is_active"]:
                    self.bot.sticky_messages[sticky["channel_id"]] = sticky

            # Carregar giveaways ativos
            active_giveaways = await database.get_active_giveaways()
            if not hasattr(self.bot, "active_giveaways"):
                self.bot.active_giveaways = {}

            for giveaway in active_giveaways:
                self.bot.active_giveaways[giveaway["message_id"]] = giveaway

            print("✅ Dados persistentes carregados")
            print(f"  - {len(self.bot.sticky_messages)} sticky messages ativas")
            print(f"  - {len(self.bot.active_giveaways)} giveaways ativos")

        except Exception as e:
            print(f"❌ Erro carregando dados persistentes: {e}")


async def setup(bot):
    """Setup function para carregar o cog"""
    await bot.add_cog(Ready(bot))


import json
import os
import sqlite3
from pathlib import Path

from discord.ext import commands


class ReadyEvent(commands.Cog):
    """Evento de inicialização do bot"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def setup_database(self):
        """Configurar todas as tabelas do banco de dados"""
        try:
            conn = sqlite3.connect("data/bot.db")
            cursor = conn.cursor()

            # Tabela de giveaways
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS giveaways (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    message_id INTEGER UNIQUE,
                    host_id INTEGER,
                    title TEXT,
                    description TEXT,
                    winners_count INTEGER DEFAULT 1,
                    end_time TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de tickets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    user_id INTEGER,
                    category TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP
                )
            """)

            # Tabela de leveling
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_levels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    user_id INTEGER,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 0,
                    messages INTEGER DEFAULT 0,
                    last_xp_time TIMESTAMP,
                    UNIQUE(guild_id, user_id)
                )
            """)

            # Tabela de avisos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    user_id INTEGER,
                    moderator_id INTEGER,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de casos de moderação
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mod_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    case_id INTEGER,
                    user_id INTEGER,
                    moderator_id INTEGER,
                    type TEXT,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de sugestões
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    message_id INTEGER,
                    user_id INTEGER,
                    title TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    upvotes INTEGER DEFAULT 0,
                    downvotes INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de sticky messages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sticky_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    content TEXT,
                    embed_data TEXT,
                    last_message_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, channel_id)
                )
            """)

            # Tabela de configurações de servidor
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER UNIQUE,
                    welcome_channel INTEGER,
                    log_channel INTEGER,
                    autorole_id INTEGER,
                    leveling_enabled BOOLEAN DEFAULT 1,
                    antispam_enabled BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de notas/anotações
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    user_id INTEGER,
                    moderator_id INTEGER,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de backups
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guild_backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    backup_data TEXT,
                    backup_type TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()

            print("✅ Todas as tabelas do banco de dados foram inicializadas")

        except Exception as e:
            print(f"❌ Erro configurando banco de dados: {e}")

    def load_sticky_messages(self):
        """Carregar mensagens sticky do arquivo JSON (compatibilidade)"""
        try:
            sticky_file = Path("data/sticky.json")
            if sticky_file.exists():
                with open(sticky_file, encoding="utf-8") as f:
                    sticky_data = json.load(f)

                # Migrar para banco de dados se necessário
                conn = sqlite3.connect("data/bot.db")
                cursor = conn.cursor()

                for channel_id, data in sticky_data.items():
                    try:
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO sticky_messages 
                            (guild_id, channel_id, content, embed_data, last_message_id)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (
                                data.get("guild_id", 0),
                                int(channel_id),
                                data.get("content", ""),
                                json.dumps(data.get("embed", {})) if data.get("embed") else None,
                                data.get("last_message_id", 0),
                            ),
                        )
                    except Exception as e:
                        print(f"Erro migrando sticky message {channel_id}: {e}")

                conn.commit()
                conn.close()

                print(f"✅ {len(sticky_data)} mensagens sticky carregadas e migradas")
            else:
                print("📝 Nenhum arquivo sticky.json encontrado")

        except Exception as e:
            print(f"❌ Erro carregando sticky messages: {e}")

    async def setup_monitoring_tasks(self):
        """Configurar tarefas de monitoramento"""

        async def check_expired_giveaways():
            """Verificar giveaways expirados"""
            while not self.bot.is_closed():
                try:
                    conn = sqlite3.connect("data/bot.db")
                    cursor = conn.cursor()

                    # Buscar giveaways expirados
                    cursor.execute("""
                        SELECT * FROM giveaways 
                        WHERE status = 'active' AND end_time <= datetime('now')
                    """)

                    expired_giveaways = cursor.fetchall()

                    for giveaway in expired_giveaways:
                        try:
                            # Marcar como finalizado
                            cursor.execute(
                                """
                                UPDATE giveaways SET status = 'ended' WHERE id = ?
                            """,
                                (giveaway[0],),
                            )

                            print(f"🎉 Giveaway expirado finalizado: ID {giveaway[0]}")
                        except Exception as e:
                            print(f"❌ Erro finalizando giveaway {giveaway[0]}: {e}")

                    conn.commit()
                    conn.close()

                except Exception as e:
                    print(f"❌ Erro verificando giveaways expirados: {e}")

                await asyncio.sleep(60)  # Verificar a cada minuto

        async def check_expired_suggestions():
            """Verificar sugestões expiradas"""
            while not self.bot.is_closed():
                try:
                    conn = sqlite3.connect("data/bot.db")
                    cursor = conn.cursor()

                    # Buscar sugestões antigas (exemplo: 30 dias)
                    cursor.execute("""
                        SELECT * FROM suggestions 
                        WHERE status = 'pending' 
                        AND created_at <= datetime('now', '-30 days')
                    """)

                    old_suggestions = cursor.fetchall()

                    for suggestion in old_suggestions:
                        try:
                            # Marcar como expirada
                            cursor.execute(
                                """
                                UPDATE suggestions SET status = 'expired' WHERE id = ?
                            """,
                                (suggestion[0],),
                            )

                            print(f"💡 Sugestão expirada: ID {suggestion[0]}")
                        except Exception as e:
                            print(f"❌ Erro processando sugestão {suggestion[0]}: {e}")

                    conn.commit()
                    conn.close()

                except Exception as e:
                    print(f"❌ Erro verificando sugestões expiradas: {e}")

                await asyncio.sleep(3600)  # Verificar a cada hora

        # Iniciar tarefas em background (não criar tasks aqui, será chamado no on_ready)
        # self.bot.loop.create_task(check_expired_giveaways())
        # self.bot.loop.create_task(check_expired_suggestions())

        # Retornar as funções para serem iniciadas depois
        return check_expired_giveaways, check_expired_suggestions

        print("✅ Sistema de monitoramento iniciado (giveaways + sugestões)")

    @commands.Cog.listener()
    async def on_ready(self):
        """Evento quando o bot fica online"""

        print(f"🤖 Bot logado como {self.bot.user}!")
        print(f"📊 Servindo {len(self.bot.guilds)} servidores")
        print(f"👥 Atendendo {len(self.bot.users)} usuários")

        # Definir status do bot
        activity = discord.Activity(type=discord.ActivityType.watching, name="Moderando servidores")
        await self.bot.change_presence(activity=activity, status=discord.Status.online)

        # Configurar banco de dados
        self.setup_database()

        # Carregar mensagens sticky
        self.load_sticky_messages()

        # Sincronizar comandos slash (apenas em desenvolvimento)
        if os.getenv("NODE_ENV") == "development" or True:  # Por enquanto sempre sincronizar
            try:
                synced = await self.bot.tree.sync()
                print(f"✅ {len(synced)} comandos slash sincronizados!")
            except Exception as e:
                print(f"❌ Erro sincronizando comandos: {e}")

        # Inicializar monitoramento
        await self.setup_monitoring_tasks()

        # Verificar saúde do sistema
        await self.system_health_check()

        print("🚀 Bot totalmente inicializado e pronto para uso!")

    async def system_health_check(self):
        """Verificação de saúde do sistema"""
        try:
            # Verificar conexão com banco
            conn = sqlite3.connect("data/bot.db")
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table"')
            table_count = cursor.fetchone()[0]
            conn.close()

            print(f"💾 Banco de dados: {table_count} tabelas ativas")

            # Verificar permissões necessárias em servidores
            missing_perms = []
            for guild in self.bot.guilds:
                me = guild.me
                required_perms = [
                    "send_messages",
                    "embed_links",
                    "read_message_history",
                    "manage_messages",
                    "add_reactions",
                    "use_external_emojis",
                ]

                for perm in required_perms:
                    if not getattr(me.guild_permissions, perm, False):
                        missing_perms.append(f"{guild.name}: {perm}")

            if missing_perms:
                print(f"⚠️ Permissões em falta: {len(missing_perms)} issues")
            else:
                print("✅ Todas as permissões necessárias estão OK")

            # Status de cogs
            loaded_cogs = len(self.bot.cogs)
            print(f"🧩 Cogs carregados: {loaded_cogs}")

            print("💚 Verificação de saúde do sistema concluída!")

        except Exception as e:
            print(f"❌ Erro na verificação de saúde: {e}")


async def setup(bot: commands.Bot):
    """Configurar o evento"""
    await bot.add_cog(ReadyEvent(bot))
