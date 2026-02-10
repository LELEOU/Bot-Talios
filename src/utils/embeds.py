"""
Utilitários para Embeds - ADAPTADO DO JS
Funções para criar embeds customizados, leaderboards, etc.
"""

from __future__ import annotations

import re
from typing import Any

import discord


class EmbedBuilder:
    """Classe utilitária para construir embeds de forma fácil"""

    @staticmethod
    def build_leaderboard_embed(
        top_users: list[dict], title: str = "Ranking de XP"
    ) -> discord.Embed:
        """Criar embed de leaderboard - IGUAL AO JS"""
        embed = discord.Embed(
            title=title,
            color=0xFFD700,  # Dourado
        )

        if not top_users:
            embed.description = "Nenhum usuário encontrado."
            return embed

        # Criar descrição com ranking
        ranking_lines = []
        for i, user in enumerate(top_users[:10], 1):  # Top 10
            user_id = user.get("user_id", user.get("id", ""))
            level = user.get("level", 0)
            xp = user.get("xp", 0)

            # Emojis para top 3
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"**{i}.**"

            ranking_lines.append(f"{emoji} <@{user_id}> — Nível: **{level}** | XP: **{xp:,}**")

        embed.description = "\\n".join(ranking_lines)

        # Footer informativo
        embed.set_footer(text="Use /rank para ver sua posição individual")

        return embed

    @staticmethod
    def build_custom_embed(options: dict[str, Any]) -> discord.Embed:
        """Criar embed customizado - ADAPTADO DO JS"""
        embed = discord.Embed()

        # Título
        if options.get("titulo") or options.get("title"):
            title = options.get("titulo") or options.get("title")
            embed.title = str(title)[:256]  # Limite Discord

        # Descrição
        if options.get("descricao") or options.get("description"):
            desc = options.get("descricao") or options.get("description")
            embed.description = str(desc)[:4096]  # Limite Discord

        # Cor
        if options.get("cor") or options.get("color"):
            color = options.get("cor") or options.get("color")
            embed.color = EmbedBuilder.parse_color(color)

        # URL
        if options.get("url"):
            embed.url = str(options["url"])

        # Thumbnail
        if options.get("thumbnail"):
            embed.set_thumbnail(url=str(options["thumbnail"]))

        # Imagem
        if options.get("imagem") or options.get("image"):
            image = options.get("imagem") or options.get("image")
            embed.set_image(url=str(image))

        # Timestamp
        if options.get("timestamp"):
            if isinstance(options["timestamp"], bool) and options["timestamp"]:
                embed.timestamp = discord.utils.utcnow()
            else:
                embed.timestamp = options["timestamp"]

        # Author
        if options.get("author"):
            author = options["author"]
            embed.set_author(
                name=str(author.get("name", ""))[:256],
                icon_url=author.get("iconURL") or author.get("icon_url"),
                url=author.get("url"),
            )

        # Footer
        if options.get("footer"):
            footer = options["footer"]
            embed.set_footer(
                text=str(footer.get("text", ""))[:2048],
                icon_url=footer.get("iconURL") or footer.get("icon_url"),
            )

        # Fields
        if options.get("fields"):
            for field in options["fields"]:
                if field.get("name") and field.get("value"):
                    embed.add_field(
                        name=str(field["name"])[:256],
                        value=str(field["value"])[:1024],
                        inline=field.get("inline", False),
                    )

        return embed

    @staticmethod
    def parse_color(color: Any) -> int:
        """Converter cor para formato Discord"""
        if isinstance(color, int):
            return color

        if isinstance(color, str):
            # Remover # se presente
            color = color.lstrip("#")

            # Cores nomeadas
            color_names = {
                "red": 0xFF0000,
                "green": 0x00FF00,
                "blue": 0x0000FF,
                "yellow": 0xFFFF00,
                "orange": 0xFFA500,
                "purple": 0x800080,
                "pink": 0xFFC0CB,
                "black": 0x000000,
                "white": 0xFFFFFF,
                "gray": 0x808080,
                "grey": 0x808080,
                "gold": 0xFFD700,
                "silver": 0xC0C0C0,
            }

            if color.lower() in color_names:
                return color_names[color.lower()]

            # Tentar converter hex
            try:
                return int(color, 16)
            except ValueError:
                return 0x000000  # Preto como fallback

        return 0x000000  # Preto como fallback

    @staticmethod
    def sanitize_embed_options(options: dict[str, Any]) -> dict[str, Any]:
        """Sanitizar e validar opções do embed - IGUAL AO JS"""
        sanitized = {}

        # Validar e limitar comprimentos
        if options.get("titulo") and isinstance(options["titulo"], str):
            sanitized["titulo"] = options["titulo"][:256]

        if options.get("descricao") and isinstance(options["descricao"], str):
            sanitized["descricao"] = options["descricao"][:4096]

        # Validar cor
        if options.get("cor"):
            if isinstance(options["cor"], str):
                hex_pattern = r"^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
                if re.match(hex_pattern, options["cor"]):
                    sanitized["cor"] = options["cor"]
            elif isinstance(options["cor"], int):
                sanitized["cor"] = options["cor"]

        # Validar URLs
        url_pattern = r"^https?://.+"

        if options.get("url") and re.match(url_pattern, str(options["url"])):
            sanitized["url"] = options["url"]

        if options.get("thumbnail") and re.match(url_pattern, str(options["thumbnail"])):
            sanitized["thumbnail"] = options["thumbnail"]

        if options.get("imagem") and re.match(url_pattern, str(options["imagem"])):
            sanitized["imagem"] = options["imagem"]

        # Validar author
        if options.get("author") and isinstance(options["author"], dict):
            author = options["author"]
            sanitized["author"] = {}

            if author.get("name"):
                sanitized["author"]["name"] = str(author["name"])[:256]

            if author.get("iconURL") and re.match(url_pattern, str(author["iconURL"])):
                sanitized["author"]["iconURL"] = author["iconURL"]

            if author.get("url") and re.match(url_pattern, str(author["url"])):
                sanitized["author"]["url"] = author["url"]

        # Validar footer
        if options.get("footer") and isinstance(options["footer"], dict):
            footer = options["footer"]
            sanitized["footer"] = {}

            if footer.get("text"):
                sanitized["footer"]["text"] = str(footer["text"])[:2048]

            if footer.get("iconURL") and re.match(url_pattern, str(footer["iconURL"])):
                sanitized["footer"]["iconURL"] = footer["iconURL"]

        # Validar fields
        if options.get("fields") and isinstance(options["fields"], list):
            sanitized["fields"] = []

            for field in options["fields"][:25]:  # Máximo 25 fields
                if field.get("name") and field.get("value"):
                    sanitized_field = {
                        "name": str(field["name"])[:256],
                        "value": str(field["value"])[:1024],
                        "inline": bool(field.get("inline", False)),
                    }
                    sanitized["fields"].append(sanitized_field)

        return sanitized

    @staticmethod
    def build_error_embed(error_message: str, title: str = "❌ Erro") -> discord.Embed:
        """Criar embed de erro padronizado"""
        embed = discord.Embed(
            title=title,
            description=str(error_message),
            color=0xFF0000,  # Vermelho
        )
        return embed

    @staticmethod
    def build_success_embed(success_message: str, title: str = "✅ Sucesso") -> discord.Embed:
        """Criar embed de sucesso padronizado"""
        embed = discord.Embed(
            title=title,
            description=str(success_message),
            color=0x00FF00,  # Verde
        )
        return embed

    @staticmethod
    def build_warning_embed(warning_message: str, title: str = "⚠️ Aviso") -> discord.Embed:
        """Criar embed de aviso padronizado"""
        embed = discord.Embed(
            title=title,
            description=str(warning_message),
            color=0xFFAA00,  # Laranja
        )
        return embed

    @staticmethod
    def build_info_embed(info_message: str, title: str = "ℹ️ Informação") -> discord.Embed:
        """Criar embed informativo padronizado"""
        embed = discord.Embed(
            title=title,
            description=str(info_message),
            color=0x0099FF,  # Azul
        )
        return embed

    @staticmethod
    def build_moderation_embed(
        action: str,
        user: discord.Member,
        moderator: discord.Member,
        reason: str,
        case_id: int | None = None,
        duration: str | None = None,
    ) -> discord.Embed:
        """Criar embed para ações de moderação"""

        action_colors = {
            "warn": 0xFFAA00,  # Laranja
            "mute": 0xFF6600,  # Vermelho-laranja
            "kick": 0xFF3300,  # Vermelho
            "ban": 0xFF0000,  # Vermelho escuro
            "unban": 0x00FF00,  # Verde
            "unmute": 0x00FF00,  # Verde
        }

        action_emojis = {
            "warn": "⚠️",
            "mute": "🔇",
            "kick": "👢",
            "ban": "🔨",
            "unban": "🔓",
            "unmute": "🔊",
        }

        color = action_colors.get(action, 0x666666)
        emoji = action_emojis.get(action, "🔨")

        title = f"{emoji} {action.title()}"
        if case_id:
            title += f" - Case #{case_id}"

        embed = discord.Embed(title=title, color=color, timestamp=discord.utils.utcnow())

        embed.add_field(name="Usuário", value=user.mention, inline=True)
        embed.add_field(name="Moderador", value=moderator.mention, inline=True)

        if duration:
            embed.add_field(name="Duração", value=duration, inline=True)

        embed.add_field(name="Razão", value=reason, inline=False)

        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"ID do usuário: {user.id}")

        return embed

    @staticmethod
    def build_level_up_embed(
        user: discord.Member,
        new_level: int,
        new_xp: int,
        role_reward: discord.Role | None = None,
    ) -> discord.Embed:
        """Criar embed para level up"""
        embed = discord.Embed(
            title="🎉 Level Up!",
            description=f"Parabéns {user.mention}! Você alcançou o **nível {new_level}**!",
            color=0x00FF00,
        )

        embed.add_field(name="Novo Nível", value=str(new_level), inline=True)
        embed.add_field(name="XP Total", value=f"{new_xp:,}", inline=True)

        if role_reward:
            embed.add_field(
                name="🎁 Recompensa",
                value=f"Você recebeu o cargo {role_reward.mention}!",
                inline=False,
            )

        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Continue enviando mensagens para ganhar mais XP!")

        return embed

    @staticmethod
    def build_giveaway_embed(
        title: str,
        description: str,
        end_time: str,
        winner_count: int,
        host: discord.Member,
        participants: int = 0,
    ) -> discord.Embed:
        """Criar embed para giveaway"""
        embed = discord.Embed(
            title=f"🎁 {title}",
            description=description,
            color=0xFF69B4,  # Rosa
        )

        embed.add_field(name="Termina", value=end_time, inline=True)
        embed.add_field(name="Vencedores", value=str(winner_count), inline=True)
        embed.add_field(name="Participantes", value=str(participants), inline=True)
        embed.add_field(name="Hospedado por", value=host.mention, inline=False)

        embed.set_footer(text="Clique no botão abaixo para participar!")

        return embed


# Instância global para uso fácil
embed_builder = EmbedBuilder()
