"""
Comando Container Builder - Utility
Sistema avançado de criação de containers Discord
"""

import discord
from discord import app_commands
from discord.ext import commands


class ContainerBuilderCommand(commands.Cog):
    """Sistema de construção de containers"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="container-builder",
        description="Sistema avançado de criação de containers Discord (Components V2)",
    )
    async def container_builder(self, interaction: discord.Interaction):
        """Abrir o construtor de containers"""

        # Verificar permissões
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar containers.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📦 Container Builder - Components V2",
            description="""Sistema avançado de criação de containers Discord!

**O que são Containers?**
Os novos Components V2 do Discord são uma evolução dos embeds tradicionais, permitindo:
• Layout totalmente personalizado
• Combinação de texto, imagens, botões e menus
• Cores de destaque customizáveis
• Organização visual superior

**Tipos de Components:**
🎨 **Layout:** Section, Container, Separator
📄 **Conteúdo:** Text Display, Media Gallery, Thumbnail
⚡ **Interativos:** Buttons, Select Menus""",
            color=0x5865F2,
        )

        embed.add_field(
            name="📋 Tipos Disponíveis",
            value="**Container:** Agrupa components com cor de destaque\n**Section:** Combina texto com acessório\n**Text Display:** Texto rich com markdown",
            inline=True,
        )

        embed.add_field(
            name="🎯 Recursos",
            value="**Separators:** Espaçamento visual\n**Media Gallery:** Galeria de imagens\n**File Display:** Arquivos anexos",
            inline=True,
        )

        embed.set_footer(text="Selecione um tipo para começar!")

        # Menu de seleção com os tipos de containers
        select = discord.ui.Select(
            placeholder="🔽 Escolha o tipo de container para criar...",
            options=[
                discord.SelectOption(
                    label="🌟 Embed Profissional",
                    description="Container estilo Rio Bot - Layout profissional",
                    value="rio_embed_style",
                    emoji="🌟",
                ),
                discord.SelectOption(
                    label="📊 Dashboard Interativo",
                    description="Painel de controle com estatísticas (Premium)",
                    value="dashboard_style",
                    emoji="📊",
                ),
                discord.SelectOption(
                    label="🎉 Boas-vindas Premium",
                    description="Sistema de boas-vindas profissional",
                    value="welcome_premium",
                    emoji="🎉",
                ),
                discord.SelectOption(
                    label="📢 Anúncio Profissional",
                    description="Template para anúncios importantes",
                    value="announcement_pro",
                    emoji="📢",
                ),
                discord.SelectOption(
                    label="📦 Container Básico",
                    description="Container simples para começar",
                    value="simple_container",
                    emoji="📦",
                ),
                discord.SelectOption(
                    label="🔘 Container Interativo",
                    description="Container avançado com botões e interações",
                    value="container_with_buttons",
                    emoji="🔘",
                ),
                discord.SelectOption(
                    label="🎨 Galeria Premium",
                    description="Galeria avançada com múltiplas imagens",
                    value="media_gallery",
                    emoji="🎨",
                ),
                discord.SelectOption(
                    label="⚡ Sistema Enterprise",
                    description="Container empresarial com recursos avançados",
                    value="advanced_container",
                    emoji="⚡",
                ),
                discord.SelectOption(
                    label="🛠️ Template Personalizado",
                    description="Construtor avançado para templates personalizados",
                    value="custom_template",
                    emoji="🛠️",
                ),
            ],
        )

        async def select_callback(select_interaction):
            await select_interaction.response.defer(ephemeral=True)

            # Importar o sistema de containers
            from ...utils.container_templates import get_container_template

            try:
                # Obter o template selecionado
                template_data = get_container_template(select_interaction.values[0])

                if not template_data:
                    await select_interaction.followup.send(
                        "❌ Template não encontrado! Verifique se o sistema de containers está configurado corretamente.",
                        ephemeral=True,
                    )
                    return

                # Criar o embed do template
                template_embed = discord.Embed(
                    title=template_data.get("title", "Container"),
                    description=template_data.get("description", "Template de container"),
                    color=int(template_data.get("color", "5865F2"), 16),
                )

                # Adicionar campos se existirem
                fields = template_data.get("fields", [])
                for field in fields[:25]:  # Limite do Discord
                    template_embed.add_field(
                        name=field.get("name", "Campo"),
                        value=field.get("value", "Valor"),
                        inline=field.get("inline", False),
                    )

                # Adicionar imagem se existir
                if template_data.get("image"):
                    template_embed.set_image(url=template_data["image"])

                # Adicionar thumbnail se existir
                if template_data.get("thumbnail"):
                    template_embed.set_thumbnail(url=template_data["thumbnail"])

                # Adicionar footer
                template_embed.set_footer(
                    text=f"Container criado por {select_interaction.user} • Template: {select_interaction.values[0]}",
                    icon_url=select_interaction.user.display_avatar.url,
                )

                # Criar botões se existirem
                view = None
                buttons = template_data.get("buttons", [])
                if buttons:
                    view = discord.ui.View(timeout=300)
                    for i, button_data in enumerate(buttons[:25]):  # Limite do Discord
                        button = discord.ui.Button(
                            label=button_data.get("label", f"Botão {i + 1}"),
                            style=getattr(
                                discord.ButtonStyle,
                                button_data.get("style", "secondary").lower(),
                                discord.ButtonStyle.secondary,
                            ),
                            emoji=button_data.get("emoji"),
                            url=button_data.get("url"),
                        )
                        view.add_item(button)

                await select_interaction.followup.send(
                    f"✅ Container **{select_interaction.values[0]}** criado com sucesso!\n\n"
                    f"📋 **Preview do Template:**",
                    embed=template_embed,
                    view=view,
                    ephemeral=True,
                )

            except Exception as e:
                await select_interaction.followup.send(
                    f"❌ Erro ao criar container: `{e!s}`\n"
                    f"Verifique se o sistema de containers está configurado corretamente.",
                    ephemeral=True,
                )

        select.callback = select_callback

        view = discord.ui.View(timeout=300)
        view.add_item(select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(ContainerBuilderCommand(bot))
