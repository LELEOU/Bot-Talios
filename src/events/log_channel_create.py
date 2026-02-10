"""
Log Channel Create - Registra criação de canais
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class LogChannelCreate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        try:
            log_channel = await self.get_log_channel(channel.guild.id)
            if not log_channel:
                return

            embed = discord.Embed(
                title="📝 Canal Criado", color=0x00FF00, timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="📍 Canal", value=f"{channel.mention}\\n`#{channel.name}`", inline=True
            )
            embed.add_field(name="🏷️ Tipo", value=channel.type.name.title(), inline=True)
            embed.add_field(name="🆔 ID", value=f"`{channel.id}`", inline=True)

            if hasattr(channel, "category") and channel.category:
                embed.add_field(name="📁 Categoria", value=channel.category.name, inline=True)

            embed.set_footer(text=f"Canal ID: {channel.id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro log canal criado: {e}")

    async def get_log_channel(self, guild_id):
        result = await database.fetchone(
            "SELECT log_channel_id FROM guild_settings WHERE guild_id = ?", (str(guild_id),)
        )
        if result and result.get("log_channel_id"):
            return self.bot.get_channel(int(result["log_channel_id"]))
        return None


async def setup(bot):
    await bot.add_cog(LogChannelCreate(bot))
