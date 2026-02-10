"""
Log Role Update - Registra alterações de cargos
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class LogRoleUpdate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        await self.log_role_action(role, "Cargo Criado", 0x00FF00, "➕")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        await self.log_role_action(role, "Cargo Deletado", 0xFF0000, "🗑️")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if (
            before.name == after.name
            and before.permissions == after.permissions
            and before.color == after.color
        ):
            return

        await self.log_role_update_detailed(before, after)

    async def log_role_action(self, role, title, color, emoji):
        try:
            log_channel = await self.get_log_channel(role.guild.id)
            if not log_channel:
                return

            embed = discord.Embed(
                title=f"{emoji} {title}", color=color, timestamp=discord.utils.utcnow()
            )

            embed.add_field(name="🏷️ Cargo", value=f"`{role.name}`", inline=True)
            embed.add_field(name="🎨 Cor", value=f"`{role.color!s}`", inline=True)
            embed.add_field(name="📍 Posição", value=f"`{role.position}`", inline=True)
            embed.add_field(name="👥 Membros", value=f"`{len(role.members)}`", inline=True)
            embed.set_footer(text=f"ID: {role.id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro log cargo: {e}")

    async def log_role_update_detailed(self, before, after):
        try:
            log_channel = await self.get_log_channel(before.guild.id)
            if not log_channel:
                return

            embed = discord.Embed(
                title="✏️ Cargo Atualizado", color=0x0099FF, timestamp=discord.utils.utcnow()
            )

            embed.add_field(name="🏷️ Cargo", value=f"{after.mention}\\n`{after.name}`", inline=True)

            # Verificar mudanças
            if before.name != after.name:
                embed.add_field(
                    name="📝 Nome", value=f"`{before.name}` → `{after.name}`", inline=False
                )

            if before.color != after.color:
                embed.add_field(
                    name="🎨 Cor", value=f"`{before.color}` → `{after.color}`", inline=False
                )

            if before.position != after.position:
                embed.add_field(
                    name="📍 Posição",
                    value=f"`{before.position}` → `{after.position}`",
                    inline=False,
                )

            if before.permissions != after.permissions:
                # Analisar permissões alteradas
                added_perms = []
                removed_perms = []

                for perm, value in after.permissions:
                    if value and not getattr(before.permissions, perm):
                        added_perms.append(perm.replace("_", " ").title())
                    elif not value and getattr(before.permissions, perm):
                        removed_perms.append(perm.replace("_", " ").title())

                if added_perms:
                    embed.add_field(
                        name="✅ Permissões Adicionadas",
                        value="\\n".join(added_perms[:10]),
                        inline=False,
                    )
                if removed_perms:
                    embed.add_field(
                        name="❌ Permissões Removidas",
                        value="\\n".join(removed_perms[:10]),
                        inline=False,
                    )

            embed.set_footer(text=f"ID: {after.id}")
            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro log cargo atualizado: {e}")

    async def get_log_channel(self, guild_id):
        result = await database.fetchone(
            "SELECT log_channel_id FROM guild_settings WHERE guild_id = ?", (str(guild_id),)
        )
        if result and result.get("log_channel_id"):
            return self.bot.get_channel(int(result["log_channel_id"]))
        return None


async def setup(bot):
    await bot.add_cog(LogRoleUpdate(bot))
