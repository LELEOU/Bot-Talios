"""
Custom Variable Change Handler - Mudanças de variáveis customizadas
Gerencia alterações em variáveis personalizadas do servidor
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import database


class CustomVariableChangeHandler(commands.Cog):
    """Handler para mudanças de variáveis customizadas"""

    def __init__(self, bot):
        self.bot = bot
        self.variable_cache = {}

    async def on_variable_change(
        self, guild_id: int, variable_name: str, old_value: str, new_value: str, changed_by: int
    ):
        """Executado quando uma variável customizada muda"""
        try:
            # Atualizar cache
            if guild_id not in self.variable_cache:
                self.variable_cache[guild_id] = {}

            self.variable_cache[guild_id][variable_name] = new_value

            # Salvar no banco de dados
            await self.save_variable_change(
                guild_id, variable_name, old_value, new_value, changed_by
            )

            # Notificar outros sistemas se necessário
            await self.notify_variable_change(
                guild_id, variable_name, old_value, new_value, changed_by
            )

            print(f"🔄 Variável alterada em {guild_id}: {variable_name} = {new_value}")

        except Exception as e:
            print(f"❌ Erro processando mudança de variável: {e}")

    async def save_variable_change(
        self, guild_id: int, variable_name: str, old_value: str, new_value: str, changed_by: int
    ):
        """Salvar mudança de variável no banco"""
        try:
            # Atualizar ou inserir variável
            await database.run(
                """INSERT OR REPLACE INTO custom_variables 
                   (guild_id, variable_name, variable_value, changed_by, changed_at) 
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    str(guild_id),
                    variable_name,
                    new_value,
                    str(changed_by),
                    discord.utils.utcnow().isoformat(),
                ),
            )

            # Log da mudança
            await database.run(
                """INSERT INTO variable_changes 
                   (guild_id, variable_name, old_value, new_value, changed_by, changed_at) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    str(guild_id),
                    variable_name,
                    old_value,
                    new_value,
                    str(changed_by),
                    discord.utils.utcnow().isoformat(),
                ),
            )

        except Exception as e:
            print(f"❌ Erro salvando mudança de variável: {e}")

    async def notify_variable_change(
        self, guild_id: int, variable_name: str, old_value: str, new_value: str, changed_by: int
    ):
        """Notificar outros sistemas sobre mudança de variável"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return

            # Buscar configurações de notificação
            config = await database.fetchone(
                "SELECT log_channel_id FROM guild_settings WHERE guild_id = ?", (str(guild_id),)
            )

            if not config or not config.get("log_channel_id"):
                return

            log_channel = guild.get_channel(int(config["log_channel_id"]))
            if not log_channel:
                return

            # Criar embed de log
            embed = discord.Embed(
                title="🔄 Variável Customizada Alterada",
                color=0x0099FF,
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(name="📝 Variável", value=f"`{variable_name}`", inline=True)

            embed.add_field(name="👤 Alterado por", value=f"<@{changed_by}>", inline=True)

            embed.add_field(
                name="⏰ Quando",
                value=f"<t:{int(discord.utils.utcnow().timestamp())}:R>",
                inline=True,
            )

            if len(old_value) <= 1000:
                embed.add_field(
                    name="📋 Valor anterior",
                    value=f"```{old_value}```" if old_value else "`(vazio)`",
                    inline=False,
                )

            if len(new_value) <= 1000:
                embed.add_field(
                    name="📝 Novo valor",
                    value=f"```{new_value}```" if new_value else "`(vazio)`",
                    inline=False,
                )

            embed.set_footer(text=f"Guild ID: {guild_id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro notificando mudança de variável: {e}")

    async def get_variable(self, guild_id: int, variable_name: str) -> str:
        """Buscar valor de variável customizada"""
        try:
            # Verificar cache primeiro
            if guild_id in self.variable_cache and variable_name in self.variable_cache[guild_id]:
                return self.variable_cache[guild_id][variable_name]

            # Buscar no banco
            result = await database.fetchone(
                "SELECT variable_value FROM custom_variables WHERE guild_id = ? AND variable_name = ?",
                (str(guild_id), variable_name),
            )

            if result:
                value = result["variable_value"]
                # Atualizar cache
                if guild_id not in self.variable_cache:
                    self.variable_cache[guild_id] = {}
                self.variable_cache[guild_id][variable_name] = value
                return value

            return None

        except Exception as e:
            print(f"❌ Erro buscando variável: {e}")
            return None

    async def set_variable(
        self, guild_id: int, variable_name: str, new_value: str, changed_by: int
    ):
        """Definir valor de variável customizada"""
        try:
            # Buscar valor atual
            old_value = await self.get_variable(guild_id, variable_name) or ""

            # Executar mudança
            await self.on_variable_change(guild_id, variable_name, old_value, new_value, changed_by)

        except Exception as e:
            print(f"❌ Erro definindo variável: {e}")

    async def delete_variable(self, guild_id: int, variable_name: str, deleted_by: int):
        """Deletar variável customizada"""
        try:
            # Buscar valor atual
            old_value = await self.get_variable(guild_id, variable_name) or ""

            # Remover do banco
            await database.run(
                "DELETE FROM custom_variables WHERE guild_id = ? AND variable_name = ?",
                (str(guild_id), variable_name),
            )

            # Remover do cache
            if guild_id in self.variable_cache and variable_name in self.variable_cache[guild_id]:
                del self.variable_cache[guild_id][variable_name]

            # Log da remoção
            await self.on_variable_change(
                guild_id, variable_name, old_value, "(deleted)", deleted_by
            )

        except Exception as e:
            print(f"❌ Erro deletando variável: {e}")

    async def list_variables(self, guild_id: int) -> dict:
        """Listar todas as variáveis de um servidor"""
        try:
            result = await database.fetchall(
                "SELECT variable_name, variable_value FROM custom_variables WHERE guild_id = ?",
                (str(guild_id),),
            )

            return {row["variable_name"]: row["variable_value"] for row in result} if result else {}

        except Exception as e:
            print(f"❌ Erro listando variáveis: {e}")
            return {}


async def setup(bot):
    """Setup function para carregar o cog"""
    await bot.add_cog(CustomVariableChangeHandler(bot))
