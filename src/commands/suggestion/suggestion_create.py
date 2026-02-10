"""
Sistema de Sugestões - Criar e Configurar
Comando para enviar sugestões e configurar o sistema
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
import uuid

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class SuggestionVoteView(discord.ui.View):
    """Interface de votação para sugestões"""

    def __init__(self, suggestion_id: str) -> None:
        super().__init__(timeout=None)
        self.suggestion_id: str = suggestion_id

    @discord.ui.button(
        label="👍", style=discord.ButtonStyle.success, custom_id="vote_approve", emoji="✅"
    )
    async def vote_approve(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.handle_vote(interaction, "approve", "👍")

    @discord.ui.button(
        label="👎", style=discord.ButtonStyle.danger, custom_id="vote_reject", emoji="❌"
    )
    async def vote_reject(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.handle_vote(interaction, "reject", "👎")

    @discord.ui.button(
        label="🤷", style=discord.ButtonStyle.secondary, custom_id="vote_neutral", emoji="🤷"
    )
    async def vote_neutral(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.handle_vote(interaction, "neutral", "🤷")

    async def handle_vote(
        self, interaction: discord.Interaction, vote_type: str, emoji: str
    ) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # 💾 REGISTRAR VOTO NO BANCO
            try:
                from ...utils.database import database

                # Verificar se já votou
                existing_vote: dict[str, Any] | None = await database.get(
                    "SELECT * FROM suggestion_votes WHERE suggestion_id = ? AND user_id = ?",
                    (self.suggestion_id, str(interaction.user.id)),
                )

                if existing_vote:
                    if existing_vote["vote_type"] == vote_type:
                        # Remover voto (toggle)
                        await database.execute(
                            "DELETE FROM suggestion_votes WHERE suggestion_id = ? AND user_id = ?",
                            (self.suggestion_id, str(interaction.user.id)),
                        )
                        await interaction.followup.send(
                            f"🗳️ **Voto removido!**\nSua opinião {emoji} foi retirada da sugestão.",
                            ephemeral=True,
                        )
                    else:
                        # Atualizar voto
                        await database.execute(
                            "UPDATE suggestion_votes SET vote_type = ?, voted_at = ? WHERE suggestion_id = ? AND user_id = ?",
                            (
                                vote_type,
                                datetime.now().isoformat(),
                                self.suggestion_id,
                                str(interaction.user.id),
                            ),
                        )
                        await interaction.followup.send(
                            f"🔄 **Voto alterado!**\nSua opinião foi alterada para {emoji}",
                            ephemeral=True,
                        )
                else:
                    # Novo voto
                    await database.execute(
                        "INSERT INTO suggestion_votes (suggestion_id, user_id, vote_type, voted_at) VALUES (?, ?, ?, ?)",
                        (
                            self.suggestion_id,
                            str(interaction.user.id),
                            vote_type,
                            datetime.now().isoformat(),
                        ),
                    )
                    await interaction.followup.send(
                        f"✅ **Voto registrado!**\nSua opinião {emoji} foi contabilizada.",
                        ephemeral=True,
                    )

                # 📊 ATUALIZAR EMBED COM NOVAS CONTAGENS
                await self.update_suggestion_embed(interaction)

            except Exception as e:
                print(f"❌ Erro ao registrar voto: {e}")
                await interaction.followup.send(
                    "❌ Erro ao registrar seu voto. Tente novamente.", ephemeral=True
                )

        except Exception as e:
            print(f"❌ Erro no sistema de votação: {e}")

    async def update_suggestion_embed(self, interaction: discord.Interaction) -> None:
        """Atualiza o embed da sugestão com contagens atualizadas"""
        try:
            from ...utils.database import database

            # Buscar votos atualizados
            votes: list[dict[str, Any]] | None = await database.get_all(
                "SELECT vote_type FROM suggestion_votes WHERE suggestion_id = ?",
                (self.suggestion_id,),
            )

            votes = votes or []

            approve_count: int = len([v for v in votes if v["vote_type"] == "approve"])
            reject_count: int = len([v for v in votes if v["vote_type"] == "reject"])
            neutral_count: int = len([v for v in votes if v["vote_type"] == "neutral"])
            total_votes: int = len(votes)

            # Buscar dados da sugestão
            suggestion: dict[str, Any] | None = await database.get(
                "SELECT * FROM suggestions WHERE id = ?", (self.suggestion_id,)
            )

            if not suggestion:
                return

            # 🔍 OBTER EMBED ATUAL
            message: discord.Message = interaction.message
            if message.embeds:
                embed: discord.Embed = message.embeds[0]

                # Atualizar field de votação
                for i, field in enumerate(embed.fields):
                    if "📊 Votação" in field.name:
                        # Calcular porcentagens
                        approve_pct: float = (
                            (approve_count / total_votes * 100) if total_votes > 0 else 0
                        )
                        reject_pct: float = (
                            (reject_count / total_votes * 100) if total_votes > 0 else 0
                        )
                        neutral_pct: float = (
                            (neutral_count / total_votes * 100) if total_votes > 0 else 0
                        )

                        # Criar barras de progresso
                        approve_bar: str = self.create_progress_bar(approve_pct, "🟩")
                        reject_bar: str = self.create_progress_bar(reject_pct, "🟥")
                        neutral_bar: str = self.create_progress_bar(neutral_pct, "🟨")

                        new_value: str = (
                            f"**👍 Aprovar:** {approve_count} votos ({approve_pct:.1f}%)\n"
                            f"{approve_bar}\n\n"
                            f"**👎 Rejeitar:** {reject_count} votos ({reject_pct:.1f}%)\n"
                            f"{reject_bar}\n\n"
                            f"**🤷 Neutro:** {neutral_count} votos ({neutral_pct:.1f}%)\n"
                            f"{neutral_bar}\n\n"
                            f"**📊 Total:** {total_votes} votos"
                        )

                        embed.set_field_at(
                            i, name="📊 Votação Atual", value=new_value, inline=False
                        )
                        break

                # Atualizar cor do embed baseado nos votos
                if total_votes > 0:
                    if approve_count > reject_count and approve_count > neutral_count:
                        embed.color = 0x00FF00  # Verde para aprovação
                    elif reject_count > approve_count and reject_count > neutral_count:
                        embed.color = 0xFF0000  # Vermelho para rejeição
                    else:
                        embed.color = 0xFFFF00  # Amarelo para empate/neutro

                # Atualizar mensagem
                await message.edit(embed=embed, view=self)

        except Exception as e:
            print(f"❌ Erro ao atualizar embed: {e}")

    def create_progress_bar(self, percentage: float, block: str, length: int = 10) -> str:
        """Cria barra de progresso visual"""
        filled: int = int(percentage / 10)  # Cada bloco representa 10%
        empty: int = length - filled
        return f"{block * filled}{'⬜' * empty} {percentage:.1f}%"


class SuggestionSystem(commands.Cog):
    """Sistema de criação e configuração de sugestões"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(name="suggest", description="💡 Enviar uma sugestão para o servidor")
    @app_commands.describe(
        titulo="Título da sua sugestão (máximo 100 caracteres)",
        descricao="Descrição detalhada da sugestão",
        categoria="Categoria da sugestão",
    )
    async def suggest(
        self,
        interaction: discord.Interaction,
        titulo: str,
        descricao: str,
        categoria: str | None = "Geral",
    ) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # ✅ VALIDAÇÕES
            if len(titulo) > 100:
                await interaction.followup.send(
                    "❌ **Título muito longo!**\n"
                    f"Máximo: 100 caracteres\n"
                    f"Atual: {len(titulo)} caracteres",
                    ephemeral=True,
                )
                return

            if len(descricao) > 1000:
                await interaction.followup.send(
                    "❌ **Descrição muito longa!**\n"
                    f"Máximo: 1000 caracteres\n"
                    f"Atual: {len(descricao)} caracteres",
                    ephemeral=True,
                )
                return

            # 🔍 VERIFICAR SE SISTEMA ESTÁ CONFIGURADO
            try:
                from ...utils.database import database

                config: dict[str, Any] | None = await database.get(
                    "SELECT * FROM suggestion_config WHERE guild_id = ?",
                    (str(interaction.guild.id),),
                )

                if not config:
                    await interaction.followup.send(
                        "❌ **Sistema de sugestões não configurado!**\n"
                        "Peça para um administrador usar `/suggestion-setup` primeiro.",
                        ephemeral=True,
                    )
                    return

                suggestion_channel_id: str = config["channel_id"]
                suggestion_channel: discord.TextChannel | None = interaction.guild.get_channel(
                    int(suggestion_channel_id)
                )

                if not suggestion_channel:
                    await interaction.followup.send(
                        "❌ **Canal de sugestões não encontrado!**\n"
                        "O canal pode ter sido deletado. Reconfigure o sistema.",
                        ephemeral=True,
                    )
                    return

            except Exception as e:
                print(f"❌ Erro ao verificar configuração: {e}")
                await interaction.followup.send(
                    "❌ Erro ao verificar configuração do sistema.", ephemeral=True
                )
                return

            # 🆔 GERAR ID ÚNICO PARA SUGESTÃO
            suggestion_id: str = str(uuid.uuid4())[:8]

            # 🎨 CRIAR EMBED DA SUGESTÃO
            suggestion_embed: discord.Embed = discord.Embed(
                title=f"💡 **{titulo}**",
                description=f"**📝 Descrição:**\n{descricao}",
                color=0x2F3136,
                timestamp=datetime.now(),
            )

            suggestion_embed.add_field(
                name="👤 Autor",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            suggestion_embed.add_field(name="📂 Categoria", value=f"`{categoria}`", inline=True)

            suggestion_embed.add_field(name="🆔 ID", value=f"`{suggestion_id}`", inline=True)

            suggestion_embed.add_field(
                name="📊 Votação Atual",
                value="**👍 Aprovar:** 0 votos (0.0%)\n"
                "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0.0%\n\n"
                "**👎 Rejeitar:** 0 votos (0.0%)\n"
                "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0.0%\n\n"
                "**🤷 Neutro:** 0 votos (0.0%)\n"
                "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0.0%\n\n"
                "**📊 Total:** 0 votos",
                inline=False,
            )

            suggestion_embed.add_field(
                name="📅 Status", value="🟡 **Pendente** - Aguardando votação", inline=True
            )

            suggestion_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            suggestion_embed.set_footer(
                text=f"Sugestão #{suggestion_id} • Vote usando os botões abaixo",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            # 🎮 CRIAR VIEW COM BOTÕES DE VOTAÇÃO
            vote_view: SuggestionVoteView = SuggestionVoteView(suggestion_id)

            # 📨 ENVIAR SUGESTÃO
            try:
                suggestion_message: discord.Message = await suggestion_channel.send(
                    f"🆕 **Nova sugestão de {interaction.user.mention}!**",
                    embed=suggestion_embed,
                    view=vote_view,
                )

                # 📌 TENTAR FIXAR SE CONFIGURADO
                if config.get("auto_pin", False):
                    try:
                        await suggestion_message.pin()
                    except:
                        pass

            except discord.Forbidden:
                await interaction.followup.send(
                    f"❌ **Sem permissão para enviar no canal {suggestion_channel.mention}!**\n"
                    "Verifique se tenho permissão de **Enviar Mensagens** nesse canal.",
                    ephemeral=True,
                )
                return

            # 💾 SALVAR SUGESTÃO NO BANCO
            try:
                await database.execute(
                    """INSERT INTO suggestions 
                       (id, guild_id, channel_id, message_id, user_id, title, description, category, status, created_at) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        suggestion_id,
                        str(interaction.guild.id),
                        str(suggestion_channel.id),
                        str(suggestion_message.id),
                        str(interaction.user.id),
                        titulo,
                        descricao,
                        categoria,
                        "pending",
                        datetime.now().isoformat(),
                    ),
                )
            except Exception as e:
                print(f"❌ Erro ao salvar sugestão: {e}")

            # ✅ CONFIRMAÇÃO PARA O USUÁRIO
            success_embed: discord.Embed = discord.Embed(
                title="✅ **Sugestão Enviada!**",
                description=f"Sua sugestão foi publicada em {suggestion_channel.mention}",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="💡 Sugestão",
                value=f"**{titulo}**\n`{descricao[:100]}{'...' if len(descricao) > 100 else ''}`",
                inline=False,
            )

            success_embed.add_field(
                name="🆔 ID da Sugestão", value=f"`{suggestion_id}`", inline=True
            )

            success_embed.add_field(
                name="🔗 Link Direto",
                value=f"[Ver sugestão]({suggestion_message.jump_url})",
                inline=True,
            )

            success_embed.add_field(
                name="🎯 Próximos passos",
                value="• Sua sugestão está disponível para votação\n"
                "• A comunidade pode votar usando os botões\n"
                "• Administradores podem aprovar/rejeitar",
                inline=False,
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando suggest: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao processar sugestão. Tente novamente.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="suggestion-setup", description="⚙️ Configurar sistema de sugestões")
    @app_commands.describe(
        canal="Canal onde as sugestões serão enviadas",
        auto_pin="Fixar automaticamente novas sugestões",
        categoria_padrao="Categoria padrão para sugestões",
    )
    async def suggestion_setup(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        auto_pin: bool | None = False,
        categoria_padrao: str | None = "Geral",
    ) -> None:
        try:
            # 🛡️ VERIFICAR PERMISSÕES
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para configurar sugestões. **Necessário**: Gerenciar Servidor",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # 🔍 VERIFICAR PERMISSÕES DO BOT NO CANAL
            permissions: discord.Permissions = canal.permissions_for(interaction.guild.me)
            missing_perms: list[str] = []

            if not permissions.send_messages:
                missing_perms.append("Enviar Mensagens")
            if not permissions.embed_links:
                missing_perms.append("Inserir Links")
            if not permissions.add_reactions:
                missing_perms.append("Adicionar Reações")
            if auto_pin and not permissions.manage_messages:
                missing_perms.append("Gerenciar Mensagens (para fixar)")

            if missing_perms:
                await interaction.followup.send(
                    f"❌ **Permissões insuficientes no canal {canal.mention}!**\n\n"
                    f"**🔐 Permissões necessárias:**\n"
                    + "\n".join([f"• {perm}" for perm in missing_perms]),
                    ephemeral=True,
                )
                return

            # 💾 SALVAR CONFIGURAÇÃO
            try:
                from ...utils.database import database

                # Verificar se já existe configuração
                existing_config: dict[str, Any] | None = await database.get(
                    "SELECT * FROM suggestion_config WHERE guild_id = ?",
                    (str(interaction.guild.id),),
                )

                if existing_config:
                    # Atualizar configuração existente
                    await database.execute(
                        "UPDATE suggestion_config SET channel_id = ?, auto_pin = ?, default_category = ? WHERE guild_id = ?",
                        (str(canal.id), auto_pin, categoria_padrao, str(interaction.guild.id)),
                    )
                else:
                    # Criar nova configuração
                    await database.execute(
                        "INSERT INTO suggestion_config (guild_id, channel_id, auto_pin, default_category) VALUES (?, ?, ?, ?)",
                        (str(interaction.guild.id), str(canal.id), auto_pin, categoria_padrao),
                    )

            except Exception as e:
                print(f"❌ Erro ao salvar configuração: {e}")
                await interaction.followup.send(
                    "❌ Erro ao salvar configuração. Tente novamente.", ephemeral=True
                )
                return

            # 🎨 EMBED DE DEMONSTRAÇÃO NO CANAL
            demo_embed: discord.Embed = discord.Embed(
                title="💡 **SISTEMA DE SUGESTÕES CONFIGURADO!**",
                description="Este canal agora está configurado para receber sugestões da comunidade!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            demo_embed.add_field(
                name="📖 Como funciona",
                value="• Use `/suggest` para enviar sugestões\n"
                "• Vote usando os botões 👍👎🤷\n"
                "• Administradores podem aprovar/rejeitar\n"
                "• Acompanhe o status das suas sugestões",
                inline=False,
            )

            demo_embed.add_field(
                name="⚙️ Configurações",
                value=f"**Canal:** {canal.mention}\n"
                f"**Auto-fixar:** {'✅ Ativo' if auto_pin else '❌ Desativo'}\n"
                f"**Categoria padrão:** `{categoria_padrao}`",
                inline=True,
            )

            demo_embed.add_field(
                name="🎯 Comandos",
                value="`/suggest` - Enviar sugestão\n"
                "`/suggestion-list` - Ver sugestões\n"
                "`/suggestion-manage` - Gerenciar (Admin)",
                inline=True,
            )

            demo_embed.set_footer(
                text=f"Configurado por {interaction.user} • Sistema ativo!",
                icon_url=interaction.user.display_avatar.url,
            )

            await canal.send(embed=demo_embed)

            # ✅ CONFIRMAÇÃO PARA ADMIN
            success_embed: discord.Embed = discord.Embed(
                title="✅ Sistema de Sugestões Configurado!",
                description=f"O sistema foi configurado com sucesso no canal {canal.mention}",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="🎯 Próximos passos",
                value="• Os usuários já podem usar `/suggest`\n"
                "• Sugestões aparecerão com botões de votação\n"
                "• Use `/suggestion-list` para gerenciar",
                inline=False,
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando suggestion-setup: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao configurar sistema de sugestões. Tente novamente.", ephemeral=True
                )
            except:
                pass


async def setup(bot: commands.Bot) -> None:
    """Carrega o cog e views persistentes"""
    await bot.add_cog(SuggestionSystem(bot))

    # Adicionar views persistentes
    bot.add_view(SuggestionVoteView("persistent"))
