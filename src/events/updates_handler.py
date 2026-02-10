"""
Updates Handler - Gerencia atualizações do bot
"""

import os
import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class UpdatesHandler(commands.Cog):
    """Handler para sistema de atualizações"""

    def __init__(self, bot):
        self.bot = bot
        self.current_version = os.environ.get("BOT_VERSION", "1.0.0")

    @commands.Cog.listener()
    async def on_ready(self):
        """Verificar atualizações quando bot inicia"""
        await self.check_version_update()

    async def check_version_update(self):
        """Verificar se houve atualização de versão"""
        try:
            # Buscar última versão registrada
            last_version = await database.fetchone(
                "SELECT version FROM bot_version ORDER BY updated_at DESC LIMIT 1"
            )

            if not last_version or last_version["version"] != self.current_version:
                await self.handle_version_update(
                    last_version["version"] if last_version else "0.0.0", self.current_version
                )

        except Exception as e:
            print(f"❌ Erro verificando atualização: {e}")

    async def handle_version_update(self, old_version: str, new_version: str):
        """Tratar atualização de versão"""
        try:
            # Registrar nova versão
            await database.run(
                "INSERT INTO bot_version (version, updated_at, changelog) VALUES (?, ?, ?)",
                (new_version, discord.utils.utcnow().isoformat(), self.get_changelog(new_version)),
            )

            # Executar migrações se necessário
            await self.run_version_migrations(old_version, new_version)

            # Notificar administradores sobre atualização
            await self.notify_update(old_version, new_version)

            print(f"🔄 Bot atualizado de v{old_version} para v{new_version}")

        except Exception as e:
            print(f"❌ Erro tratando atualização: {e}")

    def get_changelog(self, version: str) -> str:
        """Buscar changelog da versão"""
        try:
            # Tentar ler changelog de arquivo
            changelog_file = Path(__file__).parent.parent.parent / f"CHANGELOG_{version}.md"

            if changelog_file.exists():
                return changelog_file.read_text(encoding="utf-8")

            # Changelog padrão baseado na versão
            changelogs = {
                "1.0.0": "• Primeira versão estável\\n• Sistema básico de comandos\\n• Sistema de moderação",
                "1.1.0": "• Sistema de tickets\\n• Sistema de sugestões\\n• Melhorias de performance",
                "1.2.0": "• Sistema de leveling\\n• Auto-moderação\\n• Sistema de logs avançado",
                "2.0.0": "• Migração para Python\\n• Nova arquitetura\\n• Interface aprimorada",
            }

            return changelogs.get(version, f"• Atualização para versão {version}")

        except Exception as e:
            print(f"❌ Erro buscando changelog: {e}")
            return f"• Atualização para versão {version}"

    async def run_version_migrations(self, old_version: str, new_version: str):
        """Executar migrações necessárias"""
        try:
            # Definir migrações por versão
            migrations = {
                "1.1.0": self.migrate_to_v1_1_0,
                "1.2.0": self.migrate_to_v1_2_0,
                "2.0.0": self.migrate_to_v2_0_0,
            }

            # Executar migrações necessárias
            for version, migration_func in migrations.items():
                if self.version_greater_than(version, old_version) and self.version_less_equal(
                    version, new_version
                ):
                    print(f"🔧 Executando migração para v{version}")
                    await migration_func()

        except Exception as e:
            print(f"❌ Erro executando migrações: {e}")

    async def migrate_to_v1_1_0(self):
        """Migração para versão 1.1.0"""
        try:
            # Criar tabelas de tickets se não existirem
            await database.run("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY,
                    guild_id TEXT,
                    channel_id TEXT,
                    creator_id TEXT,
                    status TEXT,
                    created_at TEXT,
                    closed_at TEXT
                )
            """)

            # Criar tabelas de sugestões
            await database.run("""
                CREATE TABLE IF NOT EXISTS suggestions (
                    id INTEGER PRIMARY KEY,
                    guild_id TEXT,
                    channel_id TEXT,
                    message_id TEXT,
                    author_id TEXT,
                    content TEXT,
                    status TEXT,
                    upvotes INTEGER DEFAULT 0,
                    downvotes INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)

        except Exception as e:
            print(f"❌ Erro migração v1.1.0: {e}")

    async def migrate_to_v1_2_0(self):
        """Migração para versão 1.2.0"""
        try:
            # Criar tabelas de leveling
            await database.run("""
                CREATE TABLE IF NOT EXISTS user_levels (
                    id INTEGER PRIMARY KEY,
                    guild_id TEXT,
                    user_id TEXT,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    total_xp INTEGER DEFAULT 0,
                    last_message TEXT
                )
            """)

            # Criar tabelas de auto-moderação
            await database.run("""
                CREATE TABLE IF NOT EXISTS antispam_config (
                    id INTEGER PRIMARY KEY,
                    guild_id TEXT,
                    enabled INTEGER DEFAULT 1,
                    limite INTEGER DEFAULT 5,
                    intervalo INTEGER DEFAULT 10
                )
            """)

        except Exception as e:
            print(f"❌ Erro migração v1.2.0: {e}")

    async def migrate_to_v2_0_0(self):
        """Migração para versão 2.0.0 (Python)"""
        try:
            # Migrar dados do formato JavaScript para Python
            # Atualizar estruturas de banco se necessário

            # Adicionar campos novos se não existirem
            try:
                await database.run(
                    "ALTER TABLE guild_settings ADD COLUMN python_version TEXT DEFAULT '2.0.0'"
                )
            except:
                pass  # Campo já existe

            # Limpar dados incompatíveis
            await database.run(
                "DELETE FROM temp_sessions WHERE created_at < ?",
                (discord.utils.utcnow().isoformat(),),
            )

        except Exception as e:
            print(f"❌ Erro migração v2.0.0: {e}")

    def version_greater_than(self, version1: str, version2: str) -> bool:
        """Verificar se version1 > version2"""
        try:
            v1_parts = [int(x) for x in version1.split(".")]
            v2_parts = [int(x) for x in version2.split(".")]

            # Normalizar tamanhos
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))

            for i in range(max_len):
                if v1_parts[i] > v2_parts[i]:
                    return True
                if v1_parts[i] < v2_parts[i]:
                    return False

            return False

        except Exception:
            return False

    def version_less_equal(self, version1: str, version2: str) -> bool:
        """Verificar se version1 <= version2"""
        return not self.version_greater_than(version1, version2)

    async def notify_update(self, old_version: str, new_version: str):
        """Notificar sobre atualização"""
        try:
            # Buscar canais de notificação configurados
            notification_channels = await database.fetchall(
                "SELECT guild_id, update_channel_id FROM guild_settings WHERE update_channel_id IS NOT NULL"
            )

            changelog = self.get_changelog(new_version)

            embed = discord.Embed(
                title="🔄 Bot Atualizado!",
                description=f"O bot foi atualizado da versão **{old_version}** para **{new_version}**",
                color=0x00FF00,
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(name="📋 Novidades", value=changelog, inline=False)

            embed.add_field(name="🔧 Versão Anterior", value=f"v{old_version}", inline=True)

            embed.add_field(name="✨ Nova Versão", value=f"v{new_version}", inline=True)

            embed.set_footer(
                text="Obrigado por usar nosso bot!", icon_url=self.bot.user.display_avatar.url
            )

            # Enviar para todos os canais configurados
            for channel_data in notification_channels:
                try:
                    guild = self.bot.get_guild(int(channel_data["guild_id"]))
                    if not guild:
                        continue

                    channel = guild.get_channel(int(channel_data["update_channel_id"]))
                    if not channel:
                        continue

                    await channel.send(embed=embed)

                except Exception as e:
                    print(f"❌ Erro enviando notificação para {channel_data['guild_id']}: {e}")

        except Exception as e:
            print(f"❌ Erro notificando atualização: {e}")

    async def get_update_info(self) -> dict:
        """Buscar informações de atualização"""
        try:
            # Buscar histórico de versões
            versions = await database.fetchall(
                "SELECT * FROM bot_version ORDER BY updated_at DESC LIMIT 10"
            )

            return {
                "current_version": self.current_version,
                "version_history": [dict(v) for v in versions] if versions else [],
                "last_update": versions[0]["updated_at"] if versions else None,
            }

        except Exception as e:
            print(f"❌ Erro buscando info de atualização: {e}")
            return {
                "current_version": self.current_version,
                "version_history": [],
                "last_update": None,
            }


async def setup(bot):
    await bot.add_cog(UpdatesHandler(bot))
