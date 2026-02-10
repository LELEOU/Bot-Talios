"""
Sistema de Logs Coloridos para o Bot Discord
Melhor visualização e debugging com colorlog
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import colorlog

if TYPE_CHECKING:
    from logging import Logger


class BotLogger:
    """Logger customizado com cores para melhor visualização"""

    def __init__(self, name: str = "DiscordBot") -> None:
        """
        Inicializa o logger com cores

        Args:
            name: Nome do logger
        """
        self.logger: Logger = colorlog.getLogger(name)

        # Configurar apenas se ainda não foi configurado
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)

            # Handler colorido para console
            handler = colorlog.StreamHandler()
            handler.setFormatter(
                colorlog.ColoredFormatter(
                    "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s",
                    datefmt=None,
                    reset=True,
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "red,bg_white",
                    },
                    secondary_log_colors={},
                    style="%",
                )
            )

            self.logger.addHandler(handler)

    def success(self, message: str) -> None:
        """Log de sucesso (verde)"""
        self.logger.info(f"✅ {message}")

    def info(self, message: str) -> None:
        """Log de informação (azul)"""
        self.logger.info(f"ℹ {message}")

    def warning(self, message: str) -> None:
        """Log de aviso (amarelo)"""
        self.logger.warning(f"⚠️  {message}")

    def error(self, message: str, exc: Exception | None = None) -> None:
        """Log de erro (vermelho)"""
        self.logger.error(f"❌ {message}")
        if exc:
            self.logger.exception(exc)

    def debug(self, message: str) -> None:
        """Log de debug (cyan)"""
        self.logger.debug(f"🔧 {message}")

    def command(self, command: str, user: str) -> None:
        """Log de comando executado"""
        self.logger.info(f"⚡ Comando '{command}' executado por {user}")

    def extension(self, extension: str, status: str = "carregada") -> None:
        """Log de extensão carregada"""
        if status == "carregada":
            self.logger.info(f"📦 Extensão '{extension}' {status}")
        elif status == "erro":
            self.logger.error(f"📦 Erro ao carregar '{extension}'")


# Instância global
logger = BotLogger()
