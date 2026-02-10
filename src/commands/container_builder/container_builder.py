"""
Comando Container Builder - Python Version
Sistema avançado de criação de containers Discord
"""


import discord
from discord import app_commands
from discord.ext import commands

from ...utils.container_templates import ContainerTemplateManager


class ContainerBuilderCog(commands.Cog):
    """Cog para construção de containers avançados"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.template_manager = ContainerTemplateManager()
        self.active_containers = {}  # Session management

    @app_commands.command(
        name="container-builder", description="Sistema avançado de criação de containers Discord"
    )
    @app_commands.describe()
    async def container_builder(self, interaction: discord.Interaction):
        """Comando principal para construção de containers"""

        # Verificar permissões
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar containers.", ephemeral=True
            )
            return

        # Criar embed de introdução
        embed = discord.Embed(
            title="📦 Container Builder - Components V2",
            description=(
                "Sistema avançado de criação de containers Discord!\n\n"
                "**O que são Containers?**\n"
                "Os novos Components V2 do Discord são uma evolução dos embeds tradicionais, permitindo:\n"
                "• Layout totalmente personalizado\n"
                "• Combinação de texto, imagens, botões e menus\n"
                "• Cores de destaque customizáveis\n"
                "• Organização visual superior\n\n"
                "**Tipos de Components:**\n"
                "🎨 **Layout:** Section, Container, Separator\n"
                "📄 **Conteúdo:** Text Display, Media Gallery, Thumbnail\n"
                "⚡ **Interativos:** Buttons, Select Menus"
            ),
            color=0x5865F2,
        )

        embed.add_field(
            name="📋 Tipos Disponíveis",
            value=(
                "**Container:** Agrupa components com cor de destaque\n"
                "**Section:** Combina texto com acessório\n"
                "**Text Display:** Texto rich com markdown"
            ),
            inline=True,
        )

        embed.add_field(
            name="🎯 Recursos",
            value=(
                "**Separators:** Espaçamento visual\n"
                "**Media Gallery:** Galeria de imagens\n"
                "**File Display:** Arquivos anexos"
            ),
            inline=True,
        )

        embed.set_footer(text="Selecione um tipo para começar!")

        # Criar select menu
        select = ContainerTypeSelect(self.template_manager, self.active_containers)
        view = discord.ui.View()
        view.add_item(select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ContainerTypeSelect(discord.ui.Select):
    """Select menu para escolha do tipo de container"""

    def __init__(self, template_manager: ContainerTemplateManager, active_containers: dict):
        self.template_manager = template_manager
        self.active_containers = active_containers

        options = [
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
        ]

        super().__init__(
            placeholder="🔽 Escolha o tipo de container para criar...",
            options=options,
            custom_id="container_type_select",
        )

    async def callback(self, interaction: discord.Interaction):
        """Callback para seleção do tipo de container"""
        print(f"🔧 Debug - Tipo selecionado: {self.values[0]}")
        print(f"🔧 Debug - User ID: {interaction.user.id}")

        try:
            selected_type = self.values[0]

            # Verificar se o template existe
            template = self.template_manager.get_container_template(selected_type)
            if not template:
                await interaction.response.send_message(
                    f"❌ Tipo de container inválido: {selected_type}!", ephemeral=True
                )
                return

            print(f"✅ Debug - Template encontrado: {template['name']}")

            # Criar container ativo
            container_id = f"{interaction.user.id}_{selected_type}_{interaction.id}"
            default_config = self.template_manager.get_default_configurations().get(
                selected_type, template["config"]
            )

            container_data = {
                "user_id": interaction.user.id,
                "type": selected_type,
                "template": template,
                "config": default_config.copy(),
                "created_at": discord.utils.utcnow(),
            }

            self.active_containers[container_id] = container_data
            print(f"🔧 Debug - Container criado: {container_id}")

            # Criar embed de configuração
            embed = discord.Embed(
                title=f"🔧 Configurando: {template['name']}",
                description=(
                    f"{template['description']}\n\n"
                    f"**Container ID:** `{container_id[:20]}...`\n"
                    f"**Tipo:** {selected_type}"
                ),
                color=0x00FF7F,
            )

            embed.add_field(name="📋 Status", value="Em configuração...", inline=True)
            embed.add_field(name="🎨 Tipo", value=template["name"], inline=True)
            embed.add_field(name="🆔 ID", value=container_id[:20] + "...", inline=True)
            embed.set_footer(text="Use os botões abaixo para personalizar seu container")

            # Criar botões de configuração
            view = ContainerConfigView(container_id, self.active_containers, self.template_manager)

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as error:
            print(f"❌ Debug - Erro em callback: {error}")
            await interaction.response.send_message(f"❌ Erro interno: {error}", ephemeral=True)


class ContainerConfigView(discord.ui.View):
    """View para configuração de containers"""

    def __init__(
        self, container_id: str, active_containers: dict, template_manager: ContainerTemplateManager
    ):
        super().__init__(timeout=900)  # 15 minutos
        self.container_id = container_id
        self.active_containers = active_containers
        self.template_manager = template_manager

    @discord.ui.button(label="✏️ Editar Texto", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_text(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Editar texto do container"""
        await self._show_text_modal(interaction)

    @discord.ui.button(label="🎨 Cor", style=discord.ButtonStyle.secondary, emoji="🎨")
    async def edit_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Editar cor do container"""
        await self._show_color_modal(interaction)

    @discord.ui.button(label="🖼️ Imagem", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def edit_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Editar imagens do container"""
        await self._show_image_modal(interaction)

    @discord.ui.button(label="👀 Preview", style=discord.ButtonStyle.secondary, emoji="👀")
    async def preview_container(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Visualizar preview do container"""
        await self._show_preview(interaction)

    @discord.ui.button(label="📤 Enviar", style=discord.ButtonStyle.success, emoji="📤")
    async def send_container(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Enviar container para o canal"""
        await self._send_container(interaction)

    async def _show_text_modal(self, interaction: discord.Interaction):
        """Mostrar modal para edição de texto"""
        container = self.active_containers.get(self.container_id)
        if not container or container["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Container não encontrado!", ephemeral=True)
            return

        modal = TextEditModal(self.container_id, self.active_containers, container["config"])
        await interaction.response.send_modal(modal)

    async def _show_color_modal(self, interaction: discord.Interaction):
        """Mostrar modal para edição de cor"""
        container = self.active_containers.get(self.container_id)
        if not container or container["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Container não encontrado!", ephemeral=True)
            return

        modal = ColorEditModal(self.container_id, self.active_containers, container["config"])
        await interaction.response.send_modal(modal)

    async def _show_image_modal(self, interaction: discord.Interaction):
        """Mostrar modal para edição de imagem"""
        container = self.active_containers.get(self.container_id)
        if not container or container["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Container não encontrado!", ephemeral=True)
            return

        modal = ImageEditModal(self.container_id, self.active_containers, container["config"])
        await interaction.response.send_modal(modal)

    async def _show_preview(self, interaction: discord.Interaction):
        """Mostrar preview do container"""
        container = self.active_containers.get(self.container_id)
        if not container or container["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Container não encontrado!", ephemeral=True)
            return

        # Construir embed do preview
        embed = self.template_manager.build_discord_embed(container["config"])
        view = self.template_manager.build_container_view(container["config"])

        await interaction.response.send_message(
            content="📋 **Preview do Container:**", embed=embed, view=view, ephemeral=True
        )

    async def _send_container(self, interaction: discord.Interaction):
        """Enviar container para o canal"""
        container = self.active_containers.get(self.container_id)
        if not container or container["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Container não encontrado!", ephemeral=True)
            return

        try:
            # Construir embed e view
            embed = self.template_manager.build_discord_embed(container["config"])
            view = self.template_manager.build_container_view(container["config"])

            # Enviar no canal
            if view:
                await interaction.channel.send(embed=embed, view=view)
            else:
                await interaction.channel.send(embed=embed)

            await interaction.response.send_message(
                "✅ Container enviado com sucesso!", ephemeral=True
            )

            # Limpar container da memória
            del self.active_containers[self.container_id]

        except Exception as error:
            await interaction.response.send_message(
                f"❌ Erro ao enviar container: {error}", ephemeral=True
            )


class TextEditModal(discord.ui.Modal):
    """Modal para edição de texto"""

    def __init__(self, container_id: str, active_containers: dict, config: dict):
        super().__init__(title="✏️ Editar Texto do Container")
        self.container_id = container_id
        self.active_containers = active_containers
        self.config = config

        # Campos do modal
        self.title_input = discord.ui.TextInput(
            label="Título",
            placeholder="Digite o título do container...",
            default=config.get("title", ""),
            max_length=256,
            required=False,
        )

        self.description_input = discord.ui.TextInput(
            label="Descrição",
            placeholder="Digite a descrição do container...",
            default=config.get("description", ""),
            style=discord.TextStyle.paragraph,
            max_length=4000,
            required=False,
        )

        self.footer_input = discord.ui.TextInput(
            label="Rodapé",
            placeholder="Digite o texto do rodapé...",
            default=config.get("footer", ""),
            max_length=2048,
            required=False,
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.footer_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Processar submissão do modal"""
        container = self.active_containers.get(self.container_id)
        if not container or container["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Container não encontrado!", ephemeral=True)
            return

        # Atualizar configuração
        if self.title_input.value:
            container["config"]["title"] = self.title_input.value

        if self.description_input.value:
            container["config"]["description"] = self.description_input.value

        if self.footer_input.value:
            container["config"]["footer"] = self.footer_input.value

        await interaction.response.send_message("✅ Texto atualizado com sucesso!", ephemeral=True)


class ColorEditModal(discord.ui.Modal):
    """Modal para edição de cor"""

    def __init__(self, container_id: str, active_containers: dict, config: dict):
        super().__init__(title="🎨 Editar Cor do Container")
        self.container_id = container_id
        self.active_containers = active_containers
        self.config = config

        current_color = config.get("accent_color", 0x5865F2)
        current_hex = f"#{current_color:06X}" if current_color else "#5865F2"

        self.color_input = discord.ui.TextInput(
            label="Cor (Hex)",
            placeholder="#5865F2",
            default=current_hex,
            max_length=7,
            required=True,
        )

        self.add_item(self.color_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Processar submissão da cor"""
        container = self.active_containers.get(self.container_id)
        if not container or container["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Container não encontrado!", ephemeral=True)
            return

        try:
            # Converter hex para int
            hex_color = self.color_input.value.replace("#", "")
            color_int = int(hex_color, 16)

            container["config"]["accent_color"] = color_int

            await interaction.response.send_message(
                f"✅ Cor atualizada para {self.color_input.value}!", ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message(
                "❌ Cor inválida! Use o formato #FFFFFF", ephemeral=True
            )


class ImageEditModal(discord.ui.Modal):
    """Modal para edição de imagens"""

    def __init__(self, container_id: str, active_containers: dict, config: dict):
        super().__init__(title="🖼️ Editar Imagens do Container")
        self.container_id = container_id
        self.active_containers = active_containers
        self.config = config

        self.thumbnail_input = discord.ui.TextInput(
            label="URL da Thumbnail",
            placeholder="https://exemplo.com/imagem.png",
            default=config.get("thumbnail", ""),
            required=False,
        )

        self.image_input = discord.ui.TextInput(
            label="URL da Imagem Principal",
            placeholder="https://exemplo.com/imagem-grande.png",
            default=config.get("image", ""),
            required=False,
        )

        self.add_item(self.thumbnail_input)
        self.add_item(self.image_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Processar submissão das imagens"""
        container = self.active_containers.get(self.container_id)
        if not container or container["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Container não encontrado!", ephemeral=True)
            return

        # Atualizar imagens
        if self.thumbnail_input.value:
            container["config"]["thumbnail"] = self.thumbnail_input.value

        if self.image_input.value:
            container["config"]["image"] = self.image_input.value

        await interaction.response.send_message(
            "✅ Imagens atualizadas com sucesso!", ephemeral=True
        )


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(ContainerBuilderCog(bot))
