"""
Comandos de Configuração do Bot
Interface para dashboard e configurações do servidor
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, Select, View

if TYPE_CHECKING:
    pass

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.permission_system import perm_system


class RoleSelectMenu(Select):
    """Menu para selecionar cargos"""

    def __init__(self, setting_type: str, current_roles: list[str]) -> None:
        self.setting_type: str = setting_type

        options: list[discord.SelectOption] = [
            discord.SelectOption(
                label="Remover todos os cargos",
                value="CLEAR",
                emoji="🗑️",
                description="Limpar esta configuração",
            )
        ]

        super().__init__(
            placeholder=f"Selecione cargos para {setting_type}",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Processar seleção"""
        if self.values[0] == "CLEAR":
            # Limpar configuração
            update_data: dict[str, str] = {f"{self.setting_type}_role_ids": ""}
            await perm_system.update_config(str(interaction.guild.id), **update_data)

            await interaction.response.send_message(
                f"✅ Configuração de **{self.setting_type}** limpa!", ephemeral=True
            )
        else:
            # Atualizar com cargos selecionados
            role_ids: str = ",".join(self.values)
            update_data = {f"{self.setting_type}_role_ids": role_ids}
            await perm_system.update_config(str(interaction.guild.id), **update_data)

            roles_mention: list[str] = [f"<@&{rid}>" for rid in self.values]
            await interaction.response.send_message(
                f"✅ Cargos de **{self.setting_type}** atualizados:\n" + "\n".join(roles_mention),
                ephemeral=True,
            )


