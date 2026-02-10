"""
Log Message Update - Registra edição de mensagens
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class LogMessageUpdate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content:
            return

        try:
            log_channel = await self.get_log_channel(before.guild.id)
            if not log_channel:
                return

            embed = discord.Embed(
                title="✏️ Mensagem Editada", color=0x0099FF, timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="👤 Autor", value=f"{before.author.mention}\\n`{before.author}`", inline=True
            )
            embed.add_field(name="📍 Canal", value=f"{before.channel.mention}", inline=True)
            embed.add_field(
                name="🔗 Link", value=f"[Ir para mensagem]({after.jump_url})", inline=True
            )

            # Conteúdo anterior (limitado)
            old_content = before.content if before.content else "*Sem conteúdo de texto*"
            if len(old_content) > 500:
                old_content = old_content[:500] + "..."
            embed.add_field(name="📝 Antes", value=f"```{old_content}```", inline=False)

            # Novo conteúdo (limitado)
            new_content = after.content if after.content else "*Sem conteúdo de texto*"
            if len(new_content) > 500:
                new_content = new_content[:500] + "..."
            embed.add_field(name="📝 Depois", value=f"```{new_content}```", inline=False)

            embed.set_footer(text=f"ID da mensagem: {after.id}")
            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro log mensagem editada: {e}")

    async def get_log_channel(self, guild_id):
        result = await database.fetchone(
            "SELECT log_channel_id FROM guild_settings WHERE guild_id = ?", (str(guild_id),)
        )
        if result and result.get("log_channel_id"):
            return self.bot.get_channel(int(result["log_channel_id"]))
        return None


async def setup(bot):
    await bot.add_cog(LogMessageUpdate(bot))
