"""
Sistema de Autorole - Roles Automáticas Avançado
Sistema completo de roles automáticas com múltiplas condições e regras
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


class AutoroleSetupModal(discord.ui.Modal):
    """Modal para configurar autorole"""

    def __init__(self, guild: discord.Guild, user: discord.Member) -> None:
        super().__init__(title=f"🤖 Configurar Autorole - {guild.name}", timeout=300)
        self.guild: discord.Guild = guild
        self.user: discord.Member = user

        # Nome da regra
        self.rule_name: discord.ui.TextInput[AutoroleSetupModal] = discord.ui.TextInput(
            label="Nome da Regra",
            placeholder="Ex: Membros Novos, Verificados, etc.",
            required=True,
            max_length=100,
        )

        # Descrição da regra
        self.rule_description: discord.ui.TextInput[AutoroleSetupModal] = discord.ui.TextInput(
            label="Descrição",
            placeholder="Descreva quando esta regra será aplicada...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500,
        )

        # Condições (separadas por vírgula)
        self.rule_conditions: discord.ui.TextInput[AutoroleSetupModal] = discord.ui.TextInput(
            label="Condições (separadas por vírgula)",
            placeholder="join,boost,react:emoji_id,time:30m,role:role_id",
            required=True,
            max_length=300,
        )

        self.add_item(self.rule_name)
        self.add_item(self.rule_description)
        self.add_item(self.rule_conditions)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # Processar condições
            conditions: list[str] = [
                cond.strip().lower()
                for cond in self.rule_conditions.value.split(",")
                if cond.strip()
            ]

            if not conditions:
                await interaction.followup.send(
                    "❌ **Condições inválidas**\nEspecifique pelo menos uma condição.",
                    ephemeral=True,
                )
                return

            # Validar condições
            valid_conditions: list[dict[str, Any]] = []
            condition_types: dict[str, str] = {
                "join": "Ao entrar no servidor",
                "boost": "Ao dar boost no servidor",
                "verify": "Ao se verificar",
                "react": "Ao reagir em mensagem específica",
                "time": "Após tempo no servidor",
                "role": "Ao ganhar role específica",
                "level": "Ao atingir nível específico",
            }

            for condition in conditions:
                cond_type: str
                cond_value: str | None
                if ":" in condition:
                    cond_type, cond_value = condition.split(":", 1)
                else:
                    cond_type, cond_value = condition, None

                if cond_type in condition_types:
                    valid_conditions.append(
                        {
                            "type": cond_type,
                            "value": cond_value,
                            "description": condition_types[cond_type],
                        }
                    )
                else:
                    await interaction.followup.send(
                        f"❌ **Condição inválida:** `{condition}`\n"
                        f"**Condições válidas:** {', '.join(condition_types.keys())}",
                        ephemeral=True,
                    )
                    return

            # Criar dados da regra
            rule_data: dict[str, Any] = {
                "id": f"autorole_{self.guild.id}_{int(datetime.now().timestamp())}",
                "guild_id": str(self.guild.id),
                "name": self.rule_name.value,
                "description": self.rule_description.value,
                "conditions": valid_conditions,
                "roles_to_add": [],  # Será configurado posteriormente
                "roles_to_remove": [],  # Será configurado posteriormente
                "enabled": False,  # Desabilitado até configurar roles
                "created_by": str(self.user.id),
                "created_at": datetime.now().isoformat(),
                "usage_count": 0,
            }

            # Salvar no banco de dados
            try:
                from ...utils.database import database

                await database.execute(
                    """INSERT INTO autorole_rules 
                    (rule_id, guild_id, rule_name, rule_data, created_at, created_by, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        rule_data["id"],
                        str(self.guild.id),
                        self.rule_name.value,
                        json.dumps(rule_data),
                        datetime.now().isoformat(),
                        str(self.user.id),
                        0,
                    ),
                )

            except Exception as e:
                print(f"❌ Erro ao salvar regra: {e}")
                await interaction.followup.send(
                    "❌ Erro ao salvar regra de autorole.", ephemeral=True
                )
                return

            # Embed de confirmação
            success_embed: discord.Embed = discord.Embed(
                title="✅ **REGRA DE AUTOROLE CRIADA**",
                description=f"Regra `{self.rule_name.value}` foi criada com sucesso!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="📝 Nome da Regra", value=self.rule_name.value, inline=True
            )

            success_embed.add_field(
                name="🆔 ID da Regra", value=f"`{rule_data['id'][:20]}...`", inline=True
            )

            # Mostrar condições
            conditions_text: str = ""
            for condition in valid_conditions:
                cond_desc: str = condition["description"]
                if condition["value"]:
                    cond_desc += f" (`{condition['value']}`)"
                conditions_text += f"• {cond_desc}\n"

            success_embed.add_field(
                name="🔧 Condições Configuradas", value=conditions_text, inline=False
            )

            if self.rule_description.value:
                success_embed.add_field(
                    name="📄 Descrição", value=self.rule_description.value, inline=False
                )

            success_embed.add_field(
                name="⚠️ Próximos Passos",
                value=f"1. Configure as roles: `/autorole-roles {rule_data['id'][:8]}`\n"
                f"2. Ative a regra: `/autorole-toggle {rule_data['id'][:8]}`\n"
                f"3. Teste a regra: `/autorole-test {rule_data['id'][:8]}`",
                inline=False,
            )

            success_embed.add_field(
                name="🔴 Status Atual",
                value="**Desativada** - Configure as roles antes de ativar",
                inline=True,
            )

            success_embed.set_footer(
                text=f"Criada por {self.user}", icon_url=self.user.display_avatar.url
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no modal autorole: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao processar configuração de autorole.", ephemeral=True
                )
            except:
                pass


