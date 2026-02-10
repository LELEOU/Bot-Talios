"""
Helpers para Interações - Utilitários avançados
Funções auxiliares para comandos slash, botões, modals
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

if TYPE_CHECKING:
    pass


class InteractionHelpers:
    """Classe com helpers para interações Discord"""

    @staticmethod
    async def safe_response(
        interaction: discord.Interaction,
        content: str | None = None,
        embed: discord.Embed | None = None,
        view: discord.ui.View | None = None,
        ephemeral: bool = False,
        file: discord.File | None = None,
    ) -> bool:
        """Responder interação de forma segura"""
        try:
            if interaction.response.is_done():
                # Usar followup se já foi respondida
                await interaction.followup.send(
                    content=content, embed=embed, view=view, ephemeral=ephemeral, file=file
                )
            else:
                # Responder normalmente
                await interaction.response.send_message(
                    content=content, embed=embed, view=view, ephemeral=ephemeral, file=file
                )
            return True

        except discord.InteractionResponded:
            # Tentar followup
            try:
                await interaction.followup.send(
                    content=content or "Operação concluída.",
                    embed=embed,
                    view=view,
                    ephemeral=ephemeral,
                    file=file,
                )
                return True
            except Exception:
                return False

        except Exception as e:
            print(f"❌ Erro respondendo interação: {e}")
            return False

    @staticmethod
    async def safe_edit(
        interaction: discord.Interaction,
        content: str | None = None,
        embed: discord.Embed | None = None,
        view: discord.ui.View | None = None,
    ) -> bool:
        """Editar resposta de interação de forma segura"""
        try:
            await interaction.edit_original_response(content=content, embed=embed, view=view)
            return True

        except Exception as e:
            print(f"❌ Erro editando interação: {e}")
            return False

    @staticmethod
    async def confirm_action(
        interaction: discord.Interaction, title: str, description: str, danger: bool = False
    ) -> bool:
        """Criar confirmação com botões"""

        class ConfirmView(discord.ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=60)
                self.value: bool | None = None

            @discord.ui.button(
                label="✅ Confirmar",
                style=discord.ButtonStyle.danger if danger else discord.ButtonStyle.success,
            )
            async def confirm(
                self, button_interaction: discord.Interaction, button: discord.ui.Button
            ) -> None:
                self.value = True
                self.stop()
                await button_interaction.response.send_message("✅ Confirmado!", ephemeral=True)

            @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
            async def cancel(
                self, button_interaction: discord.Interaction, button: discord.ui.Button
            ) -> None:
                self.value = False
                self.stop()
                await button_interaction.response.send_message("❌ Cancelado!", ephemeral=True)

        embed = discord.Embed(
            title=title, description=description, color=0xFF0000 if danger else 0x00FF00
        )

        view = ConfirmView()

        await InteractionHelpers.safe_response(interaction, embed=embed, view=view, ephemeral=True)

        # Aguardar resposta
        await view.wait()

        return view.value or False

    @staticmethod
    async def paginate_embeds(
        interaction: discord.Interaction, embeds: list[discord.Embed], timeout: int = 300
    ) -> None:
        """Criar sistema de paginação para embeds"""

        if not embeds:
            await InteractionHelpers.safe_response(
                interaction, "❌ Nenhum conteúdo para paginar.", ephemeral=True
            )
            return

        if len(embeds) == 1:
            await InteractionHelpers.safe_response(interaction, embed=embeds[0])
            return

        class PaginationView(discord.ui.View):
            def __init__(self, embeds: list[discord.Embed]) -> None:
                super().__init__(timeout=timeout)
                self.embeds: list[discord.Embed] = embeds
                self.current_page: int = 0
                self.max_pages: int = len(embeds)

                # Atualizar estados dos botões
                self.update_buttons()

            def update_buttons(self) -> None:
                """Atualizar estado dos botões"""
                self.first_page.disabled = self.current_page == 0
                self.prev_page.disabled = self.current_page == 0
                self.next_page.disabled = self.current_page == self.max_pages - 1
                self.last_page.disabled = self.current_page == self.max_pages - 1

            @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.secondary)
            async def first_page(
                self, button_interaction: discord.Interaction, button: discord.ui.Button
            ) -> None:
                self.current_page = 0
                self.update_buttons()
                await button_interaction.response.edit_message(embed=self.embeds[0], view=self)

            @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary)
            async def prev_page(
                self, button_interaction: discord.Interaction, button: discord.ui.Button
            ) -> None:
                self.current_page = max(0, self.current_page - 1)
                self.update_buttons()
                await button_interaction.response.edit_message(
                    embed=self.embeds[self.current_page], view=self
                )

            @discord.ui.button(emoji="🗑️", style=discord.ButtonStyle.danger)
            async def delete_message(
                self, button_interaction: discord.Interaction, button: discord.ui.Button
            ) -> None:
                await button_interaction.response.edit_message(
                    content="🗑️ Mensagem deletada.", embed=None, view=None
                )
                self.stop()

            @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary)
            async def next_page(
                self, button_interaction: discord.Interaction, button: discord.ui.Button
            ) -> None:
                self.current_page = min(self.max_pages - 1, self.current_page + 1)
                self.update_buttons()
                await button_interaction.response.edit_message(
                    embed=self.embeds[self.current_page], view=self
                )

            @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.secondary)
            async def last_page(
                self, button_interaction: discord.Interaction, button: discord.ui.Button
            ) -> None:
                self.current_page = self.max_pages - 1
                self.update_buttons()
                await button_interaction.response.edit_message(embed=self.embeds[-1], view=self)

        # Adicionar informação de página ao embed
        for i, embed in enumerate(embeds):
            if embed.footer:
                embed.set_footer(text=f"{embed.footer.text} • Página {i + 1}/{len(embeds)}")
            else:
                embed.set_footer(text=f"Página {i + 1}/{len(embeds)}")

        view = PaginationView(embeds)
        await InteractionHelpers.safe_response(interaction, embed=embeds[0], view=view)

    @staticmethod
    async def create_modal_input(title: str, fields: list[dict[str, Any]]) -> discord.ui.Modal:
        """Criar modal dinâmico com campos"""

        class DynamicModal(discord.ui.Modal):
            def __init__(self, title: str, fields: list[dict[str, Any]]) -> None:
                super().__init__(title=title, timeout=300)
                self.results: dict[str, Any] = {}

                for field in fields[:5]:  # Máximo 5 campos
                    text_input = discord.ui.TextInput(
                        label=field.get("label", "Campo"),
                        placeholder=field.get("placeholder", ""),
                        default=field.get("default", ""),
                        required=field.get("required", True),
                        max_length=field.get("max_length", 1000),
                        style=discord.TextStyle.paragraph
                        if field.get("multiline")
                        else discord.TextStyle.short,
                    )

                    # Adicionar custom_id baseado no label
                    text_input.custom_id = field.get(
                        "id", field.get("label", f"field_{len(self.children)}")
                    )

                    self.add_item(text_input)

            async def on_submit(self, interaction: discord.Interaction) -> None:
                """Processar submit do modal"""
                for child in self.children:
                    self.results[child.custom_id] = child.value

                await interaction.response.send_message("✅ Dados recebidos!", ephemeral=True)

        return DynamicModal(title, fields)

    @staticmethod
    def format_time_delta(seconds: int) -> str:
        """Formatar tempo em formato legível"""
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m"
        if seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m" if minutes else f"{hours}h"
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h" if hours else f"{days}d"

    @staticmethod
    def parse_time_string(time_str: str) -> int:
        """Converter string de tempo para segundos"""
        import re

        time_str = time_str.lower().strip()

        # Padrões suportados: 1h, 30m, 1d, 2w
        patterns = {
            r"(\d+)s": 1,  # segundos
            r"(\d+)m": 60,  # minutos
            r"(\d+)h": 3600,  # horas
            r"(\d+)d": 86400,  # dias
            r"(\d+)w": 604800,  # semanas
        }

        total_seconds = 0

        for pattern, multiplier in patterns.items():
            matches = re.findall(pattern, time_str)
            for match in matches:
                total_seconds += int(match) * multiplier

        return total_seconds or 0

    @staticmethod
    async def send_dm_safe(
        user: discord.User, content: str | None = None, embed: discord.Embed | None = None
    ) -> bool:
        """Enviar DM de forma segura"""
        try:
            await user.send(content=content, embed=embed)
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False

    @staticmethod
    def create_progress_bar(current: int, maximum: int, length: int = 20) -> str:
        """Criar barra de progresso visual"""
        if maximum == 0:
            return "▱" * length

        progress = min(current / maximum, 1.0)
        filled = int(progress * length)

        bar = "▰" * filled + "▱" * (length - filled)
        percentage = int(progress * 100)

        return f"{bar} {percentage}%"

    @staticmethod
    def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
        """Truncar string com sufixo"""
        if len(text) <= max_length:
            return text

        return text[: max_length - len(suffix)] + suffix

    @staticmethod
    async def wait_for_reaction(
        bot: commands.Bot,
        message: discord.Message,
        user: discord.User,
        emojis: list[str],
        timeout: int = 60,
    ) -> str | None:
        """Aguardar reação específica do usuário"""

        # Adicionar reações
        for emoji in emojis:
            try:
                await message.add_reaction(emoji)
            except Exception:
                continue

        def check(reaction: discord.Reaction, reaction_user: discord.User) -> bool:
            return (
                reaction_user == user
                and str(reaction.emoji) in emojis
                and reaction.message.id == message.id
            )

        try:
            reaction, _ = await bot.wait_for("reaction_add", check=check, timeout=timeout)
            return str(reaction.emoji)
        except TimeoutError:
            return None

    @staticmethod
    def create_embed_field_list(
        items: list[str], title: str = "Lista", max_per_field: int = 10
    ) -> list[dict[str, Any]]:
        """Criar lista de fields para embed com múltiplos itens"""
        fields = []

        for i in range(0, len(items), max_per_field):
            chunk = items[i : i + max_per_field]

            field_title = title
            if len(items) > max_per_field:
                page = (i // max_per_field) + 1
                total_pages = ((len(items) - 1) // max_per_field) + 1
                field_title = f"{title} ({page}/{total_pages})"

            field_value = "\\n".join(chunk) or "Nenhum item"

            fields.append({"name": field_title, "value": field_value, "inline": False})

        return fields

    @staticmethod
    async def get_user_input(
        interaction: discord.Interaction, prompt: str, timeout: int = 300
    ) -> str | None:
        """Aguardar input do usuário via mensagem"""

        embed = discord.Embed(title="📝 Input Necessário", description=prompt, color=0x00AAFF)

        embed.set_footer(text=f"Você tem {timeout // 60} minutos para responder.")

        await InteractionHelpers.safe_response(interaction, embed=embed, ephemeral=True)

        def check(message: discord.Message) -> bool:
            return message.author == interaction.user and message.channel == interaction.channel

        try:
            bot = interaction.client
            message = await bot.wait_for("message", check=check, timeout=timeout)
            return message.content

        except TimeoutError:
            return None


# Instância global para uso fácil
interaction_helpers = InteractionHelpers()
