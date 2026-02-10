"""
Sistema de Embed Builder Interativo v2.0
Builder visual com preview em tempo real e suporte a JSON
"""

import json
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View


class EmbedBuilderModal(Modal, title="Editor de Embed"):
    """Modal para edição rápida de campos do embed"""

    def __init__(self, builder_view: "EmbedBuilderView", field_type: str):
        super().__init__(timeout=300)
        self.builder_view = builder_view
        self.field_type = field_type

        # Campos diferentes baseados no tipo
        if field_type == "title":
            self.input_field = TextInput(
                label="Título do Embed",
                placeholder="Digite o título (máx. 256 caracteres)",
                max_length=256,
                default=builder_view.embed_data.get("title", ""),
                required=False,
            )
        elif field_type == "description":
            self.input_field = TextInput(
                label="Descrição do Embed",
                placeholder="Digite a descrição (máx. 4000 caracteres)",
                style=discord.TextStyle.paragraph,
                max_length=4000,
                default=builder_view.embed_data.get("description", ""),
                required=False,
            )
        elif field_type == "color":
            self.input_field = TextInput(
                label="Cor do Embed (Hex)",
                placeholder="Ex: #FF5733 ou FF5733",
                max_length=7,
                default=builder_view.embed_data.get("color", ""),
                required=False,
            )
        elif field_type == "footer":
            self.input_field = TextInput(
                label="Texto do Rodapé",
                placeholder="Digite o texto do rodapé (máx. 2048 caracteres)",
                max_length=2048,
                default=builder_view.embed_data.get("footer", {}).get("text", ""),
                required=False,
            )
        elif field_type == "author":
            self.input_field = TextInput(
                label="Nome do Autor",
                placeholder="Digite o nome do autor (máx. 256 caracteres)",
                max_length=256,
                default=builder_view.embed_data.get("author", {}).get("name", ""),
                required=False,
            )
        elif field_type == "image":
            self.input_field = TextInput(
                label="URL da Imagem",
                placeholder="https://exemplo.com/imagem.png",
                default=builder_view.embed_data.get("image", {}).get("url", ""),
                required=False,
            )
        elif field_type == "thumbnail":
            self.input_field = TextInput(
                label="URL da Miniatura",
                placeholder="https://exemplo.com/miniatura.png",
                default=builder_view.embed_data.get("thumbnail", {}).get("url", ""),
                required=False,
            )

        self.add_item(self.input_field)

    async def on_submit(self, interaction: discord.Interaction):
        """Atualizar embed data e preview"""
        value = self.input_field.value.strip()

        if self.field_type == "title":
            if value:
                self.builder_view.embed_data["title"] = value
            else:
                self.builder_view.embed_data.pop("title", None)

        elif self.field_type == "description":
            if value:
                self.builder_view.embed_data["description"] = value
            else:
                self.builder_view.embed_data.pop("description", None)

        elif self.field_type == "color":
            if value:
                # Processar cor hex
                color_hex = value.replace("#", "")
                try:
                    self.builder_view.embed_data["color"] = int(color_hex, 16)
                except:
                    await interaction.response.send_message(
                        "❌ Cor inválida! Use formato HEX (#FF5733)", ephemeral=True
                    )
                    return
            else:
                self.builder_view.embed_data.pop("color", None)

        elif self.field_type == "footer":
            if value:
                self.builder_view.embed_data["footer"] = {"text": value}
            else:
                self.builder_view.embed_data.pop("footer", None)

        elif self.field_type == "author":
            if value:
                self.builder_view.embed_data["author"] = {"name": value}
            else:
                self.builder_view.embed_data.pop("author", None)

        elif self.field_type == "image":
            if value:
                self.builder_view.embed_data["image"] = {"url": value}
            else:
                self.builder_view.embed_data.pop("image", None)

        elif self.field_type == "thumbnail":
            if value:
                self.builder_view.embed_data["thumbnail"] = {"url": value}
            else:
                self.builder_view.embed_data.pop("thumbnail", None)

        # Atualizar preview
        await self.builder_view.update_preview(interaction)


