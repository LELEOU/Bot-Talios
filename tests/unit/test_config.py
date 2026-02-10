"""
🧪 Testes Unitários - Config Module
===================================

Testes para o módulo src/utils/config.py
"""

import os
from unittest.mock import patch

from src.utils.config import Config, Emojis, Messages


class TestConfig:
    """Testes para a classe Config."""

    def test_config_has_required_attributes(self) -> None:
        """Testar que Config tem todos os atributos obrigatórios."""
        assert hasattr(Config, "TOKEN")
        assert hasattr(Config, "GUILD_ID")
        assert hasattr(Config, "OWNER_ID")
        assert hasattr(Config, "DEBUG_MODE")
        assert hasattr(Config, "COMMAND_PREFIX")

    def test_config_default_values(self) -> None:
        """Testar valores padrão da configuração."""
        assert Config.COMMAND_PREFIX == "!"
        assert Config.CONTAINER_TIMEOUT == 15
        assert Config.MAX_CONTAINERS_PER_USER == 5
        assert Config.LOG_LEVEL == "INFO"

    @patch.dict(os.environ, {"DISCORD_TOKEN": ""}, clear=True)
    def test_config_validation_fails_without_token(self) -> None:
        """Testar que validação falha sem token."""
        # Forçar reload da config
        Config.TOKEN = ""
        assert Config.validate() is False

    @patch.dict(os.environ, {"DISCORD_TOKEN": "test_token"}, clear=True)
    def test_config_validation_passes_with_token(self) -> None:
        """Testar que validação passa com token."""
        Config.TOKEN = "test_token"
        assert Config.validate() is True


class TestEmojis:
    """Testes para a classe Emojis."""

    def test_emojis_has_success(self) -> None:
        """Testar que Emojis tem emoji de sucesso."""
        assert Emojis.SUCCESS == "✅"

    def test_emojis_has_error(self) -> None:
        """Testar que Emojis tem emoji de erro."""
        assert Emojis.ERROR == "❌"

    def test_emojis_has_warning(self) -> None:
        """Testar que Emojis tem emoji de aviso."""
        assert Emojis.WARNING == "⚠️"


class TestMessages:
    """Testes para a classe Messages."""

    def test_messages_has_no_permission(self) -> None:
        """Testar que Messages tem mensagem de sem permissão."""
        assert Messages.NO_PERMISSION == "❌ Você não tem permissão para usar este comando."

    def test_messages_has_container_not_found(self) -> None:
        """Testar que Messages tem mensagem de container não encontrado."""
        assert "Container não encontrado" in Messages.CONTAINER_NOT_FOUND

    def test_messages_internal_error_formatting(self) -> None:
        """Testar formatação de mensagem de erro interno."""
        error_msg = Messages.INTERNAL_ERROR.format(error="Test error")
        assert "Test error" in error_msg
