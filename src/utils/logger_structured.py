"""
Sistema de Logs Estruturados de Alto Desempenho
Usa structlog para logging estruturado com fallback para colorlog
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# Tentar importar structlog (logging estruturado de alta performance)
try:
    import structlog

    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False
    import colorlog

# Configuração global do structlog
_structlog_configured = False


def configure_structlog() -> None:
    """Configurar structlog com processadores otimizados."""
    global _structlog_configured
    
    if _structlog_configured or not HAS_STRUCTLOG:
        return
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    _structlog_configured = True


class StructuredLogger:
    """
    Logger estruturado de alto desempenho.
    
    Usa structlog quando disponível (3-5x mais rápido, logs estruturados).
    Fallback para colorlog se structlog não estiver instalado.
    """

    def __init__(self, name: str = "DiscordBot") -> None:
        """
        Inicializa o logger.

        Args:
            name: Nome do logger
        """
        self.name = name
        
        if HAS_STRUCTLOG:
            configure_structlog()
            self.logger = structlog.get_logger(name)
            self.is_structured = True
        else:
            # Fallback para colorlog
            self.logger = colorlog.getLogger(name)
            self.is_structured = False
            
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

    def _log(self, level: str, message: str, **context: Any) -> None:
        """
        Log interno com contexto estruturado.
        
        Args:
            level: Nível do log (debug, info, warning, error, critical)
            message: Mensagem a logar
            **context: Contexto adicional (apenas para structlog)
        """
        if self.is_structured:
            # structlog - logging estruturado
            getattr(self.logger, level)(message, **context)
        else:
            # colorlog - fallback
            getattr(self.logger, level)(message)

    def success(self, message: str, **context: Any) -> None:
        """
        Log de sucesso (verde).
        
        Args:
            message: Mensagem de sucesso
            **context: Contexto adicional (guild_id, user_id, etc.)
        """
        self._log("info", f"✅ {message}", event_type="success", **context)

    def info(self, message: str, **context: Any) -> None:
        """
        Log de informação (azul).
        
        Args:
            message: Mensagem informativa
            **context: Contexto adicional
        """
        self._log("info", f"ℹ {message}", event_type="info", **context)

    def warning(self, message: str, **context: Any) -> None:
        """
        Log de aviso (amarelo).
        
        Args:
            message: Mensagem de aviso
            **context: Contexto adicional
        """
        self._log("warning", f"⚠️  {message}", event_type="warning", **context)

    def error(self, message: str, exc: Exception | None = None, **context: Any) -> None:
        """
        Log de erro (vermelho).
        
        Args:
            message: Mensagem de erro
            exc: Exception opcional
            **context: Contexto adicional
        """
        if self.is_structured:
            if exc:
                self.logger.error(f"❌ {message}", exc_info=exc, event_type="error", **context)
            else:
                self.logger.error(f"❌ {message}", event_type="error", **context)
        else:
            self.logger.error(f"❌ {message}")
            if exc:
                self.logger.exception(exc)

    def debug(self, message: str, **context: Any) -> None:
        """
        Log de debug (cyan).
        
        Args:
            message: Mensagem de debug
            **context: Contexto adicional
        """
        self._log("debug", f"🔧 {message}", event_type="debug", **context)

    def command(self, command: str, user: str, guild_id: str | None = None, **context: Any) -> None:
        """
        Log de comando executado.
        
        Args:
            command: Nome do comando
            user: Usuário que executou
            guild_id: ID do servidor (opcional)
            **context: Contexto adicional
        """
        self._log(
            "info",
            f"⚡ Comando '{command}' executado por {user}",
            event_type="command",
            command=command,
            user=user,
            guild_id=guild_id,
            **context,
        )

    def extension(self, extension: str, status: str = "carregada", **context: Any) -> None:
        """
        Log de extensão carregada.
        
        Args:
            extension: Nome da extensão
            status: Status (carregada, recarregada, erro)
            **context: Contexto adicional
        """
        if status == "erro":
            self._log(
                "error",
                f"📦 Erro ao carregar '{extension}'",
                event_type="extension_error",
                extension=extension,
                **context,
            )
        else:
            self._log(
                "info",
                f"📦 Extensão '{extension}' {status}",
                event_type="extension_loaded",
                extension=extension,
                status=status,
                **context,
            )

    def performance(self, operation: str, duration_ms: float, **context: Any) -> None:
        """
        Log de performance/timing.
        
        Args:
            operation: Nome da operação
            duration_ms: Duração em milissegundos
            **context: Contexto adicional
        """
        self._log(
            "info",
            f"⏱️  {operation} levou {duration_ms:.2f}ms",
            event_type="performance",
            operation=operation,
            duration_ms=duration_ms,
            **context,
        )

    def database(self, query: str, duration_ms: float | None = None, **context: Any) -> None:
        """
        Log de operação de database.
        
        Args:
            query: Query executada (simplificada)
            duration_ms: Duração em milissegundos (opcional)
            **context: Contexto adicional
        """
        msg = f"💾 Database: {query}"
        if duration_ms:
            msg += f" ({duration_ms:.2f}ms)"
        
        self._log(
            "debug",
            msg,
            event_type="database",
            query=query,
            duration_ms=duration_ms,
            **context,
        )

    def security(self, event: str, severity: str = "info", **context: Any) -> None:
        """
        Log de evento de segurança.
        
        Args:
            event: Descrição do evento
            severity: Severidade (info, warning, error)
            **context: Contexto adicional
        """
        level_map = {"info": "info", "warning": "warning", "error": "error"}
        level = level_map.get(severity, "info")
        
        self._log(
            level,
            f"🛡️  {event}",
            event_type="security",
            severity=severity,
            **context,
        )


# Instância global
logger = StructuredLogger()


# Função para obter logger com nome customizado
def get_logger(name: str) -> StructuredLogger:
    """
    Obter logger com nome específico.
    
    Args:
        name: Nome do logger
        
    Returns:
        Instância de StructuredLogger
    """
    return StructuredLogger(name)
