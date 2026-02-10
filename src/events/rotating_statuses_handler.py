"""
Rotating Status Handler - Gerencia status rotativos do bot
"""

import random
import sys
from pathlib import Path

import discord
from discord.ext import commands, tasks

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class RotatingStatusHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status_list = []
        self.current_index = 0
        self.rotating_status.start()

    def cog_unload(self):
        self.rotating_status.cancel()

    @tasks.loop(minutes=5)  # Trocar status a cada 5 minutos
    async def rotating_status(self):
        """Loop principal para trocar status"""
        try:
            # Buscar configuração
            config = await self.get_status_config()

            if not config or not config.get("enabled"):
                return

            # Carregar lista de status se vazia
            if not self.status_list:
                await self.load_status_list()

            if not self.status_list:
                return

            # Escolher próximo status
            if config.get("random", False):
                status_data = random.choice(self.status_list)
            else:
                status_data = self.status_list[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.status_list)

            # Aplicar status
            await self.set_bot_status(status_data)

        except Exception as e:
            print(f"❌ Erro no status rotativo: {e}")

    @rotating_status.before_loop
    async def before_rotating_status(self):
        """Aguardar bot ficar online"""
        await self.bot.wait_until_ready()

    async def get_status_config(self) -> dict:
        """Buscar configuração de status rotativo"""
        try:
            result = await database.fetchone(
                "SELECT * FROM rotating_status_config WHERE enabled = 1"
            )

            if result:
                return {
                    "enabled": bool(result.get("enabled", 0)),
                    "interval": result.get("interval", 300),  # 5 minutos
                    "random": bool(result.get("random", 0)),
                }

            return {"enabled": False}

        except Exception as e:
            print(f"❌ Erro buscando config de status: {e}")
            return {"enabled": False}

    async def load_status_list(self):
        """Carregar lista de status do banco"""
        try:
            results = await database.fetchall(
                "SELECT * FROM status_list WHERE enabled = 1 ORDER BY order_index"
            )

            self.status_list = []
            for row in results:
                self.status_list.append(
                    {
                        "type": row.get("type", "playing"),
                        "text": row.get("text", ""),
                        "url": row.get("url", None),  # Para streaming
                    }
                )

            if not self.status_list:
                # Status padrão
                self.status_list = [
                    {"type": "playing", "text": "Gerenciando o servidor"},
                    {"type": "watching", "text": "{guild_count} servidores"},
                    {"type": "listening", "text": "{user_count} usuários"},
                ]

        except Exception as e:
            print(f"❌ Erro carregando lista de status: {e}")
            # Status de fallback
            self.status_list = [{"type": "playing", "text": "Discord Bot"}]

    async def set_bot_status(self, status_data: dict):
        """Definir status do bot"""
        try:
            # Formatar texto com variáveis
            text = await self.format_status_text(status_data["text"])

            # Determinar tipo de atividade
            activity_type = {
                "playing": discord.ActivityType.playing,
                "watching": discord.ActivityType.watching,
                "listening": discord.ActivityType.listening,
                "streaming": discord.ActivityType.streaming,
                "competing": discord.ActivityType.competing,
            }.get(status_data.get("type", "playing"), discord.ActivityType.playing)

            # Criar atividade
            if status_data.get("type") == "streaming" and status_data.get("url"):
                activity = discord.Streaming(name=text, url=status_data["url"])
            else:
                activity = discord.Activity(type=activity_type, name=text)

            # Definir status
            await self.bot.change_presence(activity=activity, status=discord.Status.online)

            print(f"🔄 Status alterado: {status_data['type']} {text}")

        except Exception as e:
            print(f"❌ Erro definindo status: {e}")

    async def format_status_text(self, text: str) -> str:
        """Formatar texto do status com variáveis"""
        try:
            # Contar servidores e usuários
            guild_count = len(self.bot.guilds)
            user_count = sum(guild.member_count for guild in self.bot.guilds)

            # Substituir variáveis
            replacements = {
                "{guild_count}": str(guild_count),
                "{server_count}": str(guild_count),
                "{user_count}": str(user_count),
                "{member_count}": str(user_count),
                "{bot_name}": self.bot.user.name,
                "{ping}": f"{round(self.bot.latency * 1000)}ms",
            }

            formatted_text = text
            for placeholder, value in replacements.items():
                formatted_text = formatted_text.replace(placeholder, value)

            return formatted_text

        except Exception as e:
            print(f"❌ Erro formatando texto de status: {e}")
            return text

    async def add_status(self, status_type: str, text: str, url: str = None) -> bool:
        """Adicionar novo status à lista"""
        try:
            # Determinar próximo índice
            max_order = await database.fetchone(
                "SELECT MAX(order_index) as max_order FROM status_list"
            )
            next_order = (max_order["max_order"] or 0) + 1 if max_order else 1

            await database.run(
                """INSERT INTO status_list (type, text, url, order_index, enabled) 
                   VALUES (?, ?, ?, ?, ?)""",
                (status_type, text, url, next_order, 1),
            )

            # Recarregar lista
            await self.load_status_list()

            return True

        except Exception as e:
            print(f"❌ Erro adicionando status: {e}")
            return False

    async def remove_status(self, status_id: int) -> bool:
        """Remover status da lista"""
        try:
            await database.run("DELETE FROM status_list WHERE id = ?", (status_id,))

            # Recarregar lista
            await self.load_status_list()

            return True

        except Exception as e:
            print(f"❌ Erro removendo status: {e}")
            return False

    async def toggle_rotating_status(self, enabled: bool) -> bool:
        """Ativar/desativar status rotativo"""
        try:
            # Atualizar configuração
            await database.run(
                "INSERT OR REPLACE INTO rotating_status_config (id, enabled, interval, random) VALUES (1, ?, ?, ?)",
                (1 if enabled else 0, 300, 0),
            )

            if enabled:
                if not self.rotating_status.is_running():
                    self.rotating_status.start()
            else:
                if self.rotating_status.is_running():
                    self.rotating_status.cancel()

                # Voltar ao status padrão
                await self.bot.change_presence(
                    activity=discord.Game(name="Discord Bot"), status=discord.Status.online
                )

            return True

        except Exception as e:
            print(f"❌ Erro alternando status rotativo: {e}")
            return False


async def setup(bot):
    await bot.add_cog(RotatingStatusHandler(bot))
