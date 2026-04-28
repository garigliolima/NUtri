import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "nuutri.db")
MAX_HISTORY = 30


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")  # melhor concorrência
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db():
    """Cria as tabelas se ainda não existirem."""
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id     INTEGER PRIMARY KEY,
                first_name      TEXT,
                username        TEXT,
                nome            TEXT,
                peso            TEXT,
                altura          TEXT,
                idade           TEXT,
                sexo            TEXT,
                objetivo        TEXT,
                nivel_atividade TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL REFERENCES users(telegram_id),
                role        TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content     TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS plans (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL REFERENCES users(telegram_id),
                plan_json   TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_messages_user
                ON messages(telegram_id, created_at);
        """)
        # Migration: adiciona coluna bioimpedancia se não existir
        try:
            con.execute("ALTER TABLE users ADD COLUMN bioimpedancia TEXT")
        except sqlite3.OperationalError:
            pass  # coluna já existe
    logger.info(f"Banco de dados inicializado: {DB_PATH}")


# ── Usuários ───────────────────────────────────────────────────────────────────

def upsert_user(telegram_id: int, first_name: str = "", username: str = ""):
    """Cria o usuário se não existir; atualiza nome/username se existir."""
    with _conn() as con:
        con.execute("""
            INSERT INTO users (telegram_id, first_name, username)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                first_name = excluded.first_name,
                username   = excluded.username,
                updated_at = datetime('now')
        """, (telegram_id, first_name, username))


def update_profile(telegram_id: int, **fields):
    """
    Atualiza campos do perfil do usuário.
    Campos válidos: nome, peso, altura, idade, sexo, objetivo, nivel_atividade
    """
    allowed = {"nome", "peso", "altura", "idade", "sexo", "objetivo", "nivel_atividade"}
    to_set = {k: v for k, v in fields.items() if k in allowed and v}
    if not to_set:
        return
    to_set["updated_at"] = datetime.utcnow().isoformat()
    cols = ", ".join(f"{k} = ?" for k in to_set)
    vals = list(to_set.values()) + [telegram_id]
    with _conn() as con:
        con.execute(f"UPDATE users SET {cols} WHERE telegram_id = ?", vals)


def get_profile(telegram_id: int) -> dict:
    """Retorna o perfil completo do usuário como dict."""
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        return dict(row) if row else {}


def save_bioimpedancia(telegram_id: int, data: dict) -> None:
    """Persiste dados de bioimpedância no perfil do usuário."""
    with _conn() as con:
        con.execute(
            "UPDATE users SET bioimpedancia = ?, updated_at = datetime('now') WHERE telegram_id = ?",
            (json.dumps(data, ensure_ascii=False), telegram_id),
        )


def get_bioimpedancia(telegram_id: int) -> dict:
    """Retorna dados de bioimpedância salvos ou {} se ausente."""
    with _conn() as con:
        row = con.execute(
            "SELECT bioimpedancia FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
    if row and row["bioimpedancia"]:
        return json.loads(row["bioimpedancia"])
    return {}


# ── Histórico de mensagens ─────────────────────────────────────────────────────

def save_message(telegram_id: int, role: str, content):
    """
    Salva uma mensagem no histórico.
    content pode ser string (texto) ou list (conteúdo misto com imagem).
    Imagens são descartadas do histórico persistido para economizar espaço.
    """
    if isinstance(content, list):
        # Filtra blocos de imagem — guarda só o texto
        text_parts = [
            block["text"] for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        stored = " ".join(text_parts) if text_parts else "[imagem]"
    else:
        stored = content

    with _conn() as con:
        con.execute(
            "INSERT INTO messages (telegram_id, role, content) VALUES (?, ?, ?)",
            (telegram_id, role, stored),
        )
        # Mantém apenas as últimas MAX_HISTORY mensagens por usuário
        con.execute("""
            DELETE FROM messages
            WHERE telegram_id = ?
              AND id NOT IN (
                SELECT id FROM messages
                WHERE telegram_id = ?
                ORDER BY id DESC
                LIMIT ?
              )
        """, (telegram_id, telegram_id, MAX_HISTORY))


def get_history(telegram_id: int) -> list[dict]:
    """
    Retorna o histórico recente no formato esperado pela API do Claude:
    [{"role": "user"|"assistant", "content": "..."}]
    """
    with _conn() as con:
        rows = con.execute("""
            SELECT role, content FROM messages
            WHERE telegram_id = ?
            ORDER BY id ASC
        """, (telegram_id,)).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def clear_history(telegram_id: int):
    """Apaga todo o histórico de conversa do usuário."""
    with _conn() as con:
        con.execute("DELETE FROM messages WHERE telegram_id = ?", (telegram_id,))


# ── Planos gerados ─────────────────────────────────────────────────────────────

def save_plan(telegram_id: int, plan_data: dict):
    """Persiste o plano nutricional gerado para histórico e analytics."""
    with _conn() as con:
        con.execute(
            "INSERT INTO plans (telegram_id, plan_json) VALUES (?, ?)",
            (telegram_id, json.dumps(plan_data, ensure_ascii=False)),
        )
    # Atualiza perfil com os dados coletados no plano
    update_profile(
        telegram_id,
        nome=plan_data.get("user_name"),
        peso=plan_data.get("peso"),
        altura=plan_data.get("altura"),
        idade=plan_data.get("idade"),
        sexo=plan_data.get("sexo"),
        objetivo=plan_data.get("objetivo"),
        nivel_atividade=plan_data.get("nivel_atividade"),
    )


def get_plans(telegram_id: int) -> list[dict]:
    """Retorna todos os planos gerados pelo usuário."""
    with _conn() as con:
        rows = con.execute("""
            SELECT plan_json, created_at FROM plans
            WHERE telegram_id = ?
            ORDER BY created_at DESC
        """, (telegram_id,)).fetchall()
    return [
        {"plan": json.loads(r["plan_json"]), "created_at": r["created_at"]}
        for r in rows
    ]


# ── Rate limiting ──────────────────────────────────────────────────────────────

def count_messages_last_hour(telegram_id: int) -> int:
    """Conta mensagens enviadas pelo usuário na última hora."""
    since = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    with _conn() as con:
        row = con.execute("""
            SELECT COUNT(*) as total FROM messages
            WHERE telegram_id = ? AND role = 'user' AND created_at > ?
        """, (telegram_id, since)).fetchone()
    return row["total"] if row else 0


# ── Analytics ─────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    """Retorna estatísticas gerais do bot."""
    with _conn() as con:
        users     = con.execute("SELECT COUNT(*) as n FROM users").fetchone()["n"]
        msgs      = con.execute("SELECT COUNT(*) as n FROM messages WHERE role='user'").fetchone()["n"]
        plans     = con.execute("SELECT COUNT(*) as n FROM plans").fetchone()["n"]
        top_objs  = con.execute("""
            SELECT objetivo, COUNT(*) as n FROM users
            WHERE objetivo IS NOT NULL
            GROUP BY objetivo ORDER BY n DESC LIMIT 5
        """).fetchall()
    return {
        "total_users": users,
        "total_messages": msgs,
        "total_plans": plans,
        "top_objectives": [{"objetivo": r["objetivo"], "count": r["n"]} for r in top_objs],
    }
