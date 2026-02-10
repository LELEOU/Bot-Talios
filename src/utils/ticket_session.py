"""
Ticket Session - Gerencia sessões de configuração de ticket por usuário
Evita depender da mensagem efêmera original para estado
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


class TicketSession:
    def __init__(self) -> None:
        self.sessions: dict[int, dict[str, Any]] = {}  # key: user_id -> session
        self.session_max_seconds: int = 15 * 60  # 15 minutos (limite de edição de original)

    def get_session(self, user_id: int) -> dict[str, Any] | None:
        """Buscar sessão ativa do usuário"""
        session = self.sessions.get(user_id)
        if not session:
            return None

        # Verificar se a sessão expirou
        if time.time() - session["started_at"] > self.session_max_seconds:
            del self.sessions[user_id]
            return None

        return session

    def start_session(self, user_id: int, initial_config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Iniciar nova sessão para o usuário"""
        if initial_config is None:
            initial_config = {}

        session: dict[str, Any] = {
            "user_id": user_id,
            "config": initial_config.copy(),
            "started_at": time.time(),
            "last_update": time.time(),
            "version": 1,
        }

        self.sessions[user_id] = session
        return session

    def update_session(
        self, user_id: int, mutate_fn: Callable[[dict[str, Any]], None]
    ) -> dict[str, Any] | None:
        """Atualizar sessão existente usando função de mutação"""
        session = self.get_session(user_id)
        if not session:
            return None

        # Aplicar mudanças na configuração
        mutate_fn(session["config"])

        # Atualizar metadados
        session["last_update"] = time.time()
        session["version"] += 1

        return session

    def end_session(self, user_id: int) -> bool:
        """Finalizar sessão do usuário"""
        if user_id in self.sessions:
            del self.sessions[user_id]
            return True
        return False

    def ensure_session(self, user_id: int) -> dict[str, Any]:
        """Garantir que existe uma sessão para o usuário"""
        session = self.get_session(user_id)
        if session:
            return session
        return self.start_session(user_id)

    def get_session_config(self, user_id: int, key: str | None = None) -> Any:
        """Buscar valor específico da configuração da sessão"""
        session = self.get_session(user_id)
        if not session:
            return None

        if key:
            return session["config"].get(key)
        return session["config"]

    def set_session_config(self, user_id: int, key: str, value: Any) -> bool:
        """Definir valor específico na configuração da sessão"""

        def update_config(config: dict[str, Any]) -> None:
            config[key] = value

        result = self.update_session(user_id, update_config)
        return result is not None

    def get_all_sessions(self) -> dict[int, dict[str, Any]]:
        """Buscar todas as sessões ativas (para debug)"""
        # Limpar sessões expiradas primeiro
        current_time = time.time()
        expired_users = []

        for user_id, session in self.sessions.items():
            if current_time - session["started_at"] > self.session_max_seconds:
                expired_users.append(user_id)

        for user_id in expired_users:
            del self.sessions[user_id]

        return self.sessions.copy()

    def clear_all_sessions(self) -> int:
        """Limpar todas as sessões (retorna quantidade removida)"""
        count: int = len(self.sessions)
        self.sessions.clear()
        return count

    def get_session_info(self, user_id: int) -> dict[str, Any] | None:
        """Buscar informações da sessão sem a configuração"""
        session = self.get_session(user_id)
        if not session:
            return None

        return {
            "user_id": session["user_id"],
            "started_at": session["started_at"],
            "last_update": session["last_update"],
            "version": session["version"],
            "age_seconds": time.time() - session["started_at"],
            "time_left_seconds": self.session_max_seconds - (time.time() - session["started_at"]),
        }

    def extend_session(self, user_id: int, extra_seconds: int = 900) -> bool:
        """Estender tempo de vida da sessão (padrão: +15 minutos)"""
        session = self.get_session(user_id)
        if not session:
            return False

        # Resetar o tempo de início para estender a vida
        session["started_at"] = time.time() - (self.session_max_seconds - extra_seconds)
        session["last_update"] = time.time()

        return True


# Instância global para uso em todo o bot
ticket_session_manager: TicketSession = TicketSession()


# Funções de conveniência para compatibilidade com o código JS
def get_session(user_id: int) -> dict[str, Any] | None:
    """Buscar sessão ativa do usuário"""
    return ticket_session_manager.get_session(user_id)


def start_session(user_id: int, initial_config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Iniciar nova sessão para o usuário"""
    return ticket_session_manager.start_session(user_id, initial_config)


def update_session(
    user_id: int, mutate_fn: Callable[[dict[str, Any]], None]
) -> dict[str, Any] | None:
    """Atualizar sessão existente usando função de mutação"""
    return ticket_session_manager.update_session(user_id, mutate_fn)


def end_session(user_id: int) -> bool:
    """Finalizar sessão do usuário"""
    return ticket_session_manager.end_session(user_id)


def ensure_session(user_id: int) -> dict[str, Any]:
    """Garantir que existe uma sessão para o usuário"""
    return ticket_session_manager.ensure_session(user_id)


# Constante para compatibilidade
SESSION_MAX_MS = ticket_session_manager.session_max_seconds * 1000
