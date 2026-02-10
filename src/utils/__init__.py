"""
Sistema de Containers Discord - Python Version
Módulo principal de utilitários
"""

from .config import Config, Emojis, Messages
from .container_templates import CONTAINER_TEMPLATES, Colors, ContainerTemplateManager

__version__ = "3.0.0"
__author__ = "Bot Development Team"

__all__ = [
    "CONTAINER_TEMPLATES",
    "Colors",
    "Config",
    "ContainerTemplateManager",
    "Emojis",
    "Messages",
]
