"""
Suggestion Reaction Handlers - Gerencia reações em sugestões
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class SuggestionReactionAdd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        await self.handle_suggestion_reaction(reaction, user, "add")

    async def handle_suggestion_reaction(self, reaction, user, action):
        """Gerenciar reações em sugestões"""
        try:
            # Verificar se é uma sugestão
            suggestion = await database.fetchone(
                "SELECT * FROM suggestions WHERE message_id = ?", (str(reaction.message.id),)
            )

            if not suggestion:
                return

            # Verificar se é emoji válido (👍 ou 👎)
            if str(reaction.emoji) not in ["👍", "👎"]:
                return

            # Verificar se usuário pode votar
            if not await self.can_user_vote(user, suggestion):
                # Remover reação inválida
                try:
                    await reaction.remove(user)
                except:
                    pass
                return

            # Remover reação oposta se existir
            await self.remove_opposite_reaction(reaction, user)

            # Atualizar contadores
            await self.update_suggestion_votes(suggestion["id"], reaction.message)

            # Verificar ações automáticas
            await self.check_auto_actions(suggestion, reaction.message)

        except Exception as e:
            print(f"❌ Erro processando reação em sugestão: {e}")

    async def can_user_vote(self, user, suggestion) -> bool:
        """Verificar se usuário pode votar na sugestão"""
        try:
            # Autor não pode votar na própria sugestão
            if str(user.id) == suggestion["author_id"]:
                return False

            # Verificar se sugestão ainda está ativa
            if suggestion["status"] != "pending":
                return False

            return True

        except Exception as e:
            print(f"❌ Erro verificando permissão de voto: {e}")
            return False

    async def remove_opposite_reaction(self, reaction, user):
        """Remover reação oposta do mesmo usuário"""
        try:
            opposite_emoji = "👎" if str(reaction.emoji) == "👍" else "👍"

            for r in reaction.message.reactions:
                if str(r.emoji) == opposite_emoji:
                    await r.remove(user)
                    break

        except Exception as e:
            print(f"❌ Erro removendo reação oposta: {e}")

    async def update_suggestion_votes(self, suggestion_id, message):
        """Atualizar contadores de votos"""
        try:
            upvotes = 0
            downvotes = 0

            for reaction in message.reactions:
                if str(reaction.emoji) == "👍":
                    upvotes = reaction.count - 1  # -1 para remover bot
                elif str(reaction.emoji) == "👎":
                    downvotes = reaction.count - 1

            await database.run(
                "UPDATE suggestions SET upvotes = ?, downvotes = ? WHERE id = ?",
                (upvotes, downvotes, suggestion_id),
            )

        except Exception as e:
            print(f"❌ Erro atualizando votos: {e}")

    async def check_auto_actions(self, suggestion, message):
        """Verificar ações automáticas baseadas em votos"""
        try:
            # Buscar configuração
            config = await database.fetchone(
                "SELECT * FROM suggestion_config WHERE guild_id = ?", (suggestion["guild_id"],)
            )

            if not config:
                return

            upvotes = 0
            downvotes = 0

            for reaction in message.reactions:
                if str(reaction.emoji) == "👍":
                    upvotes = reaction.count - 1
                elif str(reaction.emoji) == "👎":
                    downvotes = reaction.count - 1

            # Verificar auto-aprovação
            auto_approve = config.get("auto_approve_votes")
            if auto_approve and upvotes >= auto_approve and suggestion["status"] == "pending":
                await self.auto_approve_suggestion(suggestion, message, upvotes)

            # Verificar auto-rejeição
            auto_reject = config.get("auto_reject_votes")
            if auto_reject and downvotes >= auto_reject and suggestion["status"] == "pending":
                await self.auto_reject_suggestion(suggestion, message, downvotes)

        except Exception as e:
            print(f"❌ Erro verificando ações automáticas: {e}")

    async def auto_approve_suggestion(self, suggestion, message, votes):
        """Aprovar sugestão automaticamente"""
        try:
            # Atualizar status
            await database.run(
                "UPDATE suggestions SET status = 'approved', reviewed_at = ?, reviewed_by = ? WHERE id = ?",
                (discord.utils.utcnow().isoformat(), "system", suggestion["id"]),
            )

            # Atualizar embed
            embed = message.embeds[0] if message.embeds else discord.Embed()
            embed.color = 0x00FF00

            # Adicionar campo de status
            embed.add_field(
                name="✅ Status",
                value=f"**APROVADA AUTOMATICAMENTE**\\n{votes} votos positivos",
                inline=False,
            )

            await message.edit(embed=embed)

            # Notificar autor
            await self.notify_suggestion_author(suggestion, "approved", "automático")

        except Exception as e:
            print(f"❌ Erro aprovando sugestão automaticamente: {e}")

    async def auto_reject_suggestion(self, suggestion, message, votes):
        """Rejeitar sugestão automaticamente"""
        try:
            # Atualizar status
            await database.run(
                "UPDATE suggestions SET status = 'rejected', reviewed_at = ?, reviewed_by = ? WHERE id = ?",
                (discord.utils.utcnow().isoformat(), "system", suggestion["id"]),
            )

            # Atualizar embed
            embed = message.embeds[0] if message.embeds else discord.Embed()
            embed.color = 0xFF0000

            # Adicionar campo de status
            embed.add_field(
                name="❌ Status",
                value=f"**REJEITADA AUTOMATICAMENTE**\\n{votes} votos negativos",
                inline=False,
            )

            await message.edit(embed=embed)

            # Notificar autor
            await self.notify_suggestion_author(suggestion, "rejected", "automático")

        except Exception as e:
            print(f"❌ Erro rejeitando sugestão automaticamente: {e}")

    async def notify_suggestion_author(self, suggestion, status, reason):
        """Notificar autor sobre mudança de status"""
        try:
            author = self.bot.get_user(int(suggestion["author_id"]))
            if not author:
                return

            guild = self.bot.get_guild(int(suggestion["guild_id"]))
            if not guild:
                return

            status_text = {
                "approved": "✅ **APROVADA**",
                "rejected": "❌ **REJEITADA**",
                "under_review": "🔍 **EM ANÁLISE**",
            }.get(status, status.upper())

            embed = discord.Embed(
                title="📝 Status da Sugestão Atualizado",
                description=f"Sua sugestão em **{guild.name}** foi {status_text}",
                color={"approved": 0x00FF00, "rejected": 0xFF0000}.get(status, 0x0099FF),
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(
                name="💡 Sugestão",
                value=suggestion["content"][:200]
                + ("..." if len(suggestion["content"]) > 200 else ""),
                inline=False,
            )

            embed.add_field(name="📋 Motivo", value=f"Decisão {reason}", inline=True)

            embed.set_footer(text=f"Servidor: {guild.name}")

            try:
                await author.send(embed=embed)
            except discord.Forbidden:
                # Usuário não aceita DMs
                pass

        except Exception as e:
            print(f"❌ Erro notificando autor: {e}")


class SuggestionReactionRemove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if user.bot:
            return

        await self.handle_suggestion_reaction_remove(reaction, user)

    async def handle_suggestion_reaction_remove(self, reaction, user):
        """Gerenciar remoção de reações em sugestões"""
        try:
            # Verificar se é uma sugestão
            suggestion = await database.fetchone(
                "SELECT * FROM suggestions WHERE message_id = ?", (str(reaction.message.id),)
            )

            if not suggestion:
                return

            # Verificar se é emoji válido
            if str(reaction.emoji) not in ["👍", "👎"]:
                return

            # Atualizar contadores
            upvotes = 0
            downvotes = 0

            for r in reaction.message.reactions:
                if str(r.emoji) == "👍":
                    upvotes = r.count - 1  # -1 para remover bot
                elif str(r.emoji) == "👎":
                    downvotes = r.count - 1

            await database.run(
                "UPDATE suggestions SET upvotes = ?, downvotes = ? WHERE id = ?",
                (upvotes, downvotes, suggestion["id"]),
            )

        except Exception as e:
            print(f"❌ Erro processando remoção de reação: {e}")


async def setup(bot):
    await bot.add_cog(SuggestionReactionAdd(bot))
    await bot.add_cog(SuggestionReactionRemove(bot))
