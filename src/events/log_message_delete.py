"""
Log Message Delete - Registra exclusão de mensagens
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class LogMessageDelete(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        try:
            log_channel = await self.get_log_channel(message.guild.id)
            if not log_channel:
                return

            embed = discord.Embed(
                title="🗑️ Mensagem Deletada", color=0xFF0000, timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="👤 Autor", value=f"{message.author.mention}\\n`{message.author}`", inline=True
            )
            embed.add_field(name="📍 Canal", value=f"{message.channel.mention}", inline=True)
            embed.add_field(
                name="🕐 Enviada em",
                value=f"<t:{int(message.created_at.timestamp())}:R>",
                inline=True,
            )

            # Conteúdo da mensagem (limitado)
            content = message.content if message.content else "*Sem conteúdo de texto*"
            if len(content) > 1000:
                content = content[:1000] + "..."

            embed.add_field(name="📝 Conteúdo", value=f"```{content}```", inline=False)

            # Anexos se houver
            if message.attachments:
                attachments = "\\n".join([f"📎 {att.filename}" for att in message.attachments[:5]])
                embed.add_field(name="📎 Anexos", value=attachments, inline=False)

            embed.set_footer(text=f"ID da mensagem: {message.id}")
            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro log mensagem deletada: {e}")

    async def get_log_channel(self, guild_id):
        result = await database.fetchone(
            "SELECT log_channel_id FROM guild_settings WHERE guild_id = ?", (str(guild_id),)
        )
        if result and result.get("log_channel_id"):
            return self.bot.get_channel(int(result["log_channel_id"]))
        return None


async def setup(bot):
    await bot.add_cog(LogMessageDelete(bot))
