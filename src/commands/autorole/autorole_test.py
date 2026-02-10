"""
Sistema de Autorole - Teste e Configuração de Roles
Teste de regras e configuração de roles
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


class AutoroleTestRoles(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(name="autorole-test", description="🔍 Testar regra de autorole")
    @app_commands.describe(
        rule_id="ID da regra para testar", user="Usuário para testar (opcional, padrão: você)"
    )
    async def autorole_test(
        self, interaction: discord.Interaction, rule_id: str, user: discord.Member | None = None
    ) -> None:
        try:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para testar regras.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            test_user: discord.Member = user or interaction.user

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

            # Testar condições
            conditions: list[dict[str, Any]] = rule_data.get("conditions", [])
            test_results: list[dict[str, Any]] = []
            all_conditions_met: bool = True

            for i, condition in enumerate(conditions, 1):
                condition_type: str = condition.get("type", "unknown")
                condition_value: str = condition.get("value", "")
                description: str = condition.get("description", "Condição desconhecida")

                result: dict[str, Any] = await self._test_condition(test_user, condition)
                test_results.append(
                    {
                        "index": i,
                        "description": description,
                        "type": condition_type,
                        "value": condition_value,
                        "passed": result["passed"],
                        "reason": result["reason"],
                    }
                )

                if not result["passed"]:
                    all_conditions_met = False

            # Verificar roles configuradas
            roles_add: list[str] = rule_data.get("roles_to_add", [])
            roles_remove: list[str] = rule_data.get("roles_to_remove", [])

            roles_status: dict[str, list[Any]] = {
                "add_valid": [],
                "add_invalid": [],
                "remove_valid": [],
                "remove_invalid": [],
            }

            for role_id in roles_add:
                role: discord.Role | None = interaction.guild.get_role(int(role_id))
                if role:
                    roles_status["add_valid"].append(role)
                else:
                    roles_status["add_invalid"].append(role_id)

            for role_id in roles_remove:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    roles_status["remove_valid"].append(role)
                else:
                    roles_status["remove_invalid"].append(role_id)

            # Criar embed de resultado
            test_color: int = 0x00FF00 if all_conditions_met else 0xFF6B6B

            test_embed: discord.Embed = discord.Embed(
                title="🔍 **TESTE DE REGRA**",
                description=f"Testando regra `{rule['rule_name']}` para {test_user.mention}",
                color=test_color,
                timestamp=datetime.now(),
            )

            # Status geral
            overall_status: str = "✅ Aprovado" if all_conditions_met else "❌ Reprovado"
            test_embed.add_field(
                name="📊 Resultado Geral",
                value=f"**Status:** {overall_status}\n"
                f"**Usuário:** {test_user.mention}\n"
                f"**Regra:** {'✅ Ativa' if rule['enabled'] else '❌ Inativa'}",
                inline=True,
            )

            # Resultados das condições
            if test_results:
                conditions_text: str = ""
                for result in test_results:
                    status_icon: str = "✅" if result["passed"] else "❌"
                    conditions_text += (
                        f"{status_icon} **{result['index']}.** {result['description']}\n"
                    )
                    if not result["passed"]:
                        conditions_text += f"     └ {result['reason']}\n"

                test_embed.add_field(
                    name="🔧 Condições Testadas", value=conditions_text, inline=False
                )

            # Status das roles
            if roles_status["add_valid"] or roles_status["remove_valid"]:
                roles_text: str = ""

                if roles_status["add_valid"]:
                    add_text: str = ", ".join([r.mention for r in roles_status["add_valid"]])
                    roles_text += f"**➕ Adicionar:** {add_text}\n"

                if roles_status["remove_valid"]:
                    remove_text: str = ", ".join([r.mention for r in roles_status["remove_valid"]])
                    roles_text += f"**➖ Remover:** {remove_text}\n"

                test_embed.add_field(name="🏷️ Roles Configuradas", value=roles_text, inline=False)

            # Problemas encontrados
            problems: list[str] = []

            if not rule["enabled"]:
                problems.append("• A regra está **desativada**")

            if roles_status["add_invalid"]:
                problems.append(
                    f"• {len(roles_status['add_invalid'])} role(s) para adicionar não encontrada(s)"
                )

            if roles_status["remove_invalid"]:
                problems.append(
                    f"• {len(roles_status['remove_invalid'])} role(s) para remover não encontrada(s)"
                )

            if not roles_add and not roles_remove:
                problems.append("• Nenhuma role configurada para esta regra")

            if problems:
                test_embed.add_field(
                    name="⚠️ Problemas Detectados", value="\n".join(problems), inline=False
                )

            # Simulação de aplicação
            if all_conditions_met and rule["enabled"]:
                simulation_text: str = "**A regra seria aplicada com os seguintes efeitos:**\n"

                if roles_status["add_valid"]:
                    for role in roles_status["add_valid"]:
                        if role not in test_user.roles:
                            simulation_text += f"✅ Adicionaria {role.mention}\n"
                        else:
                            simulation_text += f"ℹ️ {test_user.mention} já possui {role.mention}\n"

                if roles_status["remove_valid"]:
                    for role in roles_status["remove_valid"]:
                        if role in test_user.roles:
                            simulation_text += f"❌ Removeria {role.mention}\n"
                        else:
                            simulation_text += f"ℹ️ {test_user.mention} não possui {role.mention}\n"

                test_embed.add_field(name="🔮 Simulação", value=simulation_text, inline=False)

            # Informações de debug
            debug_info: str = f"**ID da Regra:** `{rule['rule_id'][:16]}...`\n"
            debug_info += f"**Condições:** {len(conditions)}\n"
            debug_info += f"**Roles Add:** {len(roles_add)}\n"
            debug_info += f"**Roles Remove:** {len(roles_remove)}"

            test_embed.add_field(name="🔧 Debug", value=debug_info, inline=True)

            test_embed.set_footer(
                text=f"Testado por {interaction.user}", icon_url=interaction.user.display_avatar.url
            )

            await interaction.followup.send(embed=test_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando autorole-test: {e}")
            try:
                await interaction.followup.send("❌ Erro ao testar regra.", ephemeral=True)
            except:
                pass

    async def _test_condition(self, user: discord.Member, condition: dict[str, Any]) -> dict[str, Any]:
        """Testa uma condição específica para um usuário"""
        try:
            condition_type: str = condition.get("type", "unknown")
            condition_value: str = condition.get("value", "")

            if condition_type == "join":
                # Sempre passa para teste (não podemos simular entrada)
                return {
                    "passed": True,
                    "reason": "Condição de entrada seria ativada quando o usuário entrar",
                }

            if condition_type == "boost":
                if user.premium_since:
                    return {"passed": True, "reason": "Usuário é booster"}
                return {"passed": False, "reason": "Usuário não é booster do servidor"}

            if condition_type == "time_in_server":
                if not user.joined_at:
                    return {"passed": False, "reason": "Data de entrada não disponível"}

                # Parse do tempo necessário
                time_parts: list[str] = condition_value.split()
                if len(time_parts) != 2:
                    return {"passed": False, "reason": "Formato de tempo inválido"}

                number: int = int(time_parts[0])
                unit: str = time_parts[1].lower()

                required_delta: timedelta
                if unit in ["dia", "dias", "day", "days"]:
                    required_delta = timedelta(days=number)
                elif unit in ["hora", "horas", "hour", "hours"]:
                    required_delta = timedelta(hours=number)
                elif unit in ["minuto", "minutos", "minute", "minutes"]:
                    required_delta = timedelta(minutes=number)
                else:
                    return {"passed": False, "reason": "Unidade de tempo não reconhecida"}

                user_time_delta: timedelta = datetime.now(user.joined_at.tzinfo) - user.joined_at

                if user_time_delta >= required_delta:
                    return {
                        "passed": True,
                        "reason": f"Usuário está no servidor há {user_time_delta.days} dias",
                    }
                remaining: timedelta = required_delta - user_time_delta
                return {"passed": False, "reason": f"Faltam {remaining.days} dias no servidor"}

            if condition_type == "has_role":
                role_id: int = int(condition_value)
                role: discord.Role | None = user.guild.get_role(role_id)

                if not role:
                    return {"passed": False, "reason": "Role especificada não existe"}

                if role in user.roles:
                    return {"passed": True, "reason": f"Usuário possui a role {role.name}"}
                return {"passed": False, "reason": f"Usuário não possui a role {role.name}"}

            if condition_type == "reaction":
                # Para teste, sempre passa (não podemos simular reação)
                return {
                    "passed": True,
                    "reason": "Condição de reação seria ativada quando o usuário reagir",
                }

            return {"passed": False, "reason": "Tipo de condição não reconhecido"}

        except Exception as e:
            return {"passed": False, "reason": f"Erro ao testar condição: {e!s}"}

    @app_commands.command(name="autorole-roles", description="🏷️ Configurar roles de uma regra")
    @app_commands.describe(rule_id="ID da regra para configurar roles")
    async def autorole_roles(self, interaction: discord.Interaction, rule_id: str) -> None:
        try:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para configurar roles.", ephemeral=True
                )
                return

            # Buscar regra
            try:
                from ...utils.database import database

                rule: Any = await database.get(
                    "SELECT * FROM autorole_rules WHERE guild_id = ? AND rule_id LIKE ?",
                    (str(interaction.guild.id), f"{rule_id}%"),
                )

                if not rule:
                    await interaction.response.send_message(
                        f"❌ Regra não encontrada com ID: `{rule_id}`", ephemeral=True
                    )
                    return

                rule_data: dict[str, Any] = json.loads(rule["rule_data"])

            except Exception as e:
                print(f"❌ Erro ao buscar regra: {e}")
                await interaction.response.send_message(
                    "❌ Erro ao consultar regra.", ephemeral=True
                )
                return

            # Criar modal de configuração
            modal: AutoroleRolesModal = AutoroleRolesModal(rule, rule_data)
            await interaction.response.send_modal(modal)

        except Exception as e:
            print(f"❌ Erro no comando autorole-roles: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao abrir configuração de roles.", ephemeral=True
                )
            except:
                pass


class AutoroleRolesModal(discord.ui.Modal, title="🏷️ Configurar Roles da Regra"):
    def __init__(self, rule: dict[str, Any], rule_data: dict[str, Any]) -> None:
        super().__init__(timeout=300)
        self.rule: dict[str, Any] = rule
        self.rule_data: dict[str, Any] = rule_data

        # Roles atuais
        current_add: list[str] = rule_data.get("roles_to_add", [])
        current_remove: list[str] = rule_data.get("roles_to_remove", [])

        # Converter IDs em nomes
        add_names: list[str] = []
        remove_names: list[str] = []

        # Não podemos acessar guild aqui, então usamos IDs
        add_names = current_add
        remove_names = current_remove

    roles_add: discord.ui.TextInput[AutoroleRolesModal] = discord.ui.TextInput(
        label="Roles para Adicionar",
        placeholder="IDs das roles separadas por vírgula (ex: 123456789, 987654321)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
    )

    roles_remove: discord.ui.TextInput[AutoroleRolesModal] = discord.ui.TextInput(
        label="Roles para Remover",
        placeholder="IDs das roles separadas por vírgula (ex: 123456789, 987654321)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # Processar roles para adicionar
            roles_to_add: list[str] = []
            add_text: str = self.roles_add.value.strip()
            if add_text:
                for role_id in add_text.split(","):
                    role_id_clean: str = role_id.strip()
                    if role_id_clean.isdigit():
                        # Verificar se a role existe
                        role: discord.Role | None = interaction.guild.get_role(int(role_id_clean))
                        if role:
                            roles_to_add.append(role_id_clean)

            # Processar roles para remover
            roles_to_remove: list[str] = []
            remove_text: str = self.roles_remove.value.strip()
            if remove_text:
                for role_id in remove_text.split(","):
                    role_id_clean = role_id.strip()
                    if role_id_clean.isdigit():
                        # Verificar se a role existe
                        role = interaction.guild.get_role(int(role_id_clean))
                        if role:
                            roles_to_remove.append(role_id_clean)

            # Atualizar dados da regra
            self.rule_data["roles_to_add"] = roles_to_add
            self.rule_data["roles_to_remove"] = roles_to_remove

            # Salvar no banco
            try:
                from ...utils.database import database

                await database.execute(
                    "UPDATE autorole_rules SET rule_data = ? WHERE rule_id = ?",
                    (json.dumps(self.rule_data), self.rule["rule_id"]),
                )
            except Exception as e:
                print(f"❌ Erro ao salvar configuração: {e}")
                await interaction.followup.send(
                    "❌ Erro ao salvar configuração de roles.", ephemeral=True
                )
                return

            # Embed de confirmação
            config_embed: discord.Embed = discord.Embed(
                title="🏷️ **ROLES CONFIGURADAS**",
                description=f"Roles da regra `{self.rule['rule_name']}` atualizadas!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            config_embed.add_field(
                name="📝 Regra",
                value=f"**Nome:** {self.rule['rule_name']}\n"
                f"**ID:** `{self.rule['rule_id'][:16]}...`",
                inline=True,
            )

            # Mostrar roles configuradas
            if roles_to_add:
                add_list: list[str] = []
                for role_id in roles_to_add:
                    role = interaction.guild.get_role(int(role_id))
                    if role:
                        add_list.append(role.mention)

                if add_list:
                    config_embed.add_field(
                        name="➕ Roles para Adicionar", value="\n".join(add_list), inline=True
                    )

            if roles_to_remove:
                remove_list: list[str] = []
                for role_id in roles_to_remove:
                    role = interaction.guild.get_role(int(role_id))
                    if role:
                        remove_list.append(role.mention)

                if remove_list:
                    config_embed.add_field(
                        name="➖ Roles para Remover", value="\n".join(remove_list), inline=True
                    )

            if not roles_to_add and not roles_to_remove:
                config_embed.add_field(
                    name="⚠️ Configuração Limpa",
                    value="Nenhuma role configurada.\n"
                    "A regra não terá efeito até roles serem configuradas.",
                    inline=False,
                )
            else:
                config_embed.add_field(
                    name="✅ Próximos Passos",
                    value=f"• Use `/autorole-test {self.rule['rule_id'][:8]}` para testar\n"
                    f"• Use `/autorole-toggle {self.rule['rule_id'][:8]}` para ativar\n"
                    "• A regra aplicará automaticamente quando ativa",
                    inline=False,
                )

            config_embed.set_footer(
                text=f"Configurado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=config_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro ao processar configuração: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao processar configuração de roles.", ephemeral=True
                )
            except:
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoroleTestRoles(bot))