class ConfigView(View):
    """View principal de configuração"""

    def __init__(self, guild: discord.Guild) -> None:
        super().__init__(timeout=300)
        self.guild: discord.Guild = guild

    @discord.ui.button(label="👑 Cargos Admin", style=discord.ButtonStyle.primary, emoji="👑")
    async def config_admin(self, interaction: discord.Interaction, button: Button) -> None:
        """Configurar cargos de administrador"""
        embed: discord.Embed = discord.Embed(
            title="👑 Configurar Cargos de Administrador",
            description=(
                "Selecione os cargos que terão **permissões de administrador** no bot.\n\n"
                "**O que administradores podem fazer:**\n"
                "• Gerenciar todas as configurações do bot\n"
                "• Usar todos os comandos de moderação\n"
                "• Configurar permissões e cargos\n"
                "• Acessar a dashboard completa\n\n"
                "**💡 Dica:** Administradores do Discord sempre têm acesso total."
            ),
            color=0xFFAC33,
        )

        config: dict[str, Any] = await perm_system.get_guild_config(str(interaction.guild.id))
        current_roles: list[str] = config.get("admin_role_ids", "").split(",")
        current_roles = [r for r in current_roles if r]

        if current_roles:
            roles_text: str = "\n".join([f"<@&{rid}>" for rid in current_roles])
            embed.add_field(name="📋 Cargos Atuais", value=roles_text, inline=False)
        else:
            embed.add_field(
                name="📋 Cargos Atuais", value="*Nenhum cargo configurado*", inline=False
            )

        # Criar select com cargos do servidor
        select: Select = Select(
            placeholder="Selecione os cargos de administrador",
            min_values=0,
            max_values=min(25, len(interaction.guild.roles) - 1),
        )

        # Adicionar opção de limpar
        select.add_option(
            label="🗑️ Remover todos",
            value="CLEAR",
            description="Limpar todos os cargos de administrador",
        )

        # Adicionar cargos do servidor (exceto @everyone)
        for role in interaction.guild.roles[:24]:  # Limite Discord
            if role.id != interaction.guild.id:  # Não incluir @everyone
                select.add_option(
                    label=role.name[:100],
                    value=str(role.id),
                    emoji="👑" if str(role.id) in current_roles else None,
                )

        async def select_callback(select_interaction: discord.Interaction) -> None:
            if "CLEAR" in select.values:
                await perm_system.update_config(str(interaction.guild.id), admin_role_ids="")
                await select_interaction.response.send_message(
                    "✅ Cargos de administrador limpos!", ephemeral=True
                )
            else:
                role_ids: str = ",".join(select.values)
                await perm_system.update_config(str(interaction.guild.id), admin_role_ids=role_ids)
                roles_mention: list[str] = [f"<@&{rid}>" for rid in select.values]
                await select_interaction.response.send_message(
                    "✅ Cargos de administrador atualizados:\n" + "\n".join(roles_mention),
                    ephemeral=True,
                )

        select.callback = select_callback

        view: View = View(timeout=180)
        view.add_item(select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🛡️ Cargos Mod", style=discord.ButtonStyle.primary, emoji="🛡️")
    async def config_mod(self, interaction: discord.Interaction, button: Button) -> None:
        """Configurar cargos de moderador"""
        embed: discord.Embed = discord.Embed(
            title="🛡️ Configurar Cargos de Moderador",
            description=(
                "Selecione os cargos que terão **permissões de moderador** no bot.\n\n"
                "**O que moderadores podem fazer:**\n"
                "• Usar comandos de moderação (ban, kick, mute, warn)\n"
                "• Gerenciar mensagens e canais\n"
                "• Ver logs de moderação\n"
                "• Acessar painel de moderação na dashboard\n\n"
                "**💡 Nota:** Admins também têm acesso a todos os comandos de moderação."
            ),
            color=0x3498DB,
        )

        config: dict[str, Any] = await perm_system.get_guild_config(str(interaction.guild.id))
        current_roles: list[str] = config.get("mod_role_ids", "").split(",")
        current_roles = [r for r in current_roles if r]

        if current_roles:
            roles_text: str = "\n".join([f"<@&{rid}>" for rid in current_roles])
            embed.add_field(name="📋 Cargos Atuais", value=roles_text, inline=False)
        else:
            embed.add_field(
                name="📋 Cargos Atuais", value="*Nenhum cargo configurado*", inline=False
            )

        # Criar select
        select: Select = Select(
            placeholder="Selecione os cargos de moderador",
            min_values=0,
            max_values=min(25, len(interaction.guild.roles) - 1),
        )

        select.add_option(label="🗑️ Remover todos", value="CLEAR")

        for role in interaction.guild.roles[:24]:
            if role.id != interaction.guild.id:
                select.add_option(
                    label=role.name[:100],
                    value=str(role.id),
                    emoji="🛡️" if str(role.id) in current_roles else None,
                )

        async def select_callback(select_interaction: discord.Interaction) -> None:
            if "CLEAR" in select.values:
                await perm_system.update_config(str(interaction.guild.id), mod_role_ids="")
                await select_interaction.response.send_message(
                    "✅ Cargos de moderador limpos!", ephemeral=True
                )
            else:
                role_ids: str = ",".join(select.values)
                await perm_system.update_config(str(interaction.guild.id), mod_role_ids=role_ids)
                roles_mention: list[str] = [f"<@&{rid}>" for rid in select.values]
                await select_interaction.response.send_message(
                    "✅ Cargos de moderador atualizados:\n" + "\n".join(roles_mention),
                    ephemeral=True,
                )

        select.callback = select_callback

        view: View = View(timeout=180)
        view.add_item(select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🎵 Cargos DJ", style=discord.ButtonStyle.primary, emoji="🎵")
    async def config_dj(self, interaction: discord.Interaction, button: Button) -> None:
        """Configurar cargos de DJ"""
        embed: discord.Embed = discord.Embed(
            title="🎵 Configurar Cargos de DJ",
            description=(
                "Selecione os cargos que terão **permissões de DJ** no bot.\n\n"
                "**O que DJs podem fazer:**\n"
                "• Controlar a fila de músicas\n"
                "• Pular, pausar e parar músicas\n"
                "• Ajustar volume\n"
                "• Remover músicas da fila\n\n"
                "**💡 Nota:** Se nenhum cargo for configurado, todos podem usar comandos de música."
            ),
            color=0xE91E63,
        )

        config: dict[str, Any] = await perm_system.get_guild_config(str(interaction.guild.id))
        current_roles: list[str] = config.get("dj_role_ids", "").split(",")
        current_roles = [r for r in current_roles if r]
        require_dj: bool = config.get("require_roles_for_music", False)

        if current_roles:
            roles_text: str = "\n".join([f"<@&{rid}>" for rid in current_roles])
            embed.add_field(name="📋 Cargos Atuais", value=roles_text, inline=False)
        else:
            embed.add_field(
                name="📋 Cargos Atuais", value="*Nenhum cargo configurado*", inline=False
            )

        embed.add_field(
            name="⚙️ Status",
            value=f"Restringir música a DJs: **{'✅ Sim' if require_dj else '❌ Não'}**",
            inline=False,
        )

        # Criar view com select e botão de toggle
        view: View = View(timeout=180)

        select: Select = Select(
            placeholder="Selecione os cargos de DJ",
            min_values=0,
            max_values=min(25, len(interaction.guild.roles) - 1),
        )

        select.add_option(label="🗑️ Remover todos", value="CLEAR")

        for role in interaction.guild.roles[:24]:
            if role.id != interaction.guild.id:
                select.add_option(
                    label=role.name[:100],
                    value=str(role.id),
                    emoji="🎵" if str(role.id) in current_roles else None,
                )

        async def select_callback(select_interaction: discord.Interaction) -> None:
            if "CLEAR" in select.values:
                await perm_system.update_config(str(interaction.guild.id), dj_role_ids="")
                await select_interaction.response.send_message(
                    "✅ Cargos de DJ limpos!", ephemeral=True
                )
            else:
                role_ids: str = ",".join(select.values)
                await perm_system.update_config(str(interaction.guild.id), dj_role_ids=role_ids)
                roles_mention: list[str] = [f"<@&{rid}>" for rid in select.values]
                await select_interaction.response.send_message(
                    "✅ Cargos de DJ atualizados:\n" + "\n".join(roles_mention), ephemeral=True
                )

        select.callback = select_callback
        view.add_item(select)

        # Botão de toggle restrição
        toggle_btn: Button = Button(label="🔄 Toggle Restrição", style=discord.ButtonStyle.secondary)

        async def toggle_callback(btn_interaction: discord.Interaction) -> None:
            new_value: bool = not require_dj
            await perm_system.update_config(
                str(interaction.guild.id), require_roles_for_music=new_value
            )
            await btn_interaction.response.send_message(
                f"✅ Restrição de música: **{'✅ Ativada' if new_value else '❌ Desativada'}**",
                ephemeral=True,
            )

        toggle_btn.callback = toggle_callback
        view.add_item(toggle_btn)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="📊 Dashboard", style=discord.ButtonStyle.success, emoji="📊")
    async def dashboard_info(self, interaction: discord.Interaction, button: Button) -> None:
        """Informações sobre a dashboard"""
        config: dict[str, Any] = await perm_system.get_guild_config(str(interaction.guild.id))
        analytics: dict[str, Any] = await perm_system.get_analytics(str(interaction.guild.id), days=7)

        embed: discord.Embed = discord.Embed(
            title="📊 Dashboard do Bot",
            description=(
                "A dashboard web permite configurar o bot de forma visual e intuitiva!\n\n"
                "**Recursos Disponíveis:**\n"
                "🎨 Editor visual de embeds\n"
                "📈 Analytics de comandos\n"
                "⚙️ Configurações avançadas\n"
                "🛡️ Gestão de permissões\n"
                "📝 Logs em tempo real\n\n"
                f"**Status:** {'🟢 Ativada' if config.get('dashboard_enabled') else '🔴 Desativada'}"
            ),
            color=0x2ECC71,
        )

        # Estatísticas dos últimos 7 dias
        if analytics["total_commands"] > 0:
            top_cmds: list[dict[str, Any]] = analytics["top_commands"][:5]
            top_text: str = "\n".join(
                [
                    f"`{i + 1}.` {cmd['command_name']} - {cmd['count']} usos"
                    for i, cmd in enumerate(top_cmds)
                ]
            )

            embed.add_field(
                name="📈 Top 5 Comandos (7 dias)",
                value=top_text or "*Nenhum uso registrado*",
                inline=False,
            )

            embed.add_field(
                name="✅ Taxa de Sucesso", value=f"**{analytics['success_rate']}%**", inline=True
            )

            embed.add_field(
                name="📊 Total de Comandos", value=f"**{analytics['total_commands']}**", inline=True
            )

        embed.set_footer(text="Acesse a dashboard web para mais detalhes!")

        await interaction.response.send_message(embed=embed, ephemeral=True)


class ConfigCommands(commands.Cog):
    """Comandos de configuração do bot"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        # Inicializar sistema de permissões
        self.bot.loop.create_task(perm_system.initialize())

    @app_commands.command(name="config", description="⚙️ Configurar permissões e cargos do bot")
    @app_commands.checks.has_permissions(administrator=True)
    async def config(self, interaction: discord.Interaction) -> None:
        """Painel de configuração do bot"""

        embed: discord.Embed = discord.Embed(
            title="⚙️ Configuração do Bot",
            description=(
                "**Bem-vindo ao painel de configuração!**\n\n"
                "Use os botões abaixo para configurar:\n"
                "👑 **Cargos Admin** - Acesso total ao bot\n"
                "🛡️ **Cargos Mod** - Comandos de moderação\n"
                "🎵 **Cargos DJ** - Controle de música\n"
                "📊 **Dashboard** - Estatísticas e analytics\n\n"
                "**💡 Dica:** Administradores do Discord sempre têm acesso total!"
            ),
            color=0x3498DB,
            timestamp=discord.utils.utcnow(),
        )

        # Mostrar configuração atual
        config: dict[str, Any] = await perm_system.get_guild_config(str(interaction.guild.id))

        admin_count: int = len([r for r in config.get("admin_role_ids", "").split(",") if r])
        mod_count: int = len([r for r in config.get("mod_role_ids", "").split(",") if r])
        dj_count: int = len([r for r in config.get("dj_role_ids", "").split(",") if r])

        embed.add_field(
            name="📊 Status Atual",
            value=(
                f"👑 Cargos Admin: **{admin_count}**\n"
                f"🛡️ Cargos Mod: **{mod_count}**\n"
                f"🎵 Cargos DJ: **{dj_count}**\n"
                f"📊 Dashboard: **{'✅ Ativa' if config.get('dashboard_enabled') else '❌ Inativa'}**"
            ),
            inline=False,
        )

        embed.set_footer(text=f"Configurado por {interaction.user.display_name}")

        view: ConfigView = ConfigView(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @config.error
    async def config_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "❌ **Sem Permissão**\nApenas administradores podem usar este comando!",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ConfigCommands(bot))
