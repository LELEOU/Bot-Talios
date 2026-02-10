"""
Log Member Add - Registra entrada de membros
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class LogMemberAdd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            log_channel = await self.get_log_channel(member.guild.id)
            if not log_channel:
                return

            embed = discord.Embed(
                title="📥 Membro Entrou", color=0x00FF00, timestamp=discord.utils.utcnow()
            )

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="👤 Usuário", value=f"{member.mention}\\n`{member}`", inline=True)
            embed.add_field(
                name="📅 Conta criada",
                value=f"<t:{int(member.created_at.timestamp())}:R>",
                inline=True,
            )
            embed.add_field(
                name="👥 Total membros", value=f"**{member.guild.member_count:,}**", inline=True
            )
            embed.set_footer(text=f"ID: {member.id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro log membro entrou: {e}")

    async def get_log_channel(self, guild_id):
        result = await database.fetchone(
            "SELECT log_channel_id FROM guild_settings WHERE guild_id = ?", (str(guild_id),)
        )
        if result and result.get("log_channel_id"):
            return self.bot.get_channel(int(result["log_channel_id"]))
        return None


async def setup(bot):
    await bot.add_cog(LogMemberAdd(bot))
