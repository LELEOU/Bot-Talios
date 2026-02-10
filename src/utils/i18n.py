"""
Sistema de internacionalização (i18n) para suporte multilíngue.

Fornece traduções dinâmicas baseadas no idioma preferido do servidor,
com fallback automático para pt-BR.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from . import json_utils

if TYPE_CHECKING:
    import discord


class I18n:
    """Gerenciador de traduções com suporte a múltiplos idiomas."""

    _instance: ClassVar[I18n | None] = None
    _translations: ClassVar[dict[str, dict[str, Any]]] = {}
    _default_locale: ClassVar[str] = "pt-BR"
    _available_locales: ClassVar[list[str]] = ["pt-BR", "en-US", "es-ES"]

    def __new__(cls) -> I18n:
        """Implementa padrão singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Inicializa o sistema de i18n."""
        if not self._translations:
            self._load_translations()

    def _load_translations(self) -> None:
        """Carrega todos os arquivos de tradução disponíveis."""
        locales_dir = Path(__file__).parent.parent.parent / "locales"

        for locale in self._available_locales:
            locale_file = locales_dir / f"{locale}.json"
            if locale_file.exists():
                with locale_file.open(encoding="utf-8") as f:
                    self._translations[locale] = json_utils.load(f)
            else:
                print(f"⚠️ Arquivo de tradução não encontrado: {locale_file}")

    def get_locale(
        self,
        guild: discord.Guild | None = None,
        locale: discord.Locale | None = None,
    ) -> str:
        """
        Determina o locale a ser usado.

        Args:
            guild: Servidor Discord (usa preferred_locale se disponível)
            locale: Locale específico (tem prioridade sobre guild)

        Returns:
            Código do locale (ex: "pt-BR", "en-US", "es-ES")
        """
        if locale:
            locale_str = str(locale)
            return locale_str if locale_str in self._available_locales else self._default_locale

        if guild and guild.preferred_locale:
            guild_locale = str(guild.preferred_locale)
            # Mapeia variações de locale
            locale_map = {
                "pt_BR": "pt-BR",
                "pt-BR": "pt-BR",
                "en_US": "en-US",
                "en-US": "en-US",
                "en_GB": "en-US",  # UK -> US English
                "es_ES": "es-ES",
                "es-ES": "es-ES",
                "es_MX": "es-ES",  # Mexican Spanish -> Spain Spanish
            }
            return locale_map.get(guild_locale, self._default_locale)

        return self._default_locale

    def t(
        self,
        key: str,
        locale: str | None = None,
        guild: discord.Guild | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Obtém tradução para uma chave.

        Args:
            key: Chave de tradução em formato dot notation (ex: "commands.ban.success")
            locale: Locale específico (opcional)
            guild: Servidor Discord para auto-detectar locale (opcional)
            **kwargs: Variáveis para substituição na tradução

        Returns:
            Texto traduzido com variáveis substituídas

        Examples:
            >>> i18n = I18n()
            >>> i18n.t("commands.ban.success", user="John")
            "✅ John foi banido com sucesso!"

            >>> i18n.t("errors.no_permission", locale="en-US")
            "❌ You don't have permission to use this command."
        """
        # Determina o locale
        target_locale = locale or self.get_locale(guild)

        # Busca tradução
        translation = self._get_translation(key, target_locale)

        # Se não encontrou, tenta fallback para pt-BR
        if translation == key and target_locale != self._default_locale:
            translation = self._get_translation(key, self._default_locale)

        # Substitui variáveis
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except KeyError as e:
                print(f"⚠️ Variável não encontrada na tradução '{key}': {e}")

        return translation

    def _get_translation(self, key: str, locale: str) -> str:
        """
        Busca tradução no dicionário usando dot notation.

        Args:
            key: Chave em formato dot notation (ex: "commands.ban.success")
            locale: Código do locale

        Returns:
            Texto traduzido ou a própria chave se não encontrada
        """
        if locale not in self._translations:
            return key

        keys = key.split(".")
        value: Any = self._translations[locale]

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return key  # Chave não encontrada

        return str(value) if not isinstance(value, dict) else key

    def get_available_locales(self) -> list[str]:
        """Retorna lista de locales disponíveis."""
        return self._available_locales.copy()

    def reload(self) -> None:
        """Recarrega todos os arquivos de tradução."""
        self._translations.clear()
        self._load_translations()


# Singleton global para fácil importação
i18n = I18n()


# Função de conveniência para tradução rápida
def t(key: str, **kwargs: Any) -> str:
    """
    Atalho para tradução com locale padrão.

    Args:
        key: Chave de tradução
        **kwargs: Variáveis para substituição

    Returns:
        Texto traduzido

    Examples:
        >>> from src.utils.i18n import t
        >>> t("common.yes")
        "Sim"
    """
    return i18n.t(key, **kwargs)
