"""Cache SQLite pour les synthèses du chercheur (TTL 24h)."""
import hashlib
import sqlite3
import time
from pathlib import Path

DB_PATH = Path("cache.db")
TTL = 86_400  # 24 h


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_cache (
            key        TEXT PRIMARY KEY,
            focus      TEXT,
            result     TEXT,
            created_at REAL
        )
    """)
    return conn


def cache_key(idea: str, focus: str, queries: list[str]) -> str:
    raw = idea + "|" + focus + "|" + "\n".join(sorted(queries))
    return hashlib.sha256(raw.encode()).hexdigest()


def get(key: str) -> str | None:
    """Retourne le résultat mis en cache si encore valide, sinon None."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT result, created_at FROM search_cache WHERE key = ?", (key,)
        ).fetchone()
    if row and (time.time() - row[1]) < TTL:
        return row[0]
    return None


def put(key: str, focus: str, result: str) -> None:
    """Stocke ou rafraîchit une entrée de cache."""
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO search_cache "
            "(key, focus, result, created_at) VALUES (?, ?, ?, ?)",
            (key, focus, result, time.time()),
        )


def stats() -> dict:
    """Retourne le nombre d'entrées valides et expirées."""
    now = time.time()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT created_at FROM search_cache"
        ).fetchall()
    valid = sum(1 for (ts,) in rows if now - ts < TTL)
    return {"total": len(rows), "valid": valid, "expired": len(rows) - valid}
