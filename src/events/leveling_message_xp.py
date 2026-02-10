"""
Leveling Message XP - Sistema de XP por mensagens
Gerencia ganho de XP e level up através de mensagens
"""

import random
import sys
import time
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class LevelingMessageXP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldowns = {}  # Cache de cooldowns de XP

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        try:
            # Verificar se leveling está habilitado
            leveling_config = await self.get_leveling_config(message.guild.id)
            if not leveling_config.get("enabled", True):
                return

            # Verificar cooldown de XP
            user_key = f"{message.guild.id}_{message.author.id}"
            current_time = time.time()

            if user_key in self.xp_cooldowns:
                if current_time - self.xp_cooldowns[user_key] < leveling_config.get(
                    "xp_cooldown", 60
                ):
                    return

            # Verificar se canal está bloqueado
            if await self.is_channel_blocked(message.guild.id, message.channel.id):
                return

            # Calcular XP ganho
            xp_gained = await self.calculate_xp_gain(message, leveling_config)

            # Aplicar XP
            user_data = await self.add_xp(message.guild.id, message.author.id, xp_gained)

            # Verificar level up
            if user_data:
                await self.check_level_up(message, user_data, leveling_config)

            # Atualizar cooldown
            self.xp_cooldowns[user_key] = current_time

        except Exception as e:
            print(f"❌ Erro no sistema de XP: {e}")

    async def get_leveling_config(self, guild_id: int) -> dict:
        """Buscar configuração de leveling"""
        try:
            result = await database.fetchone(
                "SELECT * FROM leveling_config WHERE guild_id = ?", (str(guild_id),)
            )

            if result:
                return {
                    "enabled": bool(result.get("enabled", 1)),
                    "xp_min": result.get("xp_min", 15),
                    "xp_max": result.get("xp_max", 25),
                    "xp_cooldown": result.get("xp_cooldown", 60),
                    "level_up_channel": result.get("level_up_channel"),
                    "level_up_message": result.get(
                        "level_up_message",
                        "Parabéns {user.mention}! Você subiu para o nível **{level}**! 🎉",
                    ),
                    "level_roles": result.get("level_roles", "{}"),
                }

            # Configuração padrão
            return {
                "enabled": True,
                "xp_min": 15,
                "xp_max": 25,
                "xp_cooldown": 60,
                "level_up_channel": None,
                "level_up_message": "Parabéns {user.mention}! Você subiu para o nível **{level}**! 🎉",
                "level_roles": "{}",
            }

        except Exception as e:
            print(f"❌ Erro buscando config leveling: {e}")
            return {"enabled": False}

    async def is_channel_blocked(self, guild_id: int, channel_id: int) -> bool:
        """Verificar se canal está bloqueado para XP"""
        try:
            result = await database.fetchone(
                "SELECT id FROM leveling_blocked_channels WHERE guild_id = ? AND channel_id = ?",
                (str(guild_id), str(channel_id)),
            )
            return result is not None

        except Exception as e:
            print(f"❌ Erro verificando canal bloqueado: {e}")
            return False

    async def calculate_xp_gain(self, message: discord.Message, config: dict) -> int:
        """Calcular XP ganho baseado na mensagem"""
        base_xp = random.randint(config["xp_min"], config["xp_max"])

        # Bônus por comprimento da mensagem
        if len(message.content) > 50:
            base_xp += random.randint(1, 5)

        # Bônus por anexos/mídia
        if message.attachments:
            base_xp += random.randint(2, 8)

        # Bônus por embeds
        if message.embeds:
            base_xp += random.randint(1, 3)

        return base_xp

    async def add_xp(self, guild_id: int, user_id: int, xp_amount: int) -> dict:
        """Adicionar XP ao usuário"""
        try:
            # Buscar dados atuais do usuário
            user_data = await database.fetchone(
                "SELECT * FROM user_levels WHERE guild_id = ? AND user_id = ?",
                (str(guild_id), str(user_id)),
            )

            if user_data:
                # Usuário existe, atualizar XP
                new_xp = user_data["xp"] + xp_amount
                new_total_xp = user_data["total_xp"] + xp_amount

                await database.run(
                    "UPDATE user_levels SET xp = ?, total_xp = ?, last_message = ? WHERE guild_id = ? AND user_id = ?",
                    (
                        new_xp,
                        new_total_xp,
                        discord.utils.utcnow().isoformat(),
                        str(guild_id),
                        str(user_id),
                    ),
                )

                return {
                    "user_id": user_id,
                    "guild_id": guild_id,
                    "xp": new_xp,
                    "total_xp": new_total_xp,
                    "level": user_data["level"],
                }
            # Novo usuário
            await database.run(
                """INSERT INTO user_levels (guild_id, user_id, xp, total_xp, level, last_message) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    str(guild_id),
                    str(user_id),
                    xp_amount,
                    xp_amount,
                    1,
                    discord.utils.utcnow().isoformat(),
                ),
            )

            return {
                "user_id": user_id,
                "guild_id": guild_id,
                "xp": xp_amount,
                "total_xp": xp_amount,
                "level": 1,
            }

        except Exception as e:
            print(f"❌ Erro adicionando XP: {e}")
            return None

    async def check_level_up(self, message: discord.Message, user_data: dict, config: dict):
        """Verificar e processar level up"""
        try:
            current_level = user_data["level"]
            current_xp = user_data["xp"]

            # Calcular XP necessário para próximo nível
            xp_needed = self.calculate_xp_for_level(current_level + 1)

            if current_xp >= xp_needed:
                # Level up!
                new_level = current_level + 1
                remaining_xp = current_xp - xp_needed

                # Atualizar nível no banco
                await database.run(
                    "UPDATE user_levels SET level = ?, xp = ? WHERE guild_id = ? AND user_id = ?",
                    (new_level, remaining_xp, str(message.guild.id), str(message.author.id)),
                )

                # Enviar mensagem de level up
                await self.send_level_up_message(message, new_level, config)

                # Aplicar role de nível se configurado
                await self.apply_level_role(message.guild, message.author, new_level, config)

                # Verificar se ainda pode subir mais níveis
                updated_user_data = {**user_data, "level": new_level, "xp": remaining_xp}
                await self.check_level_up(message, updated_user_data, config)

        except Exception as e:
            print(f"❌ Erro verificando level up: {e}")

    def calculate_xp_for_level(self, level: int) -> int:
        """Calcular XP necessário para atingir determinado nível"""
        # Fórmula: 100 * level^1.5
        return int(100 * (level**1.5))

    async def send_level_up_message(self, message: discord.Message, new_level: int, config: dict):
        """Enviar mensagem de level up"""
        try:
            # Determinar canal de envio
            channel = message.channel
            if config.get("level_up_channel"):
                level_up_channel = message.guild.get_channel(int(config["level_up_channel"]))
                if level_up_channel:
                    channel = level_up_channel

            # Formatar mensagem
            level_message = config.get(
                "level_up_message",
                "Parabéns {user.mention}! Você subiu para o nível **{level}**! 🎉",
            )
            level_message = level_message.format(
                user=message.author, level=new_level, guild=message.guild
            )

            # Criar embed
            embed = discord.Embed(
                title="🎉 LEVEL UP!",
                description=level_message,
                color=0x00FF00,
                timestamp=discord.utils.utcnow(),
            )

            embed.set_thumbnail(url=message.author.display_avatar.url)

            embed.add_field(name="📊 Novo Nível", value=f"**{new_level}**", inline=True)

            embed.add_field(
                name="🎯 Próximo Nível",
                value=f"**{self.calculate_xp_for_level(new_level + 1):,}** XP",
                inline=True,
            )

            embed.set_footer(text=f"Parabéns, {message.author.display_name}!")

            await channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro enviando mensagem de level up: {e}")

    async def apply_level_role(
        self, guild: discord.Guild, member: discord.Member, level: int, config: dict
    ):
        """Aplicar role de nível"""
        try:
            # Buscar roles de nível configurados
            level_roles_str = config.get("level_roles", "{}")
            try:
                import json

                level_roles = json.loads(level_roles_str) if level_roles_str else {}
            except:
                level_roles = {}

            # Verificar se há role para este nível
            role_id = level_roles.get(str(level))
            if not role_id:
                return

            role = guild.get_role(int(role_id))
            if not role:
                return

            # Verificar se bot tem permissão
            if not guild.me.guild_permissions.manage_roles:
                return

            # Verificar hierarquia
            if role >= guild.me.top_role:
                return

            # Aplicar role
            await member.add_roles(role, reason=f"Level up - Nível {level}")

            # Remover roles de níveis anteriores se configurado
            for level_str, old_role_id in level_roles.items():
                if int(level_str) < level:
                    old_role = guild.get_role(int(old_role_id))
                    if old_role and old_role in member.roles:
                        await member.remove_roles(old_role, reason=f"Level up - Nível {level}")

        except Exception as e:
            print(f"❌ Erro aplicando role de nível: {e}")


async def setup(bot):
    """Setup function para carregar o cog"""
    await bot.add_cog(LevelingMessageXP(bot))
