"""
Sistema de Autorole - Gerenciamento e Lista
Gerenciamento completo de regras de autorole
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class AutoroleManagement(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(name="autorole-list", description="📋 Listar regras de autorole")
    @app_commands.describe(status="Filtrar por status das regras")
    async def autorole_list(
        self, interaction: discord.Interaction, status: str | None = None
    ) -> None:
        try:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para ver regras de autorole.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar regras
            try:
                from ...utils.database import database

                query: str = "SELECT * FROM autorole_rules WHERE guild_id = ?"
                params: list[str] = [str(interaction.guild.id)]

                if status:
                    if status.lower() in ["ativa", "ativo", "enabled"]:
                        query += " AND enabled = 1"
                    elif status.lower() in ["desativa", "desativo", "disabled"]:
                        query += " AND enabled = 0"

                query += " ORDER BY created_at DESC"

                rules: Any = await database.get_all(query, params)

            except Exception as e:
                print(f"❌ Erro ao buscar regras: {e}")
                await interaction.followup.send(
                    "❌ Erro ao consultar regras de autorole.", ephemeral=True
                )
                return

            if not rules:
                filter_text: str = f" ({status})" if status else ""
                empty_embed: discord.Embed = discord.Embed(
                    title="📋 **REGRAS DE AUTOROLE**",
                    description=f"Nenhuma regra de autorole encontrada{filter_text}.",
                    color=0x2F3136,
                    timestamp=datetime.now(),
                )

                empty_embed.add_field(
                    name="💡 Como Criar uma Regra",
                    value="Use `/autorole-setup` para criar sua primeira regra de autorole.\n"
                    "As regras podem ser baseadas em:\n"
                    "• Entrada no servidor\n"
                    "• Boost no servidor\n"
                    "• Reações em mensagens\n"
                    "• Tempo no servidor\n"
                    "• Ganhar roles específicas",
                    inline=False,
                )

                await interaction.followup.send(embed=empty_embed, ephemeral=True)
                return

            # Criar embed com lista
            list_embed: discord.Embed = discord.Embed(
                title="📋 **REGRAS DE AUTOROLE**",
                description=f"Total: {len(rules)} regra{'s' if len(rules) != 1 else ''}",
                color=0x4A90E2,
                timestamp=datetime.now(),
            )

            # Estatísticas rápidas
            active_count: int = sum(1 for rule in rules if rule["enabled"])
            inactive_count: int = len(rules) - active_count

            list_embed.add_field(
                name="📊 Estatísticas",
                value=f"✅ **Ativas:** {active_count}\n❌ **Inativas:** {inactive_count}",
                inline=True,
            )

            # Mostrar regras (máximo 8 por página)
            display_rules: Any = rules[:8]

            for i, rule in enumerate(display_rules, 1):
                rule_data: dict[str, Any] = json.loads(rule["rule_data"])
                created_date: datetime = datetime.fromisoformat(rule["created_at"])

                # Status da regra
                status_emoji: str = "✅" if rule["enabled"] else "❌"
                status_text: str = "Ativa" if rule["enabled"] else "Inativa"

                # Condições resumidas
                conditions: list[dict[str, Any]] = rule_data.get("conditions", [])
                condition_summary: list[str] = []
                for condition in conditions[:3]:  # Máximo 3 condições mostradas
                    cond_type: str = condition.get("type", "unknown")
                    condition_summary.append(cond_type)

                conditions_text: str = ", ".join(condition_summary)
                if len(conditions) > 3:
                    conditions_text += f" + {len(conditions) - 3} mais"

                # Roles configuradas
                roles_add: list[str] = rule_data.get("roles_to_add", [])
                roles_remove: list[str] = rule_data.get("roles_to_remove", [])
                roles_count: int = len(roles_add) + len(roles_remove)

                rule_info: str = f"**ID:** `{rule['rule_id'][:16]}...`\n"
                rule_info += f"**Status:** {status_emoji} {status_text}\n"
                rule_info += f"**Condições:** {conditions_text}\n"
                rule_info += (
                    f"**Roles:** {roles_count} configurada{'s' if roles_count != 1 else ''}\n"
                )
                rule_info += f"**Criada:** {created_date.strftime('%d/%m/%Y')}\n"
                rule_info += f"**Uso:** {rule_data.get('usage_count', 0)} vezes"

                list_embed.add_field(
                    name=f"{status_emoji} {rule['rule_name']}", value=rule_info, inline=True
                )

            if len(rules) > 8:
                list_embed.add_field(
                    name="➕ Mais Regras",
                    value=f"... e mais {len(rules) - 8} regras.\nUse filtros para refinar a busca.",
                    inline=False,
                )

            # Comandos úteis
            list_embed.add_field(
                name="💡 Comandos Úteis",
                value="`/autorole-info <id>` - Ver detalhes\n"
                "`/autorole-toggle <id>` - Ativar/desativar\n"
                "`/autorole-delete <id>` - Remover regra\n"
                "`/autorole-test <id>` - Testar regra",
                inline=False,
            )

            list_embed.set_footer(
                text=f"Consultado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=list_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando autorole-list: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao listar regras de autorole.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(
        name="autorole-info", description="ℹ️ Ver detalhes de uma regra de autorole"
    )
    @app_commands.describe(rule_id="ID da regra para ver detalhes")
    async def autorole_info(self, interaction: discord.Interaction, rule_id: str) -> None:
        try:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para ver detalhes das regras.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar regra
            try:
                from ...utils.database import database

                rule: Any = await database.get(
                    "SELECT * FROM autorole_rules WHERE guild_id = ? AND rule_id LIKE ?",
                    (str(interaction.guild.id), f"{rule_id}%"),
                )

                if not rule:
                    await interaction.followup.send(
                        f"❌ **Regra não encontrada**\n"
                        f"Nenhuma regra encontrada com ID: `{rule_id}`",
                        ephemeral=True,
                    )
                    return

                rule_data: dict[str, Any] = json.loads(rule["rule_data"])

            except Exception as e:
                print(f"❌ Erro ao buscar regra: {e}")
                await interaction.followup.send("❌ Erro ao consultar regra.", ephemeral=True)
                return

            # Criar embed detalhado
            created_date: datetime = datetime.fromisoformat(rule["created_at"])
            creator: discord.Member | None = interaction.guild.get_member(int(rule["created_by"]))
            creator_name: str = creator.display_name if creator else "Usuário não encontrado"

            status_emoji: str = "✅" if rule["enabled"] else "❌"
            status_text: str = "Ativa" if rule["enabled"] else "Inativa"
            status_color: int = 0x00FF00 if rule["enabled"] else 0xFF6B6B

            info_embed: discord.Embed = discord.Embed(
                title="ℹ️ **DETALHES DA REGRA**",
                description=f"**{rule['rule_name']}**",
                color=status_color,
                timestamp=created_date,
            )

            # Informações básicas
            info_embed.add_field(
                name="📋 Informações Básicas",
                value=f"**Status:** {status_emoji} {status_text}\n"
                f"**ID:** `{rule['rule_id'][:20]}...`\n"
                f"**Criador:** {creator_name}\n"
                f"**Criada:** {created_date.strftime('%d/%m/%Y às %H:%M')}\n"
                f"**Usos:** {rule_data.get('usage_count', 0)} vezes",
                inline=True,
            )

            # Descrição se houver
            description: str = rule_data.get("description", "").strip()
            if description:
                info_embed.add_field(name="📝 Descrição", value=description, inline=False)

            # Condições detalhadas
            conditions: list[dict[str, Any]] = rule_data.get("conditions", [])
            if conditions:
                conditions_text: str = ""
                for i, condition in enumerate(conditions, 1):
                    cond_desc: str = condition.get("description", "Condição desconhecida")
                    cond_value: str = condition.get("value", "")

                    if cond_value:
                        conditions_text += f"{i}. {cond_desc} - `{cond_value}`\n"
                    else:
                        conditions_text += f"{i}. {cond_desc}\n"

                info_embed.add_field(
                    name="🔧 Condições Configuradas", value=conditions_text, inline=False
                )

            # Roles para adicionar
            roles_add: list[str] = rule_data.get("roles_to_add", [])
            if roles_add:
                add_text: str = ""
                for role_id in roles_add:
                    role: discord.Role | None = interaction.guild.get_role(int(role_id))
                    if role:
                        add_text += f"• {role.mention}\n"
                    else:
                        add_text += f"• Role não encontrada (`{role_id}`)\n"

                info_embed.add_field(
                    name="🏷️ Roles para Adicionar",
                    value=add_text or "Nenhuma configurada",
                    inline=True,
                )

            # Roles para remover
            roles_remove: list[str] = rule_data.get("roles_to_remove", [])
            if roles_remove:
                remove_text: str = ""
                for role_id in roles_remove:
                    role = interaction.guild.get_role(int(role_id))
                    if role:
                        remove_text += f"• {role.mention}\n"
                    else:
                        remove_text += f"• Role não encontrada (`{role_id}`)\n"

                info_embed.add_field(
                    name="🗑️ Roles para Remover",
                    value=remove_text or "Nenhuma configurada",
                    inline=True,
                )

            # Se não há roles configuradas
            if not roles_add and not roles_remove:
                info_embed.add_field(
                    name="⚠️ Configuração Incompleta",
                    value="Nenhuma role configurada para esta regra.\n"
                    f"Use `/autorole-roles {rule_id}` para configurar.",
                    inline=False,
                )

            # Comandos de gerenciamento
            management_text: str = f"`/autorole-toggle {rule_id[:8]}` - {'Desativar' if rule['enabled'] else 'Ativar'}\n"
            management_text += f"`/autorole-roles {rule_id[:8]}` - Configurar roles\n"
            management_text += f"`/autorole-test {rule_id[:8]}` - Testar regra\n"
            management_text += f"`/autorole-delete {rule_id[:8]}` - Excluir regra"

            info_embed.add_field(name="🔧 Gerenciamento", value=management_text, inline=False)

            info_embed.set_footer(
                text=f"Consultado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=info_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando autorole-info: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao consultar detalhes da regra.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(
        name="autorole-toggle", description="🔄 Ativar/desativar regra de autorole"
    )
    @app_commands.describe(rule_id="ID da regra para ativar/desativar")
    async def autorole_toggle(self, interaction: discord.Interaction, rule_id: str) -> None:
        try:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para ativar/desativar regras.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar regra
            try:
                from ...utils.database import database

                rule: Any = await database.get(
                    "SELECT * FROM autorole_rules WHERE guild_id = ? AND rule_id LIKE ?",
                    (str(interaction.guild.id), f"{rule_id}%"),
                )

                if not rule:
                    await interaction.followup.send(
                        f"❌ Regra não encontrada com ID: `{rule_id}`", ephemeral=True
                    )
                    return

                rule_data: dict[str, Any] = json.loads(rule["rule_data"])

            except Exception as e:
                print(f"❌ Erro ao buscar regra: {e}")
                await interaction.followup.send("❌ Erro ao consultar regra.", ephemeral=True)
                return

            # Verificar se tem roles configuradas antes de ativar
            roles_add: list[str] = rule_data.get("roles_to_add", [])
            roles_remove: list[str] = rule_data.get("roles_to_remove", [])

            if not rule["enabled"] and not roles_add and not roles_remove:
                await interaction.followup.send(
                    "❌ **Não é possível ativar a regra**\n"
                    "Esta regra não tem roles configuradas.\n"
                    f"Configure as roles primeiro: `/autorole-roles {rule_id}`",
                    ephemeral=True,
                )
                return

            # Alternar status
            new_status: bool = not rule["enabled"]

            try:
                await database.execute(
                    "UPDATE autorole_rules SET enabled = ? WHERE rule_id = ?",
                    (1 if new_status else 0, rule["rule_id"]),
                )
            except Exception as e:
                print(f"❌ Erro ao alterar status: {e}")
                await interaction.followup.send(
                    "❌ Erro ao alterar status da regra.", ephemeral=True
                )
                return

            # Embed de confirmação
            action_text: str = "ativada" if new_status else "desativada"
            action_emoji: str = "✅" if new_status else "❌"
            action_color: int = 0x00FF00 if new_status else 0xFF6B6B

            toggle_embed: discord.Embed = discord.Embed(
                title=f"{action_emoji} **REGRA {action_text.upper()}**",
                description=f"A regra `{rule['rule_name']}` foi **{action_text}**!",
                color=action_color,
                timestamp=datetime.now(),
            )

            toggle_embed.add_field(
                name="📝 Regra",
                value=f"**Nome:** {rule['rule_name']}\n"
                f"**ID:** `{rule['rule_id'][:16]}...`\n"
                f"**Status:** {action_emoji} {action_text.title()}",
                inline=True,
            )

            # Mostrar efeito da mudança
            effect_text: str
            if new_status:
                effect_text = "• A regra agora irá aplicar automaticamente\n"
                effect_text += "• Usuários que atenderem as condições receberão as roles\n"
                effect_text += "• Verifique os logs para monitorar a atividade"
            else:
                effect_text = "• A regra não será mais aplicada automaticamente\n"
                effect_text += "• Roles existentes não serão alteradas\n"
                effect_text += "• Para reativar, use o mesmo comando novamente"

            toggle_embed.add_field(name="📊 Efeito da Alteração", value=effect_text, inline=False)

            # Mostrar configuração atual da regra
            conditions: list[dict[str, Any]] = rule_data.get("conditions", [])
            if conditions:
                cond_summary: list[str] = [cond.get("type", "unknown") for cond in conditions[:3]]
                conditions_text: str = ", ".join(cond_summary)
                if len(conditions) > 3:
                    conditions_text += f" + {len(conditions) - 3} mais"

                toggle_embed.add_field(name="🔧 Condições", value=conditions_text, inline=True)

            roles_count: int = len(roles_add) + len(roles_remove)
            if roles_count > 0:
                roles_text: str = f"{len(roles_add)} para adicionar, {len(roles_remove)} para remover"
                toggle_embed.add_field(name="🏷️ Roles", value=roles_text, inline=True)

            toggle_embed.set_footer(
                text=f"Alterado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=toggle_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando autorole-toggle: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao alterar status da regra.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="autorole-delete", description="🗑️ Excluir regra de autorole")
    @app_commands.describe(
        rule_id="ID da regra para excluir", confirmar="Digite 'sim' para confirmar a exclusão"
    )
    async def autorole_delete(
        self, interaction: discord.Interaction, rule_id: str, confirmar: str
    ) -> None:
        try:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para excluir regras.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Verificar confirmação
            if confirmar.lower() != "sim":
                await interaction.followup.send(
                    "❌ **Exclusão cancelada**\n"
                    f"Para confirmar a exclusão, use: `/autorole-delete {rule_id} confirmar:sim`",
                    ephemeral=True,
                )
                return

            # Buscar e excluir regra
            try:
                from ...utils.database import database

                rule: Any = await database.get(
                    "SELECT * FROM autorole_rules WHERE guild_id = ? AND rule_id LIKE ?",
                    (str(interaction.guild.id), f"{rule_id}%"),
                )

                if not rule:
                    await interaction.followup.send(
                        f"❌ Regra não encontrada com ID: `{rule_id}`", ephemeral=True
                    )
                    return

                # Excluir regra
                await database.execute(
                    "DELETE FROM autorole_rules WHERE rule_id = ?", (rule["rule_id"],)
                )

            except Exception as e:
                print(f"❌ Erro ao excluir regra: {e}")
                await interaction.followup.send("❌ Erro ao excluir regra.", ephemeral=True)
                return

            # Embed de confirmação
            delete_embed: discord.Embed = discord.Embed(
                title="🗑️ **REGRA EXCLUÍDA**",
                description=f"A regra `{rule['rule_name']}` foi excluída permanentemente!",
                color=0x8B0000,
                timestamp=datetime.now(),
            )

            delete_embed.add_field(
                name="📝 Regra Excluída",
                value=f"**Nome:** {rule['rule_name']}\n"
                f"**ID:** `{rule['rule_id'][:16]}...`\n"
                f"**Era ativa:** {'Sim' if rule['enabled'] else 'Não'}",
                inline=True,
            )

            delete_embed.add_field(
                name="⚠️ **ATENÇÃO**",
                value="• Esta ação é **irreversível**\n"
                "• A regra foi **permanentemente removida**\n"
                "• Roles já aplicadas **não são afetadas**\n"
                "• Crie uma nova regra se necessário",
                inline=False,
            )

            delete_embed.set_footer(
                text=f"Excluída por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=delete_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando autorole-delete: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao processar exclusão da regra.", ephemeral=True
                )
            except:
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoroleManagement(bot))
