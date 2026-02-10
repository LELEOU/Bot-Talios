"""
Reaction Remove Handler - Gerencia remoção de reações
"""

import sys
from pathlib import Path

from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class ReactionRemoveHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if user.bot:
            return

        try:
            # Verificar se é reação em sistema de roles
            await self.handle_reaction_roles(reaction, user, "remove")

            # Verificar se é reação em sugestão
            await self.handle_suggestion_reaction(reaction, user, "remove")

            # Verificar se é reação em poll
            await self.handle_poll_reaction(reaction, user, "remove")

        except Exception as e:
            print(f"❌ Erro processando remoção de reação: {e}")

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

            # Remover role quando reação é removida
            if role in member.roles:
                await member.remove_roles(role, reason="Reaction Role Removed")

        except Exception as e:
            print(f"❌ Erro removendo reaction role: {e}")

    async def handle_suggestion_reaction(self, reaction, user, action):
        """Gerenciar remoções de reações em sugestões"""
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

        except Exception as e:
            print(f"❌ Erro atualizando votos de sugestão: {e}")

    async def handle_poll_reaction(self, reaction, user, action):
        """Gerenciar remoções de reações em polls"""
        try:
            # Buscar se mensagem é um poll
            poll = await database.fetchone(
                "SELECT * FROM polls WHERE message_id = ?", (str(reaction.message.id),)
            )

            if not poll:
                return

            # Buscar opções do poll
            poll_options = await database.fetchall(
                "SELECT * FROM poll_options WHERE poll_id = ?", (poll["id"],)
            )

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
            print(f"❌ Erro atualizando votos de poll: {e}")


async def setup(bot):
    await bot.add_cog(ReactionRemoveHandler(bot))
