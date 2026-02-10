"""
Utilitários JSON com suporte a orjson para performance.

orjson é 2-3x mais rápido que o json padrão do Python.
Fornece uma API compatível com json padrão para fácil migração.
"""

from __future__ import annotations

from typing import Any

try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    import json as stdlib_json

    HAS_ORJSON = False


def dumps(obj: Any, **kwargs: Any) -> str:
    """
    Serializar objeto para JSON string.

    Args:
        obj: Objeto Python para serializar
        **kwargs: Argumentos compatíveis com json.dumps (indent, ensure_ascii, etc.)

    Returns:
        String JSON

    Examples:
        >>> dumps({"name": "John", "age": 30})
        '{"name":"John","age":30}'

        >>> dumps({"name": "João"}, indent=2)
        '{\\n  "name": "João"\\n}'
    """
    if HAS_ORJSON:
        # orjson retorna bytes, precisamos converter para str
        # orjson.OPT_INDENT_2 para pretty print
        option = 0
        if kwargs.get("indent"):
            option |= orjson.OPT_INDENT_2
        if not kwargs.get("ensure_ascii", True):
            option |= orjson.OPT_NON_STR_KEYS

        return orjson.dumps(obj, option=option).decode("utf-8")

    # Fallback para json padrão
    return stdlib_json.dumps(obj, **kwargs)


def loads(s: str | bytes) -> Any:
    """
    Desserializar JSON string para objeto Python.

    Args:
        s: String ou bytes JSON

    Returns:
        Objeto Python

    Examples:
        >>> loads('{"name": "John", "age": 30}')
        {'name': 'John', 'age': 30}

        >>> loads(b'{"active": true}')
        {'active': True}
    """
    if HAS_ORJSON:
        # orjson aceita str ou bytes
        return orjson.loads(s)

    # Fallback para json padrão
    if isinstance(s, bytes):
        s = s.decode("utf-8")
    return stdlib_json.loads(s)


def dump(obj: Any, fp: Any, **kwargs: Any) -> None:
    """
    Serializar objeto para arquivo JSON.

    Args:
        obj: Objeto Python para serializar
        fp: File-like object para escrever
        **kwargs: Argumentos compatíveis com json.dump

    Examples:
        >>> with open("data.json", "w") as f:
        ...     dump({"name": "John"}, f, indent=2)
    """
    if HAS_ORJSON:
        option = 0
        if kwargs.get("indent"):
            option |= orjson.OPT_INDENT_2
        if not kwargs.get("ensure_ascii", True):
            option |= orjson.OPT_NON_STR_KEYS

        data = orjson.dumps(obj, option=option)
        fp.write(data.decode("utf-8"))
    else:
        stdlib_json.dump(obj, fp, **kwargs)


def load(fp: Any) -> Any:
    """
    Desserializar arquivo JSON para objeto Python.

    Args:
        fp: File-like object para ler

    Returns:
        Objeto Python

    Examples:
        >>> with open("data.json") as f:
        ...     data = load(f)
    """
    if HAS_ORJSON:
        content = fp.read()
        if isinstance(content, str):
            content = content.encode("utf-8")
        return orjson.loads(content)

    return stdlib_json.load(fp)


# Aliases para compatibilidade
JSONDecodeError = (
    orjson.JSONDecodeError if HAS_ORJSON else stdlib_json.JSONDecodeError  # type: ignore[attr-defined]
)

__all__ = ["HAS_ORJSON", "JSONDecodeError", "dump", "dumps", "load", "loads"]
