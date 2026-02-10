"""
Reaction Add Handler - Gerencia adição de reações
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class ReactionAddHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        try:
            # Verificar se é reação em sistema de roles
            await self.handle_reaction_roles(reaction, user, "add")

            # Verificar se é reação em sugestão
            await self.handle_suggestion_reaction(reaction, user, "add")

            # Verificar se é reação em poll
            await self.handle_poll_reaction(reaction, user, "add")

        except Exception as e:
            print(f"❌ Erro processando reação adicionada: {e}")

    async def handle_reaction_roles(self, reaction, user, action):
        """Gerenciar roles por reação"""
        try:
            # Buscar configuração de reaction roles
            config = await database.fetchone(
                "SELECT * FROM reaction_roles WHERE message_id = ? AND emoji = ?",
                (str(reaction.message.id), str(reaction.emoji)),
            )

            if not config:
                return

            guild = reaction.message.guild
            member = guild.get_member(user.id)
            role = guild.get_role(int(config["role_id"]))

            if not member or not role:
                return

            if action == "add" and role not in member.roles:
                await member.add_roles(role, reason="Reaction Role")
            elif action == "remove" and role in member.roles:
                await member.remove_roles(role, reason="Reaction Role Removed")

        except Exception as e:
            print(f"❌ Erro em reaction roles: {e}")

    async def handle_suggestion_reaction(self, reaction, user, action):
        """Gerenciar reações em sugestões"""
        try:
            # Buscar se mensagem é uma sugestão
            suggestion = await database.fetchone(
                "SELECT * FROM suggestions WHERE message_id = ?", (str(reaction.message.id),)
            )

            if not suggestion:
                return

            # Contar votos atualizados
            message = reaction.message
            upvotes = 0
            downvotes = 0

            for r in message.reactions:
                if str(r.emoji) == "👍":
                    upvotes = r.count - 1  # -1 para remover reação do bot
                elif str(r.emoji) == "👎":
                    downvotes = r.count - 1

            # Atualizar contadores no banco
            await database.run(
                "UPDATE suggestions SET upvotes = ?, downvotes = ? WHERE id = ?",
                (upvotes, downvotes, suggestion["id"]),
            )

            # Verificar se precisa tomar ação automática
            await self.check_suggestion_auto_actions(suggestion, upvotes, downvotes)

        except Exception as e:
            print(f"❌ Erro em reação de sugestão: {e}")

    async def handle_poll_reaction(self, reaction, user, action):
        """Gerenciar reações em polls"""
        try:
            # Buscar se mensagem é um poll
            poll = await database.fetchone(
                "SELECT * FROM polls WHERE message_id = ?", (str(reaction.message.id),)
            )

            if not poll:
                return

            # Verificar se é emoji válido do poll
            poll_options = await database.fetchall(
                "SELECT * FROM poll_options WHERE poll_id = ?", (poll["id"],)
            )

            valid_emojis = [option["emoji"] for option in poll_options]

            if str(reaction.emoji) not in valid_emojis:
                return

            # Remover outras reações do usuário (poll exclusivo)
            if poll.get("exclusive", True):
                for r in reaction.message.reactions:
                    if str(r.emoji) != str(reaction.emoji) and str(r.emoji) in valid_emojis:
                        await r.remove(user)

            # Atualizar contadores de opções
            for option in poll_options:
                if option["emoji"] == str(reaction.emoji):
                    # Contar reações atuais
                    for r in reaction.message.reactions:
                        if str(r.emoji) == option["emoji"]:
                            vote_count = r.count - 1  # -1 para remover reação do bot
                            await database.run(
                                "UPDATE poll_options SET votes = ? WHERE id = ?",
                                (vote_count, option["id"]),
                            )
                            break

        except Exception as e:
            print(f"❌ Erro em reação de poll: {e}")

    async def check_suggestion_auto_actions(self, suggestion, upvotes, downvotes):
        """Verificar ações automáticas em sugestões"""
        try:
            # Buscar configuração de sugestões
            config = await database.fetchone(
                "SELECT * FROM suggestion_config WHERE guild_id = ?", (suggestion["guild_id"],)
            )

            if not config:
                return

            auto_approve_threshold = config.get("auto_approve_threshold")
            auto_deny_threshold = config.get("auto_deny_threshold")

            # Verificar aprovação automática
            if auto_approve_threshold and upvotes >= auto_approve_threshold:
                if suggestion["status"] == "pending":
                    await self.auto_approve_suggestion(suggestion, upvotes)

            # Verificar negação automática
            elif auto_deny_threshold and downvotes >= auto_deny_threshold:
                if suggestion["status"] == "pending":
                    await self.auto_deny_suggestion(suggestion, downvotes)

        except Exception as e:
            print(f"❌ Erro verificando ações automáticas: {e}")

    async def auto_approve_suggestion(self, suggestion, votes):
        """Aprovar sugestão automaticamente"""
        try:
            # Atualizar status
            await database.run(
                "UPDATE suggestions SET status = 'approved', reviewed_at = ?, reviewed_by = 'system' WHERE id = ?",
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
                embed.color = 0x00FF00  # Verde
                embed.add_field(
                    name="✅ Status",
                    value=f"**APROVADA AUTOMATICAMENTE**\\n{votes} votos positivos",
                    inline=False,
                )

                await message.edit(embed=embed)

            except discord.NotFound:
                pass

        except Exception as e:
            print(f"❌ Erro aprovando sugestão automaticamente: {e}")

    async def auto_deny_suggestion(self, suggestion, votes):
        """Negar sugestão automaticamente"""
        try:
            # Atualizar status
            await database.run(
                "UPDATE suggestions SET status = 'denied', reviewed_at = ?, reviewed_by = 'system' WHERE id = ?",
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
                embed.color = 0xFF0000  # Vermelho
                embed.add_field(
                    name="❌ Status",
                    value=f"**NEGADA AUTOMATICAMENTE**\\n{votes} votos negativos",
                    inline=False,
                )

                await message.edit(embed=embed)

            except discord.NotFound:
                pass

        except Exception as e:
            print(f"❌ Erro negando sugestão automaticamente: {e}")


async def setup(bot):
    await bot.add_cog(ReactionAddHandler(bot))
