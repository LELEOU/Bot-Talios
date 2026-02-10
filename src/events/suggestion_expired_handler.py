"""
Suggestion Expired Handler - Gerencia expiração de sugestões
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands, tasks

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class SuggestionExpiredHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_expired_suggestions.start()

    def cog_unload(self):
        self.check_expired_suggestions.cancel()

    @tasks.loop(hours=1)  # Verificar a cada hora
    async def check_expired_suggestions(self):
        """Verificar sugestões expiradas"""
        try:
            # Buscar sugestões que expiraram
            current_time = discord.utils.utcnow().isoformat()

            expired_suggestions = await database.fetchall(
                "SELECT * FROM suggestions WHERE expires_at <= ? AND status = 'pending'",
                (current_time,),
            )

            for suggestion in expired_suggestions:
                await self.handle_expired_suggestion(suggestion)

        except Exception as e:
            print(f"❌ Erro verificando sugestões expiradas: {e}")

    @check_expired_suggestions.before_loop
    async def before_check_expired_suggestions(self):
        await self.bot.wait_until_ready()

    async def handle_expired_suggestion(self, suggestion):
        """Tratar sugestão expirada"""
        try:
            # Atualizar status para expirada
            await database.run(
                "UPDATE suggestions SET status = 'expired', reviewed_at = ? WHERE id = ?",
                (discord.utils.utcnow().isoformat(), suggestion["id"]),
            )

            # Buscar mensagem e atualizar
            guild = self.bot.get_guild(int(suggestion["guild_id"]))
            if not guild:
                return

            channel = guild.get_channel(int(suggestion["channel_id"]))
            if not channel:
                return

            try:
                message = await channel.fetch_message(int(suggestion["message_id"]))

                # Atualizar embed
                embed = message.embeds[0] if message.embeds else discord.Embed()
                embed.color = 0x666666  # Cinza
                embed.add_field(
                    name="⏰ Status", value="**EXPIRADA**\\nTempo de votação esgotado", inline=False
                )

                await message.edit(embed=embed)

            except discord.NotFound:
                pass  # Mensagem foi deletada

        except Exception as e:
            print(f"❌ Erro tratando sugestão expirada: {e}")


async def setup(bot):
    await bot.add_cog(SuggestionExpiredHandler(bot))