class FieldModal(Modal, title="Adicionar/Editar Campo"):
    """Modal para adicionar ou editar campos do embed"""

    name = TextInput(
        label="Nome do Campo",
        placeholder="Digite o nome do campo (máx. 256 caracteres)",
        max_length=256,
        required=True,
    )

    value = TextInput(
        label="Valor do Campo",
        placeholder="Digite o valor do campo (máx. 1024 caracteres)",
        style=discord.TextStyle.paragraph,
        max_length=1024,
        required=True,
    )

    inline = TextInput(
        label="Campo em Linha? (sim/não)",
        placeholder="Digite 'sim' para campo em linha, 'não' para campo completo",
        max_length=3,
        default="não",
        required=False,
    )

    def __init__(self, builder_view: "EmbedBuilderView", field_index: int = -1):
        super().__init__()
        self.builder_view = builder_view
        self.field_index = field_index

        # Preencher com dados existentes se editando
        if field_index >= 0 and field_index < len(builder_view.embed_data.get("fields", [])):
            field = builder_view.embed_data["fields"][field_index]
            self.name.default = field.get("name", "")
            self.value.default = field.get("value", "")
            self.inline.default = "sim" if field.get("inline", False) else "não"

    async def on_submit(self, interaction: discord.Interaction):
        """Salvar campo no embed"""
        field_data = {
            "name": self.name.value,
            "value": self.value.value,
            "inline": self.inline.value.lower() in ["sim", "s", "yes", "y", "true"],
        }

        if "fields" not in self.builder_view.embed_data:
            self.builder_view.embed_data["fields"] = []

        if self.field_index >= 0:
            # Editar campo existente
            self.builder_view.embed_data["fields"][self.field_index] = field_data
        else:
            # Adicionar novo campo
            if len(self.builder_view.embed_data["fields"]) >= 25:
                await interaction.response.send_message(
                    "❌ Máximo de 25 campos atingido!", ephemeral=True
                )
                return
            self.builder_view.embed_data["fields"].append(field_data)

        await self.builder_view.update_preview(interaction)


class JSONImportModal(Modal, title="Importar JSON"):
    """Modal para importar embed de JSON"""

    json_input = TextInput(
        label="Cole o JSON do Embed",
        placeholder='{"title": "Meu Embed", "description": "Descrição..."}',
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=True,
    )

    def __init__(self, builder_view: "EmbedBuilderView"):
        super().__init__()
        self.builder_view = builder_view

    async def on_submit(self, interaction: discord.Interaction):
        """Importar JSON"""
        try:
            data = json.loads(self.json_input.value)
            self.builder_view.embed_data = data
            await self.builder_view.update_preview(interaction)
            await interaction.followup.send("✅ JSON importado com sucesso!", ephemeral=True)
        except json.JSONDecodeError as e:
            await interaction.response.send_message(
                f"❌ Erro ao processar JSON:\n```{e!s}```", ephemeral=True
            )


