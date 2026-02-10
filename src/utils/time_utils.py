"""
Time Utilities - Wrapper de alto desempenho para parsing de datas
Usa ciso8601 (C extension) quando disponível, fallback para datetime padrão
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Tentar importar ciso8601 (C extension - muito mais rápido)
try:
    import ciso8601

    HAS_CISO8601 = True
except ImportError:
    HAS_CISO8601 = False


def parse_datetime(date_string: str) -> datetime | None:
    """
    Parse string ISO 8601 para datetime.
    
    Usa ciso8601 (C extension) se disponível - até 10x mais rápido.
    Fallback para datetime.fromisoformat() se ciso8601 não estiver instalado.
    
    Args:
        date_string: String em formato ISO 8601 (ex: '2025-10-02T15:30:00Z')
        
    Returns:
        datetime object ou None se parsing falhar
        
    Examples:
        >>> parse_datetime('2025-10-02T15:30:00Z')
        datetime.datetime(2025, 10, 2, 15, 30, tzinfo=datetime.timezone.utc)
        
        >>> parse_datetime('2025-10-02T15:30:00+03:00')
        datetime.datetime(2025, 10, 2, 15, 30, tzinfo=datetime.timezone(datetime.timedelta(seconds=10800)))
    """
    if not date_string:
        return None
    
    try:
        if HAS_CISO8601:
            # ciso8601 é 5-10x mais rápido que datetime padrão
            return ciso8601.parse_datetime(date_string)
        else:
            # Fallback para stdlib
            # Remover 'Z' e substituir por '+00:00' para compatibilidade
            if date_string.endswith('Z'):
                date_string = date_string[:-1] + '+00:00'
            return datetime.fromisoformat(date_string)
    except (ValueError, TypeError):
        return None


def parse_datetime_utc(date_string: str) -> datetime | None:
    """
    Parse string ISO 8601 para datetime UTC.
    
    Garante que o resultado sempre seja timezone-aware em UTC.
    
    Args:
        date_string: String em formato ISO 8601
        
    Returns:
        datetime object em UTC ou None se parsing falhar
    """
    dt = parse_datetime(date_string)
    if dt is None:
        return None
    
    # Converter para UTC se tiver timezone
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    
    # Assumir UTC se não tiver timezone
    return dt.replace(tzinfo=timezone.utc)


def now_utc() -> datetime:
    """
    Obter datetime atual em UTC.
    
    Returns:
        datetime object timezone-aware em UTC
    """
    return datetime.now(timezone.utc)


def to_iso8601(dt: datetime) -> str:
    """
    Converter datetime para string ISO 8601.
    
    Args:
        dt: datetime object
        
    Returns:
        String ISO 8601 (ex: '2025-10-02T15:30:00+00:00')
    """
    return dt.isoformat()


def to_iso8601_utc(dt: datetime) -> str:
    """
    Converter datetime para string ISO 8601 em UTC.
    
    Args:
        dt: datetime object
        
    Returns:
        String ISO 8601 em UTC com 'Z' suffix (ex: '2025-10-02T15:30:00Z')
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    
    # Substituir '+00:00' por 'Z' (formato mais compacto)
    return dt.isoformat().replace('+00:00', 'Z')


def timestamp_to_datetime(timestamp: int | float) -> datetime:
    """
    Converter Unix timestamp para datetime UTC.
    
    Args:
        timestamp: Unix timestamp (segundos desde 1970-01-01)
        
    Returns:
        datetime object timezone-aware em UTC
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> float:
    """
    Converter datetime para Unix timestamp.
    
    Args:
        dt: datetime object
        
    Returns:
        Unix timestamp (float)
    """
    return dt.timestamp()


def format_relative_time(dt: datetime) -> str:
    """
    Formatar datetime como tempo relativo (ex: '5 minutos atrás').
    
    Args:
        dt: datetime object
        
    Returns:
        String formatada (ex: '5 minutos atrás', 'há 2 horas', 'ontem')
    """
    now = now_utc()
    
    # Garantir que dt seja timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    
    diff = now - dt
    seconds = int(diff.total_seconds())
    
    if seconds < 0:
        return "no futuro"
    
    if seconds < 60:
        return "agora mesmo"
    
    minutes = seconds // 60
    if minutes < 60:
        return f"há {minutes} minuto{'s' if minutes != 1 else ''}"
    
    hours = minutes // 60
    if hours < 24:
        return f"há {hours} hora{'s' if hours != 1 else ''}"
    
    days = hours // 24
    if days < 7:
        return f"há {days} dia{'s' if days != 1 else ''}"
    
    weeks = days // 7
    if weeks < 4:
        return f"há {weeks} semana{'s' if weeks != 1 else ''}"
    
    months = days // 30
    if months < 12:
        return f"há {months} {'mês' if months == 1 else 'meses'}"
    
    years = days // 365
    return f"há {years} ano{'s' if years != 1 else ''}"


def is_recent(dt: datetime, max_age_seconds: int = 300) -> bool:
    """
    Verificar se datetime é recente (dentro de max_age_seconds).
    
    Args:
        dt: datetime object
        max_age_seconds: idade máxima em segundos (padrão: 5 minutos)
        
    Returns:
        True se dt for recente, False caso contrário
    """
    now = now_utc()
    
    # Garantir que dt seja timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    
    diff = now - dt
    return diff.total_seconds() <= max_age_seconds


# Funções de conveniência para compatibilidade
def utcnow() -> datetime:
    """Alias para now_utc() - compatibilidade com código antigo."""
    return now_utc()


def parse_iso8601(date_string: str) -> datetime | None:
    """Alias para parse_datetime() - nome mais explícito."""
    return parse_datetime(date_string)


# Constantes úteis
SECONDS_IN_MINUTE = 60
SECONDS_IN_HOUR = 3600
SECONDS_IN_DAY = 86400
SECONDS_IN_WEEK = 604800
SECONDS_IN_MONTH = 2592000  # 30 dias
SECONDS_IN_YEAR = 31536000  # 365 dias
