"""
Sistema de Notes - Gerenciamento de Anotações de Usuários
Sistema completo para moderadores criarem anotações sobre usuários
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class NoteCreateModal(discord.ui.Modal):
    """Modal para criar anotações"""

    def __init__(self, user: discord.Member, moderator: discord.Member) -> None:
        super().__init__(title=f"📝 Nova Anotação - {user.display_name}", timeout=300)
        self.target_user: discord.Member = user
        self.moderator: discord.Member = moderator

        # Campo para o título da anotação
        self.note_title = discord.ui.TextInput(
            label="Título da Anotação",
            placeholder="Ex: Comportamento suspeito, Advertência verbal, etc.",
            required=True,
            max_length=100,
        )

        # Campo para o conteúdo da anotação
        self.note_content = discord.ui.TextInput(
            label="Conteúdo da Anotação",
            placeholder="Descreva detalhadamente o ocorrido...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
        )

        # Campo para categoria
        self.note_category = discord.ui.TextInput(
            label="Categoria",
            placeholder="Ex: warning, info, positive, negative, ban, kick",
            required=False,
            max_length=50,
            default="info",
        )

        # Campo para severidade (1-5)
        self.note_severity = discord.ui.TextInput(
            label="Severidade (1-5)",
            placeholder="1 = Leve, 3 = Moderada, 5 = Grave",
            required=False,
            max_length=1,
            default="3",
        )

        self.add_item(self.note_title)
        self.add_item(self.note_content)
        self.add_item(self.note_category)
        self.add_item(self.note_severity)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # Validar severidade
            severity: int
            try:
                severity = int(self.note_severity.value) if self.note_severity.value else 3
                severity = max(1, min(5, severity))
            except Exception:
                severity = 3

            # Criar dados da anotação
            note_data: dict[str, Any] = {
                "id": f"{interaction.guild.id}_{self.target_user.id}_{int(datetime.now().timestamp())}",
                "guild_id": str(interaction.guild.id),
                "user_id": str(self.target_user.id),
                "moderator_id": str(self.moderator.id),
                "title": self.note_title.value,
                "content": self.note_content.value,
                "category": self.note_category.value.lower()
                if self.note_category.value
                else "info",
                "severity": severity,
                "created_at": datetime.now().isoformat(),
                "active": True,
            }

            # Salvar no banco de dados
            try:
                from ...utils.database import database

                await database.execute(
                    """INSERT INTO user_notes 
                    (note_id, guild_id, user_id, moderator_id, title, content, category, severity, created_at, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        note_data["id"],
                        note_data["guild_id"],
                        note_data["user_id"],
                        note_data["moderator_id"],
                        note_data["title"],
                        note_data["content"],
                        note_data["category"],
                        note_data["severity"],
                        note_data["created_at"],
                        1,
                    ),
                )
            except Exception as e:
                print(f"❌ Erro ao salvar anotação: {e}")
                await interaction.followup.send(
                    "❌ Erro ao salvar a anotação no banco de dados.", ephemeral=True
                )
                return

            # Criar embed de confirmação
            confirmation_embed: discord.Embed = discord.Embed(
                title="✅ **ANOTAÇÃO CRIADA**",
                description=f"Anotação sobre {self.target_user.mention} foi criada com sucesso!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            confirmation_embed.add_field(name="📝 Título", value=note_data["title"], inline=False)

            confirmation_embed.add_field(
                name="📄 Conteúdo",
                value=note_data["content"][:200]
                + ("..." if len(note_data["content"]) > 200 else ""),
                inline=False,
            )

            confirmation_embed.add_field(
                name="🏷️ Categoria", value=note_data["category"].title(), inline=True
            )

            confirmation_embed.add_field(
                name="⚡ Severidade",
                value="🟢 Leve"
                if severity <= 2
                else "🟡 Moderada"
                if severity <= 3
                else "🔴 Grave",
                inline=True,
            )

            confirmation_embed.add_field(
                name="👮 Moderador", value=self.moderator.mention, inline=True
            )

            confirmation_embed.set_thumbnail(url=self.target_user.display_avatar.url)
            confirmation_embed.set_footer(
                text=f"ID: {note_data['id'][:16]}...", icon_url=self.moderator.display_avatar.url
            )

            await interaction.followup.send(embed=confirmation_embed, ephemeral=True)

            # Enviar log se configurado
            try:
                log_config: dict[str, Any] | None = await database.get(
                    "SELECT channel_id FROM logs WHERE guild_id = ? AND log_type = 'notes'",
                    (str(interaction.guild.id)),  # type: ignore
                )

                if log_config:
                    log_channel: discord.abc.GuildChannel | None = interaction.guild.get_channel(int(log_config["channel_id"]))  # type: ignore
                    if log_channel and isinstance(log_channel, discord.TextChannel):
                        log_embed: discord.Embed = discord.Embed(
                            title="📝 **NOVA ANOTAÇÃO CRIADA**",
                            color=0x4A90E2,
                            timestamp=datetime.now(),
                        )

                        log_embed.add_field(
                            name="👤 Usuário",
                            value=f"{self.target_user.mention}\n`{self.target_user.id}`",
                            inline=True,
                        )

                        log_embed.add_field(
                            name="👮 Moderador",
                            value=f"{self.moderator.mention}\n`{self.moderator.id}`",
                            inline=True,
                        )

                        log_embed.add_field(
                            name="📝 Título", value=note_data["title"], inline=False
                        )

                        await log_channel.send(embed=log_embed)
            except Exception:
                pass

        except Exception as e:
            print(f"❌ Erro no modal de anotação: {e}")
            try:
                await interaction.followup.send("❌ Erro ao processar anotação.", ephemeral=True)
            except Exception:
                pass


class NotesCreation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.categories: dict[str, dict[str, Any]] = {
            "info": {"emoji": "ℹ️", "color": 0x4A90E2, "name": "Informação"},
            "warning": {"emoji": "⚠️", "color": 0xFFA500, "name": "Advertência"},
            "positive": {"emoji": "✅", "color": 0x00FF00, "name": "Positiva"},
            "negative": {"emoji": "❌", "color": 0xFF6B6B, "name": "Negativa"},
            "ban": {"emoji": "🔨", "color": 0x8B0000, "name": "Banimento"},
            "kick": {"emoji": "🥾", "color": 0xFF4500, "name": "Expulsão"},
            "mute": {"emoji": "🔇", "color": 0x696969, "name": "Silenciamento"},
            "other": {"emoji": "📋", "color": 0x2F3136, "name": "Outros"},
        }

    @app_commands.command(name="note-add", description="📝 Adicionar anotação sobre um usuário")
    @app_commands.describe(usuario="Usuário para adicionar anotação")
    async def note_add(self, interaction: discord.Interaction, usuario: discord.Member) -> None:
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.manage_messages:  # type: ignore
                await interaction.response.send_message(
                    "❌ Você não tem permissão para criar anotações. **Necessário**: Gerenciar Mensagens",
                    ephemeral=True,
                )
                return

            # Verificar se não está tentando anotar sobre si mesmo
            if usuario.id == interaction.user.id:
                await interaction.response.send_message(
                    "❌ Você não pode criar anotações sobre si mesmo.", ephemeral=True
                )
                return

            # Verificar se o usuário alvo não é um moderador/admin de nível superior
            if (
                usuario.guild_permissions.administrator
                and not interaction.user.guild_permissions.administrator  # type: ignore
            ):
                await interaction.response.send_message(
                    "❌ Você não pode criar anotações sobre administradores.", ephemeral=True
                )
                return

            # Abrir modal para criar anotação
            modal: NoteCreateModal = NoteCreateModal(usuario, interaction.user)  # type: ignore
            await interaction.response.send_modal(modal)

        except Exception as e:
            print(f"❌ Erro no comando note-add: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao abrir formulário de anotação.", ephemeral=True
                )
            except Exception:
                pass

    @app_commands.command(name="note-list", description="📋 Ver anotações de um usuário")
    @app_commands.describe(
        usuario="Usuário para ver anotações",
        categoria="Filtrar por categoria",
        ativo="Mostrar apenas anotações ativas",
    )
    async def note_list(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        categoria: str | None = None,
        ativo: bool | None = True,
    ) -> None:
        try:
            if not interaction.user.guild_permissions.manage_messages:  # type: ignore
                await interaction.response.send_message(
                    "❌ Você não tem permissão para ver anotações.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar anotações
            try:
                from ...utils.database import database

                query: str = "SELECT * FROM user_notes WHERE guild_id = ? AND user_id = ?"
                params: list[str] = [str(interaction.guild.id), str(usuario.id)]  # type: ignore

                if categoria:
                    query += " AND category = ?"
                    params.append(categoria.lower())

                if ativo:
                    query += " AND active = 1"

                query += " ORDER BY created_at DESC"

                notes: list[dict[str, Any]] = await database.get_all(query, params)

            except Exception as e:
                print(f"❌ Erro ao buscar anotações: {e}")
                await interaction.followup.send(
                    "❌ Erro ao buscar anotações no banco de dados.", ephemeral=True
                )
                return

            if not notes:
                empty_embed: discord.Embed = discord.Embed(
                    title="📋 **NENHUMA ANOTAÇÃO ENCONTRADA**",
                    description=f"Não há anotações {'ativas' if ativo else ''} para {usuario.mention}.",
                    color=0x2F3136,
                    timestamp=datetime.now(),
                )

                empty_embed.set_thumbnail(url=usuario.display_avatar.url)
                await interaction.followup.send(embed=empty_embed, ephemeral=True)
                return

            # Criar embed com lista de anotações
            list_embed: discord.Embed = discord.Embed(
                title=f"📋 **ANOTAÇÕES - {usuario.display_name}**",
                description=f"Total: {len(notes)} anotação{'s' if len(notes) != 1 else ''}",
                color=0x4A90E2,
                timestamp=datetime.now(),
            )

            # Agrupar por categoria para estatísticas
            category_stats: dict[str, int] = {}
            severity_stats: dict[str, int] = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}

            for note in notes:
                cat: str = note["category"]
                sev: str = str(note["severity"])

                category_stats[cat] = category_stats.get(cat, 0) + 1
                severity_stats[sev] += 1

            # Mostrar estatísticas
            if len(notes) <= 10:
                # Mostrar todas as anotações se forem poucas
                for i, note in enumerate(notes[:10], 1):
                    created_date: datetime = datetime.fromisoformat(note["created_at"])
                    moderator: discord.Member | None = interaction.guild.get_member(int(note["moderator_id"]))  # type: ignore
                    moderator_name: str = (
                        moderator.display_name if moderator else "Moderador não encontrado"
                    )

                    cat_info: dict[str, Any] = self.categories.get(note["category"], self.categories["other"])
                    severity_emoji: str = (
                        "🟢" if note["severity"] <= 2 else "🟡" if note["severity"] <= 3 else "🔴"
                    )

                    note_value: str = f"**{note['title']}**\n"
                    note_value += (
                        f"{note['content'][:100]}{'...' if len(note['content']) > 100 else ''}\n"
                    )
                    note_value += (
                        f"👮 {moderator_name} • {created_date.strftime('%d/%m/%Y %H:%M')}\n"
                    )
                    note_value += f"{cat_info['emoji']} {cat_info['name']} • {severity_emoji} Sev. {note['severity']}"

                    list_embed.add_field(name=f"📝 Anotação #{i}", value=note_value, inline=False)
            else:
                # Mostrar resumo se forem muitas
                recent_notes: list[dict[str, Any]] = notes[:5]
                for i, note in enumerate(recent_notes, 1):
                    created_date_recent: datetime = datetime.fromisoformat(note["created_at"])
                    cat_info_recent: dict[str, Any] = self.categories.get(note["category"], self.categories["other"])

                    note_value_recent: str = f"**{note['title']}** - {cat_info_recent['emoji']} {cat_info_recent['name']}\n"
                    note_value_recent += f"{created_date_recent.strftime('%d/%m/%Y %H:%M')}"

                    list_embed.add_field(name=f"📝 Recente #{i}", value=note_value_recent, inline=True)

                if len(notes) > 5:
                    list_embed.add_field(
                        name="➕ Mais Anotações",
                        value=f"... e mais {len(notes) - 5} anotações\nUse `/note-search` para buscar específicas",
                        inline=False,
                    )

            # Estatísticas por categoria
            if category_stats:
                stats_text: str = ""
                for cat, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[
                    :5
                ]:
                    cat_info_stat: dict[str, Any] = self.categories.get(cat, self.categories["other"])
                    stats_text += f"{cat_info_stat['emoji']} **{cat_info_stat['name']}:** {count}\n"

                list_embed.add_field(name="📊 Por Categoria", value=stats_text, inline=True)

            # Estatísticas por severidade
            severity_text: str = ""
            for sev in ["5", "4", "3", "2", "1"]:
                if severity_stats[sev] > 0:
                    emoji: str = "🔴" if sev in ["4", "5"] else "🟡" if sev == "3" else "🟢"
                    severity_text += f"{emoji} **Nível {sev}:** {severity_stats[sev]}\n"

            if severity_text:
                list_embed.add_field(name="⚡ Por Severidade", value=severity_text, inline=True)

            list_embed.set_thumbnail(url=usuario.display_avatar.url)
            list_embed.set_footer(
                text=f"Consultado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=list_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando note-list: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao buscar lista de anotações.", ephemeral=True
                )
            except Exception:
                pass

    @app_commands.command(name="note-search", description="🔍 Buscar anotações por palavra-chave")
    @app_commands.describe(
        palavra_chave="Palavra-chave para buscar",
        usuario="Buscar apenas anotações de um usuário específico",
        categoria="Filtrar por categoria",
    )
    async def note_search(
        self,
        interaction: discord.Interaction,
        palavra_chave: str,
        usuario: discord.Member | None = None,
        categoria: str | None = None,
    ) -> None:
        try:
            if not interaction.user.guild_permissions.manage_messages:  # type: ignore
                await interaction.response.send_message(
                    "❌ Você não tem permissão para buscar anotações.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar anotações
            try:
                from ...utils.database import database

                query_search: str = """SELECT * FROM user_notes 
                          WHERE guild_id = ? AND active = 1 
                          AND (title LIKE ? OR content LIKE ?)"""
                params_search: list[str] = [str(interaction.guild.id), f"%{palavra_chave}%", f"%{palavra_chave}%"]  # type: ignore

                if usuario:
                    query_search += " AND user_id = ?"
                    params_search.append(str(usuario.id))

                if categoria:
                    query_search += " AND category = ?"
                    params_search.append(categoria.lower())

                query_search += " ORDER BY created_at DESC LIMIT 20"

                results: list[dict[str, Any]] = await database.get_all(query_search, params_search)

            except Exception as e:
                print(f"❌ Erro na busca: {e}")
                await interaction.followup.send(
                    "❌ Erro ao executar busca no banco de dados.", ephemeral=True
                )
                return

            if not results:
                search_embed: discord.Embed = discord.Embed(
                    title="🔍 **BUSCA SEM RESULTADOS**",
                    description=f"Nenhuma anotação encontrada com a palavra-chave: **{palavra_chave}**",
                    color=0xFF6B6B,
                    timestamp=datetime.now(),
                )

                search_embed.add_field(
                    name="💡 Dicas de Busca",
                    value="• Use palavras-chave mais gerais\n"
                    "• Verifique a ortografia\n"
                    "• Tente buscar sem filtros de usuário/categoria\n"
                    "• Lembre-se que a busca é apenas em anotações ativas",
                    inline=False,
                )

                await interaction.followup.send(embed=search_embed, ephemeral=True)
                return

            # Criar embed com resultados
            search_result_embed: discord.Embed = discord.Embed(
                title="🔍 **RESULTADOS DA BUSCA**",
                description=f"Palavra-chave: **{palavra_chave}**\nEncontrados: **{len(results)}** resultado{'s' if len(results) != 1 else ''}",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            # Mostrar resultados (máximo 8 para não ficar muito grande)
            for i, note in enumerate(results[:8], 1):
                target_user: discord.Member | None = interaction.guild.get_member(int(note["user_id"]))  # type: ignore
                moderator_search: discord.Member | None = interaction.guild.get_member(int(note["moderator_id"]))  # type: ignore
                created_date_search: datetime = datetime.fromisoformat(note["created_at"])

                user_name: str = target_user.display_name if target_user else "Usuário não encontrado"
                mod_name: str = moderator_search.display_name if moderator_search else "Moderador desconhecido"

                cat_info_search: dict[str, Any] = self.categories.get(note["category"], self.categories["other"])
                severity_emoji_search: str = (
                    "🟢" if note["severity"] <= 2 else "🟡" if note["severity"] <= 3 else "🔴"
                )

                # Destacar palavra-chave no texto
                title_search: str = note["title"]
                content_search: str = note["content"][:150]

                # Simples highlight (case-insensitive)
                import re

                pattern: re.Pattern[str] = re.compile(re.escape(palavra_chave), re.IGNORECASE)
                title_search = pattern.sub(f"**{palavra_chave.upper()}**", title_search)
                content_search = pattern.sub(f"**{palavra_chave.upper()}**", content_search)

                result_text: str = f"**{title_search}**\n"
                result_text += f"{content_search}{'...' if len(note['content']) > 150 else ''}\n"
                result_text += f"👤 {user_name} • 👮 {mod_name}\n"
                result_text += f"📅 {created_date_search.strftime('%d/%m/%Y %H:%M')} • "
                result_text += f"{cat_info_search['emoji']} {cat_info_search['name']} • {severity_emoji_search} Sev.{note['severity']}"

                search_result_embed.add_field(name=f"📝 Resultado #{i}", value=result_text, inline=False)

            if len(results) > 8:
                search_result_embed.add_field(
                    name="➕ Mais Resultados",
                    value=f"... e mais {len(results) - 8} resultados encontrados.\n"
                    f"Refine sua busca para ver resultados mais específicos.",
                    inline=False,
                )

            search_result_embed.set_footer(
                text=f"Busca realizada por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=search_result_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando note-search: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao executar busca de anotações.", ephemeral=True
                )
            except Exception:
                pass


def setup(bot: commands.Bot) -> None:
    """Adiciona o cog ao bot"""
    bot.add_cog(NotesCreation(bot))