class EmbedBuilderView(View):
    """View principal do construtor de embeds"""

    def __init__(self, user: discord.User):
        super().__init__(timeout=600)  # 10 minutos
        self.user = user
        self.embed_data = {
            "title": "📝 Novo Embed",
            "description": "Use os botões abaixo para personalizar",
            "color": 0x3498DB,
        }
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Apenas o criador pode interagir"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Apenas quem iniciou o builder pode editar!", ephemeral=True
            )
            return False
        return True

    def build_embed(self) -> discord.Embed:
        """Construir embed a partir dos dados"""
        embed = discord.Embed()

        if "title" in self.embed_data:
            embed.title = self.embed_data["title"]

        if "description" in self.embed_data:
            embed.description = self.embed_data["description"]

        if "color" in self.embed_data:
            embed.color = self.embed_data["color"]

        if "footer" in self.embed_data:
            embed.set_footer(text=self.embed_data["footer"].get("text", ""))

        if "author" in self.embed_data:
            embed.set_author(name=self.embed_data["author"].get("name", ""))

        if "image" in self.embed_data:
            embed.set_image(url=self.embed_data["image"].get("url", ""))

        if "thumbnail" in self.embed_data:
            embed.set_thumbnail(url=self.embed_data["thumbnail"].get("url", ""))

        if "fields" in self.embed_data:
            for field in self.embed_data["fields"]:
                embed.add_field(
                    name=field.get("name", "Campo"),
                    value=field.get("value", "Valor"),
                    inline=field.get("inline", False),
                )

        if self.embed_data.get("timestamp"):
            embed.timestamp = datetime.utcnow()

        return embed

    async def update_preview(self, interaction: discord.Interaction):
        """Atualizar preview do embed"""
        embed = self.build_embed()

        # Adicionar info de controle
        info_text = (
            "🎨 **Preview em Tempo Real**\n"
            f"📊 Campos: {len(self.embed_data.get('fields', []))}/25\n"
            f"📏 Caracteres Totais: {len(str(self.embed_data))}\n\n"
            "Use os botões abaixo para editar!"
        )

        try:
            await interaction.response.edit_message(content=info_text, embed=embed, view=self)
        except:
            # Se já respondeu, usar followup
            try:
                await interaction.edit_original_response(content=info_text, embed=embed, view=self)
            except:
                pass

    @discord.ui.button(label="✏️ Título", style=discord.ButtonStyle.primary, row=0)
    async def edit_title(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(EmbedBuilderModal(self, "title"))

    @discord.ui.button(label="📝 Descrição", style=discord.ButtonStyle.primary, row=0)
    async def edit_description(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(EmbedBuilderModal(self, "description"))

    @discord.ui.button(label="🎨 Cor", style=discord.ButtonStyle.primary, row=0)
    async def edit_color(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(EmbedBuilderModal(self, "color"))

    @discord.ui.button(label="➕ Campo", style=discord.ButtonStyle.success, row=1)
    async def add_field(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(FieldModal(self))

    @discord.ui.button(label="👤 Autor", style=discord.ButtonStyle.secondary, row=1)
    async def edit_author(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(EmbedBuilderModal(self, "author"))

    @discord.ui.button(label="📄 Rodapé", style=discord.ButtonStyle.secondary, row=1)
    async def edit_footer(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(EmbedBuilderModal(self, "footer"))

    @discord.ui.button(label="🖼️ Imagem", style=discord.ButtonStyle.secondary, row=2)
    async def edit_image(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(EmbedBuilderModal(self, "image"))

    @discord.ui.button(label="🔲 Miniatura", style=discord.ButtonStyle.secondary, row=2)
    async def edit_thumbnail(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(EmbedBuilderModal(self, "thumbnail"))

    @discord.ui.button(label="⏰ Timestamp", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_timestamp(self, interaction: discord.Interaction, button: Button):
        self.embed_data["timestamp"] = not self.embed_data.get("timestamp", False)
        await self.update_preview(interaction)

    @discord.ui.button(label="📥 Importar JSON", style=discord.ButtonStyle.secondary, row=3)
    async def import_json(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(JSONImportModal(self))

    @discord.ui.button(label="📤 Exportar JSON", style=discord.ButtonStyle.secondary, row=3)
    async def export_json(self, interaction: discord.Interaction, button: Button):
        json_str = json.dumps(self.embed_data, indent=2, ensure_ascii=False)

        # Limitar tamanho
        if len(json_str) > 1900:
            # Salvar em arquivo
            import io

            file = discord.File(io.BytesIO(json_str.encode()), filename="embed.json")
            await interaction.response.send_message(
                "📤 **JSON do Embed:**", file=file, ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"📤 **JSON do Embed:**\n```json\n{json_str}\n```", ephemeral=True
            )

    @discord.ui.button(label="🗑️ Limpar", style=discord.ButtonStyle.danger, row=3)
    async def clear_embed(self, interaction: discord.Interaction, button: Button):
        self.embed_data = {
            "title": "📝 Novo Embed",
            "description": "Embed limpo! Use os botões para personalizar",
            "color": 0x3498DB,
        }
        await self.update_preview(interaction)

    @discord.ui.button(label="✅ Enviar", style=discord.ButtonStyle.success, row=4)
    async def send_embed(self, interaction: discord.Interaction, button: Button):
        """Enviar embed para o canal"""
        embed = self.build_embed()

        # Perguntar onde enviar
        await interaction.response.send_message(
            "✅ **Embed pronto!** Mencione o canal onde deseja enviar:", ephemeral=True
        )

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger, row=4)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="❌ Builder cancelado!", embed=None, view=None
        )
        self.stop()


class EmbedBuilderCog(commands.Cog):
    """Cog para comandos de embed builder"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="embed", description="🎨 Criar embed interativo com preview em tempo real"
    )
    async def embed_builder(self, interaction: discord.Interaction):
        """Iniciar construtor de embeds"""
        view = EmbedBuilderView(interaction.user)
        embed = view.build_embed()

        info_text = (
            "🎨 **Embed Builder Interativo**\n"
            "📊 Campos: 0/25\n"
            "📏 Preview atualiza em tempo real!\n\n"
            "Use os botões abaixo para personalizar seu embed:"
        )

        await interaction.response.send_message(
            content=info_text, embed=embed, view=view, ephemeral=True
        )
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(EmbedBuilderCog(bot))
