"""
Camada de Abstração do Banco de Dados
Facilita operações CRUD e gerenciamento de dados
"""

from __future__ import annotations

from typing import Any

import aiosqlite


class DatabaseManager:
    """Gerenciador de banco de dados com métodos utilitários"""

    def __init__(self, db_path: str) -> None:
        """
        Inicializa o gerenciador

        Args:
            db_path: Caminho para o arquivo do banco de dados
        """
        self.db_path: str = db_path

    async def execute(
        self, query: str, params: tuple = (), commit: bool = True
    ) -> aiosqlite.Cursor | None:
        """
        Executa uma query SQL

        Args:
            query: Query SQL a executar
            params: Parâmetros da query (para prevenir SQL injection)
            commit: Se deve fazer commit automaticamente

        Returns:
            Cursor do resultado ou None
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            if commit:
                await db.commit()
            return cursor

    async def fetch_one(self, query: str, params: tuple = ()) -> dict[str, Any] | None:
        """
        Busca um único resultado

        Args:
            query: Query SQL
            params: Parâmetros da query

        Returns:
            Dicionário com o resultado ou None
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetch_all(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """
        Busca todos os resultados

        Args:
            query: Query SQL
            params: Parâmetros da query

        Returns:
            Lista de dicionários com os resultados
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def insert(self, table: str, data: dict[str, Any]) -> int:
        """
        Insere dados em uma tabela

        Args:
            table: Nome da tabela
            data: Dicionário com os dados a inserir

        Returns:
            ID do registro inserido
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, tuple(data.values()))
            await db.commit()
            return cursor.lastrowid

    async def update(
        self, table: str, data: dict[str, Any], condition: str, params: tuple = ()
    ) -> int:
        """
        Atualiza dados em uma tabela

        Args:
            table: Nome da tabela
            data: Dicionário com os dados a atualizar
            condition: Condição WHERE
            params: Parâmetros da condição

        Returns:
            Número de linhas afetadas
        """
        set_clause = ", ".join([f"{k} = ?" for k in data])
        query = f"UPDATE {table} SET {set_clause} WHERE {condition}"

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, tuple(data.values()) + params)
            await db.commit()
            return cursor.rowcount

    async def delete(self, table: str, condition: str, params: tuple = ()) -> int:
        """
        Deleta dados de uma tabela

        Args:
            table: Nome da tabela
            condition: Condição WHERE
            params: Parâmetros da condição

        Returns:
            Número de linhas deletadas
        """
        query = f"DELETE FROM {table} WHERE {condition}"

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.rowcount

    async def table_exists(self, table_name: str) -> bool:
        """
        Verifica se uma tabela existe

        Args:
            table_name: Nome da tabela

        Returns:
            True se a tabela existe, False caso contrário
        """
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = await self.fetch_one(query, (table_name,))
        return result is not None

    async def create_index(self, index_name: str, table: str, columns: list[str]) -> None:
        """
        Cria um índice para melhorar performance

        Args:
            index_name: Nome do índice
            table: Nome da tabela
            columns: Lista de colunas para indexar
        """
        columns_str: str = ", ".join(columns)
        query: str = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({columns_str})"
        await self.execute(query, commit=True)
        await self.execute(query)
