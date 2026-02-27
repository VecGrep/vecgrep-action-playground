"""Database connection pool and query helpers."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Generator


DATABASE_URL = os.environ.get("DATABASE_URL", "app.db")
POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "5"))


@dataclass
class QueryResult:
    rows: list[dict]
    row_count: int


class ConnectionPool:
    """Thread-safe SQLite connection pool."""

    def __init__(self, database_url: str, pool_size: int = POOL_SIZE) -> None:
        self._database_url = database_url
        self._pool: Queue[sqlite3.Connection] = Queue(maxsize=pool_size)
        for _ in range(pool_size):
            conn = sqlite3.connect(database_url, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._pool.put(conn)

    @contextmanager
    def acquire(self) -> Generator[sqlite3.Connection, None, None]:
        try:
            conn = self._pool.get(timeout=5)
        except Empty:
            raise RuntimeError("Connection pool exhausted — no available connections.")
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            self._pool.put(conn)

    def close_all(self) -> None:
        while not self._pool.empty():
            conn = self._pool.get_nowait()
            conn.close()


_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(DATABASE_URL, POOL_SIZE)
    return _pool


def execute(sql: str, params: tuple = ()) -> QueryResult:
    """Execute a parameterized query and return all rows."""
    with get_pool().acquire() as conn:
        cursor = conn.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
        return QueryResult(rows=rows, row_count=cursor.rowcount)


def execute_many(sql: str, params_list: list[tuple]) -> int:
    """Execute a parameterized query for multiple rows. Returns affected row count."""
    with get_pool().acquire() as conn:
        cursor = conn.executemany(sql, params_list)
        return cursor.rowcount
