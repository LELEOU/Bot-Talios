"""
Sistema de Antispam - Gerenciamento de Regras
Configuração avançada de regras e exceções do antispam
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


class AntispamRules(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.rule_types: list[str] = [
            "spam_messages",  # Spam de mensagens rápidas
            "duplicate_content",  # Conteúdo duplicado
            "excessive_mentions",  # Muitas menções
            "excessive_emojis",  # Muitos emojis
            "excessive_caps",  # Muito CAPS
            "suspicious_links",  # Links suspeitos
            "repeated_chars",  # Caracteres repetidos
            "zalgo_text",  # Texto zalgo/unicode
            "invite_links",  # Convites Discord
            "external_links",  # Links externos
        ]

    @app_commands.command(
        name="antispam-rules", description="📋 Gerenciar regras personalizadas do antispam"
    )
    @app_commands.describe(
        acao="Ação a ser executada",
        regra="Tipo de regra para configurar",
        valor="Novo valor para a regra",
    )
    async def antispam_rules(
        self,
        interaction: discord.Interaction,
        acao: str,
        regra: str | None = None,
        valor: str | None = None,
    ) -> None:
        try:
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para gerenciar regras antispam.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar configuração atual
            try:
                from ...utils.database import database

                config_data: Any = await database.get(
                    "SELECT config_data FROM antispam_config WHERE guild_id = ?",
                    (str(interaction.guild.id),),
                )

                config: dict[str, Any]
                if config_data:
                    config = json.loads(config_data["config_data"])
                else:
                    # Configuração padrão expandida
                    config = {
                        "enabled": True,
                        "rules": {
                            "spam_messages": {
                                "enabled": True,
                                "max_messages": 5,
                                "time_window": 10,
                            },
                            "duplicate_content": {
                                "enabled": True,
                                "max_duplicates": 3,
                                "similarity_threshold": 80,
                            },
                            "excessive_mentions": {
                                "enabled": True,
                                "max_mentions": 5,
                                "include_everyone": True,
                            },
                            "excessive_emojis": {
                                "enabled": True,
                                "max_emojis": 10,
                                "include_custom": True,
                            },
                            "excessive_caps": {
                                "enabled": True,
                                "max_percentage": 70,
                                "min_length": 10,
                            },
                            "suspicious_links": {
                                "enabled": True,
                                "check_shortened": True,
                                "whitelist": [],
                            },
                            "repeated_chars": {
                                "enabled": True,
                                "max_repetition": 5,
                                "ignore_emojis": True,
                            },
                            "zalgo_text": {"enabled": True, "max_combining_chars": 3},
                            "invite_links": {
                                "enabled": True,
                                "allow_own_server": False,
                                "whitelist": [],
                            },
                            "external_links": {
                                "enabled": False,
                                "whitelist": [],
                                "require_permission": True,
                            },
                        },
                        "actions": {
                            "first_violation": "warn",
                            "second_violation": "mute",
                            "third_violation": "kick",
                            "persistent_violation": "ban",
                        },
                        "whitelist_users": [],
                        "ignored_roles": [],
                        "ignored_channels": [],
                    }
            except Exception as e:
                print(f"❌ Erro ao carregar config: {e}")
                await interaction.followup.send("❌ Erro ao carregar configuração.", ephemeral=True)
                return

            if acao.lower() in ["list", "listar", "ver"]:
                # Listar regras atuais
                rules_embed: discord.Embed = discord.Embed(
                    title="📋 **REGRAS ANTISPAM ATIVAS**",
                    description=f"Servidor: {interaction.guild.name}",
                    color=0x4A90E2,
                    timestamp=datetime.now(),
                )

                rules: dict[str, Any] = config.get("rules", {})

                active_rules: list[str] = []
                inactive_rules: list[str] = []

                rule_descriptions: dict[str, str] = {
                    "spam_messages": "📨 Spam de Mensagens",
                    "duplicate_content": "🔄 Conteúdo Duplicado",
                    "excessive_mentions": "📞 Menções Excessivas",
                    "excessive_emojis": "😀 Emojis Excessivos",
                    "excessive_caps": "🔠 CAPS Excessivo",
                    "suspicious_links": "🔗 Links Suspeitos",
                    "repeated_chars": "🔤 Caracteres Repetidos",
                    "zalgo_text": "👻 Texto Zalgo",
                    "invite_links": "💌 Links de Convite",
                    "external_links": "🌐 Links Externos",
                }

                for rule_name in self.rule_types:
                    rule_config: dict[str, Any] = rules.get(rule_name, {})
                    enabled: bool = rule_config.get("enabled", True)
                    description: str = rule_descriptions.get(rule_name, rule_name.title())

                    if enabled:
                        # Mostrar configurações específicas
                        details: list[str] = []
                        if rule_name == "spam_messages":
                            details.append(
                                f"Max: {rule_config.get('max_messages', 5)} msgs/{rule_config.get('time_window', 10)}s"
                            )
                        elif rule_name == "excessive_mentions":
                            details.append(f"Max: {rule_config.get('max_mentions', 5)} menções")
                        elif rule_name == "excessive_caps":
                            details.append(f"Max: {rule_config.get('max_percentage', 70)}% CAPS")
                        elif rule_name == "excessive_emojis":
                            details.append(f"Max: {rule_config.get('max_emojis', 10)} emojis")

                        detail_text: str = f" ({', '.join(details)})" if details else ""
                        active_rules.append(f"✅ {description}{detail_text}")
                    else:
                        inactive_rules.append(f"❌ {description}")

                if active_rules:
                    rules_embed.add_field(
                        name="🟢 Regras Ativas", value="\n".join(active_rules), inline=False
                    )

                if inactive_rules:
                    rules_embed.add_field(
                        name="🔴 Regras Desativas", value="\n".join(inactive_rules), inline=False
                    )

                # Ações configuradas
                actions: dict[str, str] = config.get("actions", {})
                action_text: str = ""
                action_emojis: dict[str, str] = {"warn": "⚠️", "mute": "🔇", "kick": "🥾", "ban": "🔨"}

                for violation, action in actions.items():
                    emoji: str = action_emojis.get(action, "📊")
                    violation_name: str = violation.replace("_", " ").title()
                    action_name: str = action.title()
                    action_text += f"{emoji} **{violation_name}:** {action_name}\n"

                if action_text:
                    rules_embed.add_field(
                        name="⚖️ Ações Configuradas", value=action_text, inline=True
                    )

                # Estatísticas de exceções
                whitelist_count: int = len(config.get("whitelist_users", []))
                ignored_roles_count: int = len(config.get("ignored_roles", []))
                ignored_channels_count: int = len(config.get("ignored_channels", []))

                if whitelist_count > 0 or ignored_roles_count > 0 or ignored_channels_count > 0:
                    exception_text: str = ""
                    if whitelist_count > 0:
                        exception_text += f"👥 **Usuários na whitelist:** {whitelist_count}\n"
                    if ignored_roles_count > 0:
                        exception_text += f"🎭 **Roles ignorados:** {ignored_roles_count}\n"
                    if ignored_channels_count > 0:
                        exception_text += f"📺 **Canais ignorados:** {ignored_channels_count}\n"

                    rules_embed.add_field(
                        name="🚫 Exceções Configuradas", value=exception_text, inline=True
                    )

                rules_embed.set_footer(
                    text="Use /antispam-rules edit <regra> <valor> para modificar",
                    icon_url=interaction.user.display_avatar.url,
                )

                await interaction.followup.send(embed=rules_embed, ephemeral=True)

            elif acao.lower() in ["edit", "editar", "modificar"] and regra and valor:
                # Editar uma regra específica
                if regra not in self.rule_types:
                    await interaction.followup.send(
                        "❌ **Regra inválida!**\n"
                        "**Regras disponíveis:**\n"
                        + "\n".join([f"• `{rule}`" for rule in self.rule_types]),
                        ephemeral=True,
                    )
                    return

                # Processar novo valor
                success: bool = False
                error_msg: str = ""

                try:
                    rules = config.get("rules", {})
                    if regra not in rules:
                        # Criar configuração padrão para a regra
                        rules[regra] = {"enabled": True}

                    # Interpretar o valor baseado no tipo da regra
                    if valor.lower() in ["true", "on", "ativo", "sim", "enable"]:
                        rules[regra]["enabled"] = True
                        success = True
                    elif valor.lower() in ["false", "off", "desativo", "não", "disable"]:
                        rules[regra]["enabled"] = False
                        success = True
                    elif valor.isdigit():
                        # Valor numérico
                        num_value: int = int(valor)
                        if regra == "spam_messages" and "max_messages" in rules[regra]:
                            rules[regra]["max_messages"] = max(1, min(50, num_value))
                            success = True
                        elif regra == "excessive_mentions":
                            rules[regra]["max_mentions"] = max(1, min(20, num_value))
                            success = True
                        elif regra == "excessive_emojis":
                            rules[regra]["max_emojis"] = max(1, min(50, num_value))
                            success = True
                        elif regra == "excessive_caps":
                            rules[regra]["max_percentage"] = max(10, min(100, num_value))
                            success = True
                        else:
                            error_msg = "Valor numérico não aplicável para esta regra."
                    else:
                        error_msg = "Valor não reconhecido. Use: true/false ou número (para regras aplicáveis)."

                    if success:
                        # Salvar configuração atualizada
                        config["rules"] = rules
                        config_json: str = json.dumps(config)

                        await database.execute(
                            "UPDATE antispam_config SET config_data = ? WHERE guild_id = ?",
                            (config_json, str(interaction.guild.id)),
                        )

                        edit_embed: discord.Embed = discord.Embed(
                            title="✅ **REGRA ATUALIZADA**",
                            description=f"Regra `{regra}` foi modificada com sucesso!",
                            color=0x00FF00,
                            timestamp=datetime.now(),
                        )

                        edit_embed.add_field(
                            name="📝 Alteração Realizada",
                            value=f"**Regra:** {regra}\n**Novo valor:** {valor}",
                            inline=True,
                        )

                        # Mostrar configuração atual da regra
                        rule_config = rules[regra]
                        config_text: str = ""
                        for key, val in rule_config.items():
                            config_text += f"**{key}:** {val}\n"

                        edit_embed.add_field(
                            name="⚙️ Configuração Atual",
                            value=config_text or "Configuração padrão",
                            inline=True,
                        )

                        await interaction.followup.send(embed=edit_embed, ephemeral=True)
                    else:
                        await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)

                except Exception as e:
                    print(f"❌ Erro ao editar regra: {e}")
                    await interaction.followup.send(
                        "❌ Erro ao salvar alteração da regra.", ephemeral=True
                    )

            elif acao.lower() in ["reset", "resetar"]:
                # Reset das regras para padrão
                try:
                    # Restaurar configuração padrão
                    default_rules: dict[str, dict[str, Any]] = {
                        "spam_messages": {"enabled": True, "max_messages": 5, "time_window": 10},
                        "duplicate_content": {"enabled": True, "max_duplicates": 3},
                        "excessive_mentions": {"enabled": True, "max_mentions": 5},
                        "excessive_emojis": {"enabled": True, "max_emojis": 10},
                        "excessive_caps": {"enabled": True, "max_percentage": 70},
                        "suspicious_links": {"enabled": True},
                        "repeated_chars": {"enabled": True, "max_repetition": 5},
                        "zalgo_text": {"enabled": False},
                        "invite_links": {"enabled": True},
                        "external_links": {"enabled": False},
                    }

                    config["rules"] = default_rules

                    # Salvar
                    config_json = json.dumps(config)
                    await database.execute(
                        "UPDATE antispam_config SET config_data = ? WHERE guild_id = ?",
                        (config_json, str(interaction.guild.id)),
                    )

                    reset_embed: discord.Embed = discord.Embed(
                        title="🔄 **REGRAS RESETADAS**",
                        description="Todas as regras foram restauradas para os valores padrão!",
                        color=0xFFA500,
                        timestamp=datetime.now(),
                    )

                    reset_embed.add_field(
                        name="✅ Regras Restauradas",
                        value="• Spam de mensagens: 5 msgs/10s\n"
                        "• Menções excessivas: 5 máx\n"
                        "• Emojis excessivos: 10 máx\n"
                        "• CAPS excessivo: 70% máx\n"
                        "• Links suspeitos: Ativo\n"
                        "• Caracteres repetidos: 5 máx\n"
                        "• Links de convite: Ativo",
                        inline=False,
                    )

                    await interaction.followup.send(embed=reset_embed, ephemeral=True)

                except Exception as e:
                    print(f"❌ Erro ao resetar regras: {e}")
                    await interaction.followup.send("❌ Erro ao resetar regras.", ephemeral=True)

            else:
                # Mostrar ajuda de uso
                help_embed: discord.Embed = discord.Embed(
                    title="❓ **COMO USAR ANTISPAM-RULES**",
                    description="Comando para gerenciar regras personalizadas do sistema antispam",
                    color=0x4A90E2,
                    timestamp=datetime.now(),
                )

                help_embed.add_field(
                    name="📋 Ações Disponíveis",
                    value="`list` - Ver todas as regras atuais\n"
                    "`edit` - Modificar uma regra específica\n"
                    "`reset` - Restaurar regras padrão",
                    inline=False,
                )

                help_embed.add_field(
                    name="🎯 Regras Configuráveis",
                    value="• `spam_messages` - Spam de mensagens rápidas\n"
                    "• `excessive_mentions` - Muitas menções\n"
                    "• `excessive_emojis` - Muitos emojis\n"
                    "• `excessive_caps` - Muito CAPS\n"
                    "• `suspicious_links` - Links suspeitos\n"
                    "• `repeated_chars` - Caracteres repetidos\n"
                    "• `invite_links` - Links de convite Discord\n"
                    "• `external_links` - Links externos",
                    inline=False,
                )

                help_embed.add_field(
                    name="💡 Exemplos de Uso",
                    value="`/antispam-rules list` - Ver regras atuais\n"
                    "`/antispam-rules edit spam_messages 10` - Max 10 msgs\n"
                    "`/antispam-rules edit excessive_caps false` - Desativar CAPS\n"
                    "`/antispam-rules reset` - Restaurar padrões",
                    inline=False,
                )

                await interaction.followup.send(embed=help_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando antispam-rules: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao gerenciar regras do antispam.", ephemeral=True
                )
            except:
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AntispamRules(bot))
