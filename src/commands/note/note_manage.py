"""
Sistema de Notes - Gerenciamento e Edição de Anotações
Edição, remoção e gerenciamento avançado de anotações
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class NoteEditModal(discord.ui.Modal):
    """Modal para editar anotações"""

    def __init__(self, note_data: dict[str, Any], moderator: discord.Member) -> None:
        super().__init__(
            title=f"✏️ Editar Anotação - ID: {note_data['note_id'][:8]}...", timeout=300
        )
        self.note_data: dict[str, Any] = note_data
        self.moderator: discord.Member = moderator

        # Campo para o título
        self.note_title = discord.ui.TextInput(
            label="Título da Anotação",
            placeholder="Título da anotação...",
            required=True,
            max_length=100,
            default=note_data["title"],
        )

        # Campo para o conteúdo
        self.note_content = discord.ui.TextInput(
            label="Conteúdo da Anotação",
            placeholder="Conteúdo detalhado...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
            default=note_data["content"],
        )

        # Campo para categoria
        self.note_category = discord.ui.TextInput(
            label="Categoria",
            placeholder="Ex: warning, info, positive, negative",
            required=False,
            max_length=50,
            default=note_data.get("category", "info"),
        )

        # Campo para severidade
        self.note_severity = discord.ui.TextInput(
            label="Severidade (1-5)",
            placeholder="1 = Leve, 5 = Grave",
            required=False,
            max_length=1,
            default=str(note_data.get("severity", 3)),
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

            # Atualizar no banco de dados
            try:
                from ...utils.database import database

                # Registrar edição no histórico
                edit_history: dict[str, Any] = {
                    "edited_by": str(self.moderator.id),
                    "edited_at": datetime.now().isoformat(),
                    "changes": {
                        "title": {"old": self.note_data["title"], "new": self.note_title.value},
                        "content": {
                            "old": self.note_data["content"],
                            "new": self.note_content.value,
                        },
                        "category": {
                            "old": self.note_data.get("category", "info"),
                            "new": self.note_category.value.lower(),
                        },
                        "severity": {"old": self.note_data.get("severity", 3), "new": severity},
                    },
                }

                await database.execute(
                    """UPDATE user_notes 
                    SET title = ?, content = ?, category = ?, severity = ?, 
                        updated_at = ?, updated_by = ?
                    WHERE note_id = ?""",
                    (
                        self.note_title.value,
                        self.note_content.value,
                        self.note_category.value.lower(),
                        severity,
                        datetime.now().isoformat(),
                        str(self.moderator.id),
                        self.note_data["note_id"],
                    ),
                )

                # Salvar histórico de edição
                await database.execute(
                    """INSERT INTO note_edit_history 
                    (note_id, edit_data, created_at) VALUES (?, ?, ?)""",
                    (
                        self.note_data["note_id"],
                        json.dumps(edit_history),
                        datetime.now().isoformat(),
                    ),
                )

            except Exception as e:
                print(f"❌ Erro ao atualizar anotação: {e}")
                await interaction.followup.send(
                    "❌ Erro ao salvar alterações da anotação.", ephemeral=True
                )
                return

            # Embed de confirmação
            edit_embed: discord.Embed = discord.Embed(
                title="✅ **ANOTAÇÃO EDITADA**",
                description=f"Anotação `{self.note_data['note_id'][:16]}...` foi atualizada!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            # Mostrar mudanças
            changes_made: list[str] = []
            if self.note_data["title"] != self.note_title.value:
                changes_made.append(
                    f"**Título:** `{self.note_data['title']}` → `{self.note_title.value}`"
                )

            if self.note_data["content"] != self.note_content.value:
                old_preview: str = (
                    self.note_data["content"][:50] + "..."
                    if len(self.note_data["content"]) > 50
                    else self.note_data["content"]
                )
                new_preview: str = (
                    self.note_content.value[:50] + "..."
                    if len(self.note_content.value) > 50
                    else self.note_content.value
                )
                changes_made.append("**Conteúdo alterado**")

            if self.note_data.get("category", "info") != self.note_category.value.lower():
                changes_made.append(
                    f"**Categoria:** `{self.note_data.get('category', 'info')}` → `{self.note_category.value.lower()}`"
                )

            if self.note_data.get("severity", 3) != severity:
                changes_made.append(
                    f"**Severidade:** `{self.note_data.get('severity', 3)}` → `{severity}`"
                )

            if changes_made:
                edit_embed.add_field(
                    name="🔄 Alterações Realizadas", value="\n".join(changes_made), inline=False
                )
            else:
                edit_embed.add_field(
                    name="ℹ️ Nenhuma Alteração",
                    value="Os dados permaneceram os mesmos.",
                    inline=False,
                )

            edit_embed.add_field(name="✏️ Editado por", value=self.moderator.mention, inline=True)

            edit_embed.add_field(
                name="📅 Data da Edição",
                value=datetime.now().strftime("%d/%m/%Y às %H:%M"),
                inline=True,
            )

            edit_embed.set_footer(text=f"ID da Anotação: {self.note_data['note_id'][:16]}...")

            await interaction.followup.send(embed=edit_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no modal de edição: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao processar edição da anotação.", ephemeral=True
                )
            except Exception:
                pass


class NotesManagement(commands.Cog):
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

    @app_commands.command(name="note-edit", description="✏️ Editar uma anotação existente")
    @app_commands.describe(note_id="ID da anotação para editar (primeiros caracteres suficientes)")
    async def note_edit(self, interaction: discord.Interaction, note_id: str) -> None:
        try:
            if not interaction.user.guild_permissions.manage_messages:  # type: ignore
                await interaction.response.send_message(
                    "❌ Você não tem permissão para editar anotações.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar anotação
            try:
                from ...utils.database import database

                # Buscar por ID parcial ou completo
                note: dict[str, Any] | None = await database.get(
                    "SELECT * FROM user_notes WHERE guild_id = ? AND note_id LIKE ? AND active = 1",
                    (str(interaction.guild.id), f"{note_id}%"),  # type: ignore
                )

                if not note:
                    await interaction.followup.send(
                        f"❌ **Anotação não encontrada**\n"
                        f"Nenhuma anotação ativa encontrada com ID: `{note_id}`\n\n"
                        f"💡 **Dicas:**\n"
                        f"• Use `/note-list @usuário` para ver IDs das anotações\n"
                        f"• Apenas os primeiros caracteres do ID são necessários\n"
                        f"• Certifique-se de que a anotação não foi removida",
                        ephemeral=True,
                    )
                    return

            except Exception as e:
                print(f"❌ Erro ao buscar anotação: {e}")
                await interaction.followup.send(
                    "❌ Erro ao buscar anotação no banco de dados.", ephemeral=True
                )
                return

            # Verificar se o usuário pode editar (moderador original ou admin)
            can_edit: bool = (
                str(interaction.user.id) == note["moderator_id"]
                or interaction.user.guild_permissions.administrator  # type: ignore
            )

            if not can_edit:
                original_mod: discord.Member | None = interaction.guild.get_member(int(note["moderator_id"]))  # type: ignore
                mod_name: str = original_mod.display_name if original_mod else "Moderador desconhecido"

                await interaction.followup.send(
                    f"❌ **Sem permissão para editar**\n"
                    f"Apenas o moderador que criou a anotação ou administradores podem editá-la.\n"
                    f"**Criada por:** {mod_name}",
                    ephemeral=True,
                )
                return

            # Abrir modal de edição
            modal: NoteEditModal = NoteEditModal(note, interaction.user)  # type: ignore
            await interaction.response.send_modal(modal)

        except discord.InteractionResponded:
            # Modal já foi enviado
            pass
        except Exception as e:
            print(f"❌ Erro no comando note-edit: {e}")
            try:
                await interaction.followup.send("❌ Erro ao editar anotação.", ephemeral=True)
            except Exception:
                pass

    @app_commands.command(name="note-delete", description="🗑️ Remover uma anotação")
    @app_commands.describe(
        note_id="ID da anotação para remover",
        permanente="Se deve ser removida permanentemente (padrão: apenas desativar)",
    )
    async def note_delete(
        self, interaction: discord.Interaction, note_id: str, permanente: bool | None = False
    ) -> None:
        try:
            if not interaction.user.guild_permissions.manage_messages:  # type: ignore
                await interaction.response.send_message(
                    "❌ Você não tem permissão para remover anotações.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar anotação
            try:
                from ...utils.database import database

                note_del: dict[str, Any] | None = await database.get(
                    "SELECT * FROM user_notes WHERE guild_id = ? AND note_id LIKE ? AND active = 1",
                    (str(interaction.guild.id), f"{note_id}%"),  # type: ignore
                )

                if not note_del:
                    await interaction.followup.send(
                        f"❌ Anotação não encontrada com ID: `{note_id}`", ephemeral=True
                    )
                    return

            except Exception as e:
                print(f"❌ Erro ao buscar anotação: {e}")
                await interaction.followup.send("❌ Erro ao buscar anotação.", ephemeral=True)
                return

            # Verificar permissão
            can_delete: bool = (
                str(interaction.user.id) == note_del["moderator_id"]
                or interaction.user.guild_permissions.administrator  # type: ignore
            )

            if not can_delete:
                await interaction.followup.send(
                    "❌ Você só pode remover suas próprias anotações (ou ser administrador).",
                    ephemeral=True,
                )
                return

            # Executar remoção
            try:
                action_text: str
                action_color: int
                if permanente and interaction.user.guild_permissions.administrator:  # type: ignore
                    # Remoção permanente (apenas admins)
                    await database.execute(
                        "DELETE FROM user_notes WHERE note_id = ?", (note_del["note_id"],)
                    )

                    # Remover histórico também
                    await database.execute(
                        "DELETE FROM note_edit_history WHERE note_id = ?", (note_del["note_id"],)
                    )

                    action_text = "**removida permanentemente**"
                    action_color = 0x8B0000
                else:
                    # Apenas desativar
                    await database.execute(
                        """UPDATE user_notes 
                        SET active = 0, deleted_at = ?, deleted_by = ?
                        WHERE note_id = ?""",
                        (datetime.now().isoformat(), str(interaction.user.id), note_del["note_id"]),
                    )

                    action_text = "**desativada**"
                    action_color = 0xFFA500

            except Exception as e:
                print(f"❌ Erro ao remover anotação: {e}")
                await interaction.followup.send(
                    "❌ Erro ao executar remoção da anotação.", ephemeral=True
                )
                return

            # Buscar informações do usuário
            target_user_del: discord.Member | None = interaction.guild.get_member(int(note_del["user_id"]))  # type: ignore
            user_name_del: str = target_user_del.display_name if target_user_del else "Usuário não encontrado"

            # Embed de confirmação
            delete_embed: discord.Embed = discord.Embed(
                title="🗑️ **ANOTAÇÃO REMOVIDA**",
                description=f"A anotação foi {action_text} com sucesso!",
                color=action_color,
                timestamp=datetime.now(),
            )

            delete_embed.add_field(
                name="📝 Anotação Removida",
                value=f"**Título:** {note_del['title']}\n"
                f"**Usuário:** {user_name_del}\n"
                f"**ID:** `{note_del['note_id'][:16]}...`",
                inline=False,
            )

            delete_embed.add_field(
                name="👮 Removida por", value=interaction.user.mention, inline=True
            )

            delete_embed.add_field(
                name="🔄 Tipo de Remoção",
                value="Permanente" if permanente else "Desativada",
                inline=True,
            )

            if not permanente:
                delete_embed.add_field(
                    name="ℹ️ Importante",
                    value="A anotação foi apenas desativada e pode ser reativada por administradores.",
                    inline=False,
                )

            delete_embed.set_footer(
                text=f"Ação executada em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
            )

            await interaction.followup.send(embed=delete_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando note-delete: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao processar remoção da anotação.", ephemeral=True
                )
            except Exception:
                pass

    @app_commands.command(name="note-stats", description="📊 Estatísticas de anotações do servidor")
    @app_commands.describe(
        periodo="Período para estatísticas", moderador="Ver estatísticas de um moderador específico"
    )
    async def note_stats(
        self,
        interaction: discord.Interaction,
        periodo: str | None = "mes",
        moderador: discord.Member | None = None,
    ) -> None:
        try:
            if not interaction.user.guild_permissions.manage_guild:  # type: ignore
                await interaction.response.send_message(
                    "❌ Você não tem permissão para ver estatísticas de anotações.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Calcular período
            now: datetime = datetime.now()
            start_date: datetime
            if periodo and periodo.lower() in ["hoje", "today"]:
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif periodo and periodo.lower() in ["semana", "week"]:
                start_date = now - timedelta(days=7)
            elif periodo and periodo.lower() in ["mes", "month"]:
                start_date = now - timedelta(days=30)
            elif periodo and periodo.lower() in ["ano", "year"]:
                start_date = now - timedelta(days=365)
            else:
                start_date = now - timedelta(days=30)

            # Buscar estatísticas
            try:
                from ...utils.database import database

                query_stats: str = """
                SELECT 
                    COUNT(*) as total_notes,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT moderator_id) as moderators_involved,
                    category,
                    AVG(severity) as avg_severity,
                    moderator_id
                FROM user_notes 
                WHERE guild_id = ? AND created_at >= ?
                """
                params_stats: list[str] = [str(interaction.guild.id), start_date.isoformat()]  # type: ignore

                if moderador:
                    query_stats += " AND moderator_id = ?"
                    params_stats.append(str(moderador.id))

                query_stats += " AND active = 1 GROUP BY category, moderator_id"

                stats_data: list[dict[str, Any]] = await database.get_all(query_stats, params_stats)

                # Query para totais gerais
                general_query: str = """
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT user_id) as users,
                    COUNT(DISTINCT moderator_id) as mods
                FROM user_notes 
                WHERE guild_id = ? AND created_at >= ? AND active = 1
                """
                general_params: list[str] = [str(interaction.guild.id), start_date.isoformat()]  # type: ignore

                if moderador:
                    general_query += " AND moderator_id = ?"
                    general_params.append(str(moderador.id))

                general_stats: dict[str, Any] | None = await database.get(general_query, general_params)

            except Exception as e:
                print(f"❌ Erro ao buscar estatísticas: {e}")
                await interaction.followup.send(
                    "❌ Erro ao consultar estatísticas.", ephemeral=True
                )
                return

            # Criar embed de estatísticas
            title: str = "📊 **ESTATÍSTICAS DE ANOTAÇÕES**"
            if moderador:
                title += f" - {moderador.display_name}"

            stats_embed: discord.Embed = discord.Embed(
                title=title,
                description=f"Período: {periodo.title() if periodo else 'Mês'} ({start_date.strftime('%d/%m/%Y')} - Hoje)",
                color=0x4A90E2,
                timestamp=datetime.now(),
            )

            if general_stats and general_stats["total"] > 0:
                # Estatísticas gerais
                stats_embed.add_field(
                    name="📈 Resumo Geral",
                    value=f"**Total de Anotações:** {general_stats['total']}\n"
                    f"**Usuários com Anotações:** {general_stats['users']}\n"
                    f"**Moderadores Ativos:** {general_stats['mods']}",
                    inline=True,
                )

                # Estatísticas por categoria
                category_stats: dict[str, int] = {}
                severity_total: float = 0.0
                severity_count: int = 0
                category_stats = {}
                severity_total = 0
                severity_count = 0

                for stat in stats_data:
                    category = stat["category"]
                    if category not in category_stats:
                        category_stats[category] = 0
                    category_stats[category] += 1

                    if stat["avg_severity"]:
                        severity_total += stat["avg_severity"]
                        severity_count += 1

                if category_stats:
                    cat_text = ""
                    for category, count in sorted(
                        category_stats.items(), key=lambda x: x[1], reverse=True
                    ):
                        cat_info = self.categories.get(category, self.categories["other"])
                        percentage = (count / general_stats["total"]) * 100
                        cat_text += f"{cat_info['emoji']} **{cat_info['name']}:** {count} ({percentage:.1f}%)\n"

                    stats_embed.add_field(name="🏷️ Por Categoria", value=cat_text, inline=True)

                # Severidade média
                if severity_count > 0:
                    avg_severity = severity_total / severity_count
                    severity_emoji = (
                        "🟢" if avg_severity <= 2 else "🟡" if avg_severity <= 3 else "🔴"
                    )

                    stats_embed.add_field(
                        name="⚡ Severidade Média",
                        value=f"{severity_emoji} **{avg_severity:.1f}**/5.0\n"
                        f"{'Baixa' if avg_severity <= 2 else 'Moderada' if avg_severity <= 3.5 else 'Alta'}",
                        inline=True,
                    )

                # Top moderadores (se não for filtro específico)
                if not moderador:
                    try:
                        top_mods_query: str = """
                        SELECT moderator_id, COUNT(*) as note_count
                        FROM user_notes
                        WHERE guild_id = ? AND created_at >= ? AND active = 1
                        GROUP BY moderator_id
                        ORDER BY note_count DESC
                        LIMIT 5
                        """

                        top_mods: list[dict[str, Any]] = await database.get_all(
                            top_mods_query, [str(interaction.guild.id), start_date.isoformat()]  # type: ignore
                        )

                        if top_mods:
                            top_text: str = ""
                            for i, mod_data in enumerate(top_mods, 1):
                                mod: discord.Member | None = interaction.guild.get_member(int(mod_data["moderator_id"]))  # type: ignore
                                mod_name_top: str = mod.display_name if mod else "Usuário não encontrado"
                                count_top: int = mod_data["note_count"]

                                medal: str = ["🥇", "🥈", "🥉", "🏅", "📝"][i - 1] if i <= 5 else "📝"
                                top_text += f"{medal} **{mod_name_top}** - {count_top} anotações\n"

                            stats_embed.add_field(
                                name="👮 Top Moderadores", value=top_text, inline=False
                            )
                    except Exception:
                        pass

            else:
                stats_embed.add_field(
                    name="📊 Sem Dados",
                    value=f"Nenhuma anotação encontrada para o período selecionado.\n"
                    f"Período: {periodo.title()}",
                    inline=False,
                )

                stats_embed.add_field(
                    name="💡 Sugestões",
                    value="• Tente um período maior (mês, ano)\n"
                    "• Verifique se há anotações criadas\n"
                    "• Remova filtros de moderador específico",
                    inline=False,
                )

            stats_embed.set_footer(
                text=f"Consultado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=stats_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando note-stats: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao gerar estatísticas de anotações.", ephemeral=True
                )
            except Exception:
                pass


def setup(bot: commands.Bot) -> None:
    """Adiciona o cog ao bot"""
    bot.add_cog(NotesManagement(bot))
