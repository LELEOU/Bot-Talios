"""
Configuração e utilitários auxiliares
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()


class Config:
    """Classe de configuração do bot"""

    # Bot configuration
    TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    GUILD_ID: int | None = int(os.getenv("GUILD_ID", "0")) or None
    OWNER_ID: int | None = int(os.getenv("OWNER_ID", "0")) or None

    # Development
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"
    COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", "!")

    # Container settings
    CONTAINER_TIMEOUT: int = int(os.getenv("CONTAINER_TIMEOUT", "15"))
    MAX_CONTAINERS_PER_USER: int = int(os.getenv("MAX_CONTAINERS_PER_USER", "5"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FILE: str | None = os.getenv("LOG_FILE")

    # Performance
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "10"))
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "30"))

    # Bot info
    BOT_NAME: str = os.getenv("BOT_NAME", "Container Bot Python")
    BOT_DESCRIPTION: str = os.getenv("BOT_DESCRIPTION", "Sistema avançado de containers Discord")

    @classmethod
    def validate(cls) -> bool:
        """Validar configurações obrigatórias"""
        if not cls.TOKEN:
            print("❌ DISCORD_TOKEN é obrigatório!")
            return False

        return True


    @classmethod
    def get_log_level(cls) -> str:
        """Obter nível de log configurado"""
        return cls.LOG_LEVEL


    @classmethod
    def is_debug(cls) -> bool:
        """Verificar se está em modo debug"""
        return cls.DEBUG_MODE


class Emojis:
    """Emojis padronizados para o bot"""

    # Status
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "🔄"

    # Containers
    CONTAINER = "📦"
    EDIT = "✏️"
    COLOR = "🎨"
    IMAGE = "🖼️"
    PREVIEW = "👀"
    SEND = "📤"

    # Categories
    PROFESSIONAL = "🌟"
    DASHBOARD = "📊"
    WELCOME = "🎉"
    ANNOUNCEMENT = "📢"
    BASIC = "📦"
    INTERACTIVE = "🔘"

    # Actions
    CONFIG = "⚙️"
    DELETE = "🗑️"
    COPY = "📋"
    SAVE = "💾"

    # System
    DEBUG = "🔧"
    CLEANUP = "🧹"
    SECURITY = "🛡️"
    PERFORMANCE = "⚡"


class Messages:
    """Mensagens padronizadas"""

    # Errors
    NO_PERMISSION = "❌ Você não tem permissão para usar este comando."
    CONTAINER_NOT_FOUND = "❌ Container não encontrado ou você não tem permissão!"
    INVALID_COLOR = "❌ Cor inválida! Use o formato #FFFFFF"
    INTERNAL_ERROR = "❌ Erro interno: {error}"

    # Success
    CONTAINER_SENT = "✅ Container enviado com sucesso!"
    CONFIG_UPDATED = "✅ Configuração atualizada com sucesso!"
    TEXT_UPDATED = "✅ Texto atualizado com sucesso!"
    COLOR_UPDATED = "✅ Cor atualizada para {color}!"
    IMAGES_UPDATED = "✅ Imagens atualizadas com sucesso!"

    # Info
    PREVIEW_TITLE = "📋 **Preview do Container:**"
    CONTAINER_EXPIRED = "🧹 Container expirado removido"
    BOT_STARTED = "🤖 Bot iniciado com sucesso!"


def format_uptime(seconds: int) -> str:
    """
    Formatar tempo de uptime

    Args:
        seconds (int): Segundos de uptime

    Returns:
        str: Uptime formatado
    """
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m {seconds}s"


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncar texto se for muito longo

    Args:
        text (str): Texto a ser truncado
        max_length (int): Comprimento máximo

    Returns:
        str: Texto truncado
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - 3] + "..."


def format_number(number: int) -> str:
    """
    Formatar número com separadores

    Args:
        number (int): Número a ser formatado

    Returns:
        str: Número formatado
    """
    return f"{number:,}"


def validate_hex_color(color: str) -> int | None:
    """
    Validar e converter cor hexadecimal

    Args:
        color (str): Cor em formato hex (#FFFFFF)

    Returns:
        int | None: Cor em decimal ou None se inválida
    """
    try:
        if color.startswith("#"):
            color = color[1:]

        if len(color) != 6:
            return None

        return int(color, 16)
    except ValueError:
        return None


def is_url_valid(url: str) -> bool:
    """
    Verificar se URL é válida

    Args:
        url (str): URL a ser verificada

    Returns:
        bool: True se válida
    """
    import re

    pattern = re.compile(
        r"^https?://"  # http:// ou https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
        r"(?::\d+)?"  # porta
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    return bool(pattern.match(url))
