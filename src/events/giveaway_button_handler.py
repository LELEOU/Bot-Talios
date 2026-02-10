"""
Giveaway Button Handler - Sistema de botões de sorteios
Gerencia participação em sorteios através de botões
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import database


class GiveawayButtonHandler(commands.Cog):
    """Handler para botões de sorteios"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Listener para interações de botões"""
        if not interaction.type == discord.InteractionType.component:
            return

        if not hasattr(interaction, "custom_id"):
            return

        # Verificar se é botão de giveaway
        if interaction.custom_id != "giveaway_join":
            return

        try:
            await interaction.response.defer(ephemeral=True)

            message_id = interaction.message.id

            # Buscar giveaway no banco
            giveaway = await self.get_giveaway_by_message_id(message_id)

            if not giveaway:
                await interaction.followup.send(
                    content="❌ Sorteio não encontrado ou inválido.", ephemeral=True
                )
                return

            if giveaway.get("status") != "active":
                await interaction.followup.send(
                    content="❌ Este sorteio já foi finalizado.", ephemeral=True
                )
                return

            # Verificar se usuário já está participando
            is_participating = await self.is_user_in_giveaway(giveaway["id"], interaction.user.id)

            if is_participating:
                # Remover participação
                success = await self.remove_giveaway_entry(giveaway["id"], interaction.user.id)

                if success:
                    await interaction.followup.send(
                        content="❌ Você saiu do sorteio! Clique novamente para participar.",
                        ephemeral=True,
                    )

                    # Atualizar embed do sorteio
                    await self.update_giveaway_embed(interaction.message, giveaway["id"])
                else:
                    await interaction.followup.send(
                        content="❌ Erro ao sair do sorteio. Tente novamente.", ephemeral=True
                    )
            else:
                # Adicionar participação
                success = await self.add_giveaway_entry(giveaway["id"], interaction.user.id)

                if success:
                    await interaction.followup.send(
                        content="✅ Você entrou no sorteio! Boa sorte! 🍀", ephemeral=True
                    )

                    # Atualizar embed do sorteio
                    await self.update_giveaway_embed(interaction.message, giveaway["id"])
                else:
                    await interaction.followup.send(
                        content="❌ Erro ao entrar no sorteio. Tente novamente.", ephemeral=True
                    )

        except Exception as e:
            print(f"❌ Erro no botão de giveaway: {e}")
            try:
                await interaction.followup.send(
                    content="❌ Ocorreu um erro. Tente novamente.", ephemeral=True
                )
            except:
                pass  # Interação já expirou

    async def get_giveaway_by_message_id(self, message_id: int) -> dict:
        """Buscar giveaway pelo ID da mensagem"""
        try:
            result = await database.fetchone(
                "SELECT * FROM giveaways WHERE message_id = ?", (str(message_id),)
            )
            return dict(result) if result else None

        except Exception as e:
            print(f"❌ Erro buscando giveaway: {e}")
            return None

    async def is_user_in_giveaway(self, giveaway_id: int, user_id: int) -> bool:
        """Verificar se usuário está participando do sorteio"""
        try:
            result = await database.fetchone(
                "SELECT id FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?",
                (giveaway_id, str(user_id)),
            )
            return result is not None

        except Exception as e:
            print(f"❌ Erro verificando participação: {e}")
            return False

    async def add_giveaway_entry(self, giveaway_id: int, user_id: int) -> bool:
        """Adicionar entrada no sorteio"""
        try:
            await database.run(
                "INSERT INTO giveaway_entries (giveaway_id, user_id, joined_at) VALUES (?, ?, ?)",
                (giveaway_id, str(user_id), discord.utils.utcnow().isoformat()),
            )
            return True

        except Exception as e:
            print(f"❌ Erro adicionando entrada: {e}")
            return False

    async def remove_giveaway_entry(self, giveaway_id: int, user_id: int) -> bool:
        """Remover entrada do sorteio"""
        try:
            await database.run(
                "DELETE FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?",
                (giveaway_id, str(user_id)),
            )
            return True

        except Exception as e:
            print(f"❌ Erro removendo entrada: {e}")
            return False

    async def get_giveaway_entries_count(self, giveaway_id: int) -> int:
        """Contar participantes do sorteio"""
        try:
            result = await database.fetchone(
                "SELECT COUNT(*) as count FROM giveaway_entries WHERE giveaway_id = ?",
                (giveaway_id,),
            )
            return result["count"] if result else 0

        except Exception as e:
            print(f"❌ Erro contando participantes: {e}")
            return 0

    async def update_giveaway_embed(self, message: discord.Message, giveaway_id: int):
        """Atualizar embed do sorteio com nova contagem"""
        try:
            # Buscar dados atualizados do sorteio
            giveaway = await database.fetchone(
                "SELECT * FROM giveaways WHERE id = ?", (giveaway_id,)
            )

            if not giveaway:
                return

            # Contar participantes
            participants_count = await self.get_giveaway_entries_count(giveaway_id)

            # Reconstruir embed
            embed = discord.Embed(
                title="🎉 SORTEIO ATIVO",
                description=giveaway.get("description", "Sorteio em andamento!"),
                color=0x00FF00,
                timestamp=discord.utils.parse_time(giveaway["ends_at"]),
            )

            embed.add_field(
                name="🎁 Prêmio", value=giveaway.get("prize", "Não especificado"), inline=True
            )

            embed.add_field(
                name="👥 Participantes", value=f"**{participants_count:,}**", inline=True
            )

            embed.add_field(
                name="🏆 Vencedores", value=f"**{giveaway.get('winners', 1)}**", inline=True
            )

            embed.add_field(
                name="⏰ Termina em",
                value=f"<t:{int(discord.utils.parse_time(giveaway['ends_at']).timestamp())}:R>",
                inline=False,
            )

            embed.set_footer(
                text="Clique no botão abaixo para participar!",
                icon_url=self.bot.user.display_avatar.url,
            )

            # Manter o botão original
            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    label=f"🎉 Participar ({participants_count})",
                    custom_id="giveaway_join",
                    style=discord.ButtonStyle.primary,
                    emoji="🎉",
                )
            )

            # Atualizar mensagem
            await message.edit(embed=embed, view=view)

        except Exception as e:
            print(f"❌ Erro atualizando embed do sorteio: {e}")


async def setup(bot):
    """Setup function para carregar o cog"""
    await bot.add_cog(GiveawayButtonHandler(bot))