class AutoroleRolesView(discord.ui.View):
    """View para configurar roles de uma regra de autorole"""

    def __init__(self, rule_data: dict[str, Any], user: discord.Member) -> None:
        super().__init__(timeout=300)
        self.rule_data: dict[str, Any] = rule_data
        self.user: discord.Member = user

        # Opções de roles para adicionar
        self.role_select: discord.ui.RoleSelect = discord.ui.RoleSelect(
            placeholder="🏷️ Selecione roles para ADICIONAR...", min_values=0, max_values=10, row=0
        )

        # Opções de roles para remover
        self.remove_role_select: discord.ui.RoleSelect = discord.ui.RoleSelect(
            placeholder="🗑️ Selecione roles para REMOVER...", min_values=0, max_values=10, row=1
        )

        self.add_item(self.role_select)
        self.add_item(self.remove_role_select)

    @discord.ui.button(label="💾 Salvar Configuração", style=discord.ButtonStyle.green, row=2)
    async def save_roles(
        self, interaction: discord.Interaction, button: discord.ui.Button[AutoroleRolesView]
    ) -> None:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Apenas quem configurou pode salvar.", ephemeral=True
            )
            return

        try:
            await interaction.response.defer(ephemeral=True)

            # Obter roles selecionadas
            roles_to_add: list[str] = (
                [str(role.id) for role in self.role_select.values]
                if hasattr(self.role_select, "values")
                else []
            )
            roles_to_remove: list[str] = (
                [str(role.id) for role in self.remove_role_select.values]
                if hasattr(self.remove_role_select, "values")
                else []
            )

            if not roles_to_add and not roles_to_remove:
                await interaction.followup.send(
                    "❌ **Nenhuma role selecionada**\nSelecione pelo menos uma role para adicionar ou remover.",
                    ephemeral=True,
                )
                return

            # Atualizar dados da regra
            self.rule_data["roles_to_add"] = roles_to_add
            self.rule_data["roles_to_remove"] = roles_to_remove

            # Salvar no banco
            try:
                from ...utils.database import database

                await database.execute(
                    "UPDATE autorole_rules SET rule_data = ? WHERE rule_id = ?",
                    (json.dumps(self.rule_data), self.rule_data["id"]),
                )

            except Exception as e:
                print(f"❌ Erro ao salvar roles: {e}")
                await interaction.followup.send(
                    "❌ Erro ao salvar configuração de roles.", ephemeral=True
                )
                return

            # Embed de confirmação
            success_embed: discord.Embed = discord.Embed(
                title="💾 **ROLES CONFIGURADAS**",
                description=f"Roles da regra `{self.rule_data['name']}` foram configuradas!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            if roles_to_add:
                add_text: str = ""
                for role_id in roles_to_add:
                    role: discord.Role | None = interaction.guild.get_role(int(role_id))
                    add_text += f"• {role.mention if role else f'Role ID: {role_id}'}\n"

                success_embed.add_field(name="🏷️ Roles para Adicionar", value=add_text, inline=True)

            if roles_to_remove:
                remove_text: str = ""
                for role_id in roles_to_remove:
                    role = interaction.guild.get_role(int(role_id))
                    remove_text += f"• {role.mention if role else f'Role ID: {role_id}'}\n"

                success_embed.add_field(name="🗑️ Roles para Remover", value=remove_text, inline=True)

            success_embed.add_field(
                name="✅ Próximo Passo",
                value=f"Ative a regra com: `/autorole-toggle {self.rule_data['id'][:8]}`",
                inline=False,
            )

            # Desabilitar todos os componentes
            for item in self.children:
                item.disabled = True

            await interaction.followup.send(embed=success_embed, view=self, ephemeral=True)
            self.stop()

        except Exception as e:
            print(f"❌ Erro ao salvar roles: {e}")
            await interaction.followup.send(
                "❌ Erro ao processar configuração de roles.", ephemeral=True
            )

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary, row=2)
    async def cancel_setup(
        self, interaction: discord.Interaction, button: discord.ui.Button[AutoroleRolesView]
    ) -> None:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Apenas quem configurou pode cancelar.", ephemeral=True
            )
            return

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(content="❌ **Configuração cancelada**", view=self)

        self.stop()


class AutoroleSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.active_rules_cache: dict[int, Any] = {}
        self.cooldowns: dict[int, float] = {}

    @app_commands.command(name="autorole-setup", description="🤖 Configurar sistema de autorole")
    async def autorole_setup(self, interaction: discord.Interaction) -> None:
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para configurar autorole. **Necessário**: Gerenciar Roles",
                    ephemeral=True,
                )
                return

            # Abrir modal de configuração
            modal: AutoroleSetupModal = AutoroleSetupModal(interaction.guild, interaction.user)
            await interaction.response.send_modal(modal)

        except Exception as e:
            print(f"❌ Erro no comando autorole-setup: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao configurar autorole.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(
        name="autorole-roles", description="🏷️ Configurar roles de uma regra de autorole"
    )
    @app_commands.describe(rule_id="ID da regra (primeiros caracteres suficientes)")
    async def autorole_roles(self, interaction: discord.Interaction, rule_id: str) -> None:
        try:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para configurar roles.", ephemeral=True
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
                        f"Nenhuma regra encontrada com ID: `{rule_id}`\n"
                        f"Use `/autorole-list` para ver todas as regras.",
                        ephemeral=True,
                    )
                    return

                rule_data: dict[str, Any] = json.loads(rule["rule_data"])

            except Exception as e:
                print(f"❌ Erro ao buscar regra: {e}")
                await interaction.followup.send(
                    "❌ Erro ao buscar regra de autorole.", ephemeral=True
                )
                return

            # Criar view de configuração
            view: AutoroleRolesView = AutoroleRolesView(rule_data, interaction.user)

            # Embed explicativo
            config_embed: discord.Embed = discord.Embed(
                title="🏷️ **CONFIGURAR ROLES DA REGRA**",
                description=f"Configurando roles para: **{rule_data['name']}**",
                color=0x4A90E2,
                timestamp=datetime.now(),
            )

            # Mostrar condições da regra
            conditions_text: str = ""
            for condition in rule_data.get("conditions", []):
                cond_desc: str = condition["description"]
                if condition.get("value"):
                    cond_desc += f" (`{condition['value']}`)"
                conditions_text += f"• {cond_desc}\n"

            config_embed.add_field(
                name="🔧 Condições da Regra",
                value=conditions_text or "Nenhuma condição configurada",
                inline=False,
            )

            config_embed.add_field(
                name="📋 Instruções",
                value="1. **Roles para ADICIONAR:** Selecione roles que serão dadas aos usuários\n"
                "2. **Roles para REMOVER:** Selecione roles que serão removidas dos usuários\n"
                "3. Clique em **💾 Salvar Configuração** quando terminar",
                inline=False,
            )

            # Mostrar roles atuais se já configuradas
            current_add: list[str] = rule_data.get("roles_to_add", [])
            current_remove: list[str] = rule_data.get("roles_to_remove", [])

            if current_add or current_remove:
                current_text: str = ""
                if current_add:
                    add_roles: list[discord.Role | None] = [
                        interaction.guild.get_role(int(role_id)) for role_id in current_add
                    ]
                    add_names: list[str] = [
                        role.mention if role else "Role não encontrada" for role in add_roles
                    ]
                    current_text += f"**🏷️ Adicionar:** {', '.join(add_names)}\n"

                if current_remove:
                    remove_roles: list[discord.Role | None] = [
                        interaction.guild.get_role(int(role_id)) for role_id in current_remove
                    ]
                    remove_names: list[str] = [
                        role.mention if role else "Role não encontrada" for role in remove_roles
                    ]
                    current_text += f"**🗑️ Remover:** {', '.join(remove_names)}\n"

                config_embed.add_field(
                    name="🏷️ Configuração Atual", value=current_text, inline=False
                )

            config_embed.set_footer(
                text="Selecione as roles usando os menus abaixo",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=config_embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando autorole-roles: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao configurar roles da regra.", ephemeral=True
                )
            except:
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoroleSystem(bot))
