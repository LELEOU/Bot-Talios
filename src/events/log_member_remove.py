"""
Log Member Remove - Registra saída de membros
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class LogMemberRemove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            log_channel = await self.get_log_channel(member.guild.id)
            if not log_channel:
                return

            embed = discord.Embed(
                title="📤 Membro Saiu", color=0xFF9900, timestamp=discord.utils.utcnow()
            )

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="👤 Usuário", value=f"**{member}**\\n`{member.id}`", inline=True)
            embed.add_field(
                name="📅 Entrou em",
                value=f"<t:{int(member.joined_at.timestamp())}:R>"
                if member.joined_at
                else "Desconhecido",
                inline=True,
            )
            embed.add_field(
                name="👥 Total membros", value=f"**{member.guild.member_count:,}**", inline=True
            )

            # Mostrar roles que tinha
            if len(member.roles) > 1:  # Excluir @everyone
                roles = [role.mention for role in member.roles[1:]]
                if len(roles) <= 10:  # Limite para não quebrar embed
                    embed.add_field(name="🏷️ Cargos", value=" ".join(roles), inline=False)

            embed.set_footer(text=f"ID: {member.id}")
            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro log membro saiu: {e}")

    async def get_log_channel(self, guild_id):
        result = await database.fetchone(
            "SELECT log_channel_id FROM guild_settings WHERE guild_id = ?", (str(guild_id),)
        )
        if result and result.get("log_channel_id"):
            return self.bot.get_channel(int(result["log_channel_id"]))
        return None


async def setup(bot):
    await bot.add_cog(LogMemberRemove(bot))
