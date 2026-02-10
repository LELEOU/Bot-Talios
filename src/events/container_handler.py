"""
Container Handler - Python Version
Handler para eventos e interações de containers
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any

import discord
from discord.ext import commands

from ..utils.container_templates import ContainerTemplateManager


class ContainerHandler:
    """Handler para gerenciamento de containers ativos"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.template_manager = ContainerTemplateManager()
        self.active_containers: dict[str, dict[str, Any]] = {}
        self.cleanup_task = None
        self._processed_interactions = set()  # Cache para evitar processamento duplo

    async def start_cleanup_task(self):
        """Iniciar task de limpeza (deve ser chamado após o bot estar pronto)"""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self.cleanup_expired_containers())

    async def handle_interaction(self, interaction: discord.Interaction):
        """
        Handler principal para interações de containers

        Args:
            interaction (discord.Interaction): Interação recebida
        """
        # Verificar se a interação já foi processada usando cache de IDs
        interaction_id = f"{interaction.id}_{interaction.user.id}_container"
        if interaction_id in self._processed_interactions:
            print("⚠️ Container: Interação já processada")
            return
        self._processed_interactions.add(interaction_id)

        # Limpar cache periodicamente
        if len(self._processed_interactions) > 500:
            self._processed_interactions = set(list(self._processed_interactions)[-250:])

        print(f"🔧 Debug - Interação recebida: {interaction.data.get('custom_id', 'N/A')}")

        custom_id = interaction.data.get("custom_id", "")

        # Container type selection
        if custom_id == "container_type_select":
            await self.handle_container_type_selection(interaction)

        # Container configuration
        elif custom_id.startswith("container_config_"):
            await self.handle_container_config(interaction)

        # Container preview
        elif custom_id.startswith("container_preview_"):
            await self.handle_container_preview(interaction)

        # Container send
        elif custom_id.startswith("container_send_"):
            await self.handle_container_send(interaction)

        # Modal submissions
        elif custom_id.startswith("container_modal_"):
            await self.handle_container_modal(interaction)

    async def handle_container_type_selection(self, interaction: discord.Interaction):
        """
        Lidar com seleção de tipo de container

        Args:
            interaction (discord.Interaction): Interação de select menu
        """
        print("🔧 Debug - Iniciando handle_container_type_selection")
        print(f"🔧 Debug - Interaction values: {interaction.data.get('values', [])}")
        print(f"🔧 Debug - User ID: {interaction.user.id}")

        try:
            # Verificar se já foi respondida
            if interaction.response.is_done():
                print("⚠️ Interação já foi processada")
                return

            values = interaction.data.get("values", [])
            if not values:
                await interaction.response.send_message(
                    "❌ Nenhum tipo de container foi selecionado!", ephemeral=True
                )
                return

            selected_type = values[0]
            print(f"🔧 Debug - Tipo selecionado: {selected_type}")

            # Verificar se o template existe
            template = self.template_manager.get_container_template(selected_type)
            if not template:
                print(f"❌ Debug - Template não encontrado para tipo: {selected_type}")
                await interaction.response.send_message(
                    f"❌ Tipo de container inválido: {selected_type}!", ephemeral=True
                )
                return

            print(f"✅ Debug - Template encontrado: {template['name']}")

            # Criar container ativo
            container_id = f"{interaction.user.id}_{selected_type}_{uuid.uuid4().hex[:8]}"

            # Obter configuração padrão
            default_configs = self.template_manager.get_default_configurations()
            default_config = default_configs.get(selected_type, template["config"]).copy()

            container_data = {
                "user_id": interaction.user.id,
                "type": selected_type,
                "template": template,
                "config": default_config,
                "created_at": datetime.utcnow(),
            }

            self.active_containers[container_id] = container_data
            print(f"🔧 Debug - Container criado com ID: {container_id}")
            print(f"🔧 Debug - Containers ativos: {len(self.active_containers)}")

            # Criar embed de configuração
            embed = discord.Embed(
                title=f"🔧 Configurando: {template['name']}",
                description=(
                    f"{template['description']}\n\n"
                    f"**Container ID:** `{container_id}`\n"
                    f"**Tipo:** {selected_type}"
                ),
                color=0x00FF7F,
            )

            embed.add_field(name="📋 Status", value="Em configuração...", inline=True)
            embed.add_field(name="🎨 Tipo", value=template["name"], inline=True)
            embed.add_field(name="🆔 ID", value=container_id[:20] + "...", inline=True)
            embed.set_footer(text="Use os botões abaixo para personalizar seu container")

            # Criar view de configuração
            view = self.create_config_view(container_id, selected_type)

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            print("✅ Debug - Resposta enviada com sucesso")

        except Exception as error:
            print(f"❌ Debug - Erro em handle_container_type_selection: {error}")
            await self.safe_respond(interaction, f"❌ Erro interno: {error}")

    def create_config_view(self, container_id: str, container_type: str) -> discord.ui.View:
        """
        Criar view de configuração para container

        Args:
            container_id (str): ID do container
            container_type (str): Tipo do container

        Returns:
            discord.ui.View: View com botões de configuração
        """
        view = discord.ui.View(timeout=900)  # 15 minutos

        # Botão para editar texto
        text_button = discord.ui.Button(
            label="✏️ Texto",
            style=discord.ButtonStyle.primary,
            custom_id=f"container_config_{container_id}_text",
            emoji="✏️",
        )
        text_button.callback = self.create_button_callback("text", container_id)
        view.add_item(text_button)

        # Botão para editar cor
        color_button = discord.ui.Button(
            label="🎨 Cor",
            style=discord.ButtonStyle.secondary,
            custom_id=f"container_config_{container_id}_color",
            emoji="🎨",
        )
        color_button.callback = self.create_button_callback("color", container_id)
        view.add_item(color_button)

        # Botão para editar imagem
        image_button = discord.ui.Button(
            label="🖼️ Imagem",
            style=discord.ButtonStyle.secondary,
            custom_id=f"container_config_{container_id}_image",
            emoji="🖼️",
        )
        image_button.callback = self.create_button_callback("image", container_id)
        view.add_item(image_button)

        # Botão de preview
        preview_button = discord.ui.Button(
            label="👀 Preview",
            style=discord.ButtonStyle.secondary,
            custom_id=f"container_preview_{container_id}",
            emoji="👀",
        )
        preview_button.callback = self.create_button_callback("preview", container_id)
        view.add_item(preview_button)

        # Botão de envio
        send_button = discord.ui.Button(
            label="📤 Enviar",
            style=discord.ButtonStyle.success,
            custom_id=f"container_send_{container_id}",
            emoji="📤",
        )
        send_button.callback = self.create_button_callback("send", container_id)
        view.add_item(send_button)

        return view

    def create_button_callback(self, action: str, container_id: str):
        """
        Criar callback para botões de configuração

        Args:
            action (str): Ação do botão
            container_id (str): ID do container

        Returns:
            Callable: Função callback
        """

        async def button_callback(interaction: discord.Interaction):
            container = self.active_containers.get(container_id)
            if not container or container["user_id"] != interaction.user.id:
                await self.safe_respond(
                    interaction, "❌ Container não encontrado ou você não tem permissão!"
                )
                return

            if action == "text":
                await self.show_text_modal(interaction, container_id)
            elif action == "color":
                await self.show_color_modal(interaction, container_id)
            elif action == "image":
                await self.show_image_modal(interaction, container_id)
            elif action == "preview":
                await self.show_preview(interaction, container_id)
            elif action == "send":
                await self.send_container(interaction, container_id)

        return button_callback

    async def show_text_modal(self, interaction: discord.Interaction, container_id: str):
        """Mostrar modal de edição de texto"""
        container = self.active_containers.get(container_id)
        config = container["config"]

        class TextModal(discord.ui.Modal):
            def __init__(self):
                super().__init__(title="✏️ Editar Texto")

                self.title_input = discord.ui.TextInput(
                    label="Título",
                    placeholder="Digite o título...",
                    default=config.get("title", ""),
                    max_length=256,
                    required=False,
                )

                self.description_input = discord.ui.TextInput(
                    label="Descrição",
                    placeholder="Digite a descrição...",
                    default=config.get("description", ""),
                    style=discord.TextStyle.paragraph,
                    max_length=4000,
                    required=False,
                )

                self.footer_input = discord.ui.TextInput(
                    label="Rodapé",
                    placeholder="Digite o rodapé...",
                    default=config.get("footer", ""),
                    max_length=2048,
                    required=False,
                )

                self.add_item(self.title_input)
                self.add_item(self.description_input)
                self.add_item(self.footer_input)

            async def on_submit(self, modal_interaction):
                # Atualizar configuração
                if self.title_input.value:
                    config["title"] = self.title_input.value
                if self.description_input.value:
                    config["description"] = self.description_input.value
                if self.footer_input.value:
                    config["footer"] = self.footer_input.value

                await modal_interaction.response.send_message(
                    "✅ Texto atualizado com sucesso!", ephemeral=True
                )

        modal = TextModal()
        await interaction.response.send_modal(modal)

    async def show_color_modal(self, interaction: discord.Interaction, container_id: str):
        """Mostrar modal de edição de cor"""
        container = self.active_containers.get(container_id)
        config = container["config"]

        current_color = config.get("accent_color", 0x5865F2)
        current_hex = f"#{current_color:06X}"

        class ColorModal(discord.ui.Modal):
            def __init__(self):
                super().__init__(title="🎨 Editar Cor")

                self.color_input = discord.ui.TextInput(
                    label="Cor (Hex)",
                    placeholder="#5865F2",
                    default=current_hex,
                    max_length=7,
                    required=True,
                )
                self.add_item(self.color_input)

            async def on_submit(self, modal_interaction):
                try:
                    hex_color = self.color_input.value.replace("#", "")
                    color_int = int(hex_color, 16)
                    config["accent_color"] = color_int

                    await modal_interaction.response.send_message(
                        f"✅ Cor atualizada para {self.color_input.value}!", ephemeral=True
                    )
                except ValueError:
                    await modal_interaction.response.send_message(
                        "❌ Cor inválida! Use o formato #FFFFFF", ephemeral=True
                    )

        modal = ColorModal()
        await interaction.response.send_modal(modal)

    async def show_image_modal(self, interaction: discord.Interaction, container_id: str):
        """Mostrar modal de edição de imagem"""
        container = self.active_containers.get(container_id)
        config = container["config"]

        class ImageModal(discord.ui.Modal):
            def __init__(self):
                super().__init__(title="🖼️ Editar Imagens")

                self.thumbnail_input = discord.ui.TextInput(
                    label="URL da Thumbnail",
                    placeholder="https://exemplo.com/thumb.png",
                    default=config.get("thumbnail", ""),
                    required=False,
                )

                self.image_input = discord.ui.TextInput(
                    label="URL da Imagem Principal",
                    placeholder="https://exemplo.com/imagem.png",
                    default=config.get("image", ""),
                    required=False,
                )

                self.add_item(self.thumbnail_input)
                self.add_item(self.image_input)

            async def on_submit(self, modal_interaction):
                if self.thumbnail_input.value:
                    config["thumbnail"] = self.thumbnail_input.value
                if self.image_input.value:
                    config["image"] = self.image_input.value

                await modal_interaction.response.send_message(
                    "✅ Imagens atualizadas com sucesso!", ephemeral=True
                )

        modal = ImageModal()
        await interaction.response.send_modal(modal)

    async def show_preview(self, interaction: discord.Interaction, container_id: str):
        """Mostrar preview do container"""
        container = self.active_containers.get(container_id)

        # Construir embed e view
        embed = self.template_manager.build_discord_embed(container["config"])
        view = self.template_manager.build_container_view(container["config"])

        await interaction.response.send_message(
            content="📋 **Preview do Container:**", embed=embed, view=view, ephemeral=True
        )

    async def send_container(self, interaction: discord.Interaction, container_id: str):
        """Enviar container para o canal"""
        container = self.active_containers.get(container_id)

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
            if container_id in self.active_containers:
                del self.active_containers[container_id]

        except Exception as error:
            await self.safe_respond(interaction, f"❌ Erro ao enviar container: {error}")

    async def safe_respond(self, interaction: discord.Interaction, content: str):
        """
        Responder de forma segura à interação

        Args:
            interaction (discord.Interaction): Interação
            content (str): Conteúdo da resposta
        """
        try:
            if interaction.response.is_done():
                await interaction.followup.send(content, ephemeral=True)
            else:
                await interaction.response.send_message(content, ephemeral=True)
        except Exception as error:
            print(f"❌ Erro ao responder interação: {error}")

    async def cleanup_expired_containers(self):
        """Limpeza automática de containers expirados"""
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutos

                current_time = datetime.utcnow()
                expired_containers = []

                for container_id, container_data in self.active_containers.items():
                    created_at = container_data["created_at"]
                    if current_time - created_at > timedelta(minutes=15):
                        expired_containers.append(container_id)

                # Remover containers expirados
                for container_id in expired_containers:
                    del self.active_containers[container_id]
                    print(f"🧹 Debug - Container expirado removido: {container_id}")

                if expired_containers:
                    print(f"🧹 Debug - {len(expired_containers)} containers expirados removidos")
                    print(f"🧹 Debug - Containers ativos restantes: {len(self.active_containers)}")

            except Exception as error:
                print(f"❌ Erro na limpeza automática: {error}")


def setup_container_handler(bot: commands.Bot) -> ContainerHandler:
    """
    Configurar o handler de containers

    Args:
        bot (commands.Bot): Instância do bot

    Returns:
        ContainerHandler: Handler configurado
    """
    return ContainerHandler(bot)
