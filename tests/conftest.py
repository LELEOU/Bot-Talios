"""
🧪 Pytest Configuration - Discord Bot Tests
==========================================

Este arquivo configura fixtures e utilitários compartilhados
para todos os testes do bot.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator

import discord
import pytest
from discord.ext import commands


# ============================================================================
# CONFIGURAÇÃO DE ASYNCIO
# ============================================================================
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Criar event loop para testes async."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# MOCK BOT
# ============================================================================
@pytest.fixture
async def mock_bot() -> AsyncGenerator[commands.Bot, None]:
    """Criar instância mock do bot para testes.

    Yields:
        Bot instance configurada para testes
    """
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True

    bot = commands.Bot(
        command_prefix="!",
        intents=intents,
        help_command=None,
    )

    yield bot

    # Cleanup
    await bot.close()


# ============================================================================
# MOCK GUILD
# ============================================================================
@pytest.fixture
def mock_guild() -> discord.Guild:
    """Criar mock de Guild para testes.

    Returns:
        Mock Guild object
    """
    # Nota: Implementar mock completo quando necessário
    # Por enquanto retorna None, mas pode ser expandido
    return None  # type: ignore


# ============================================================================
# MOCK USER
# ============================================================================
@pytest.fixture
def mock_user() -> discord.User:
    """Criar mock de User para testes.

    Returns:
        Mock User object
    """
    # Nota: Implementar mock completo quando necessário
    return None  # type: ignore


# ============================================================================
# MOCK INTERACTION
# ============================================================================
@pytest.fixture
def mock_interaction() -> discord.Interaction:
    """Criar mock de Interaction para testes de slash commands.

    Returns:
        Mock Interaction object
    """
    # Nota: Implementar mock completo quando necessário
    return None  # type: ignore


# ============================================================================
# DATABASE
# ============================================================================
@pytest.fixture
async def test_database() -> AsyncGenerator[str, None]:
    """Criar database temporário para testes.

    Yields:
        Path to temporary test database
    """
    import tempfile
    from pathlib import Path

    # Criar database temporário
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "test.db"

    # Inicializar database
    from src.utils.database import Database

    db = Database()
    db.db_path = str(db_path)
    await db.create_tables()

    yield str(db_path)

    # Cleanup
    if db_path.exists():
        db_path.unlink()
    temp_dir.rmdir()


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================
@pytest.fixture
def test_config() -> dict:
    """Configuração de teste para o bot.

    Returns:
        Dict com configurações de teste
    """
    return {
        "TOKEN": "test_token_123",
        "GUILD_ID": 123456789,
        "OWNER_ID": 987654321,
        "DEBUG_MODE": True,
        "COMMAND_PREFIX": "!",
    }


# ============================================================================
# MARKERS
# ============================================================================
def pytest_configure(config: pytest.Config) -> None:
    """Configurar markers customizados."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
