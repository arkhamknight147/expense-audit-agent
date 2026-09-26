"""Append-only, hash-chained audit log in SQLite (T3.5, D3, ADR-021).

The code exposes only `append_event`, `events` and `verify_chain`: there is no update or
delete path. Each row stores the hash of the previous row, so editing or deleting any past
row breaks the chain and `verify_chain` reports where.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import DB_PATH

GENESIS = "0" * 64
SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  claim_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  reason_code TEXT,
  payload TEXT NOT NULL,
  prev_hash TEXT NOT NULL,
  hash TEXT NOT NULL
);
"""


def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), check_same_thread=False)
    con.execute(SCHEMA)
    return con


def _hash(prev: str, claim_id: str, ts: str, actor: str, action: str, reason: str | None, payload: str) -> str:
    body = json.dumps([prev, claim_id, ts, actor, action, reason, payload], ensure_ascii=False)
    return hashlib.sha256(body.encode()).hexdigest()


def append_event(con: sqlite3.Connection, claim_id: str, actor: str, action: str, payload: dict,
                 reason_code: str | None = None) -> str:
    row = con.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    prev = row[0] if row else GENESIS
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    h = _hash(prev, claim_id, ts, actor, action, reason_code, body)
    con.execute("INSERT INTO audit_log (claim_id, ts, actor, action, reason_code, payload, prev_hash, hash) "
                "VALUES (?,?,?,?,?,?,?,?)", (claim_id, ts, actor, action, reason_code, body, prev, h))
    con.commit()
    return h


def events(con: sqlite3.Connection, claim_id: str | None = None) -> list[dict]:
    q = "SELECT id, claim_id, ts, actor, action, reason_code, payload, prev_hash, hash FROM audit_log"
    rows = con.execute(q + (" WHERE claim_id=? ORDER BY id" if claim_id else " ORDER BY id"),
                       (claim_id,) if claim_id else ()).fetchall()
    keys = ["id", "claim_id", "ts", "actor", "action", "reason_code", "payload", "prev_hash", "hash"]
    return [dict(zip(keys, r)) | {"payload": json.loads(r[6])} for r in rows]


def verify_chain(con: sqlite3.Connection) -> tuple[bool, int | None]:
    """Return (ok, first_bad_row_id)."""
    prev = GENESIS
    for rid, cid, ts, actor, action, reason, payload, prev_hash, h in con.execute(
            "SELECT id, claim_id, ts, actor, action, reason_code, payload, prev_hash, hash FROM audit_log ORDER BY id"):
        if prev_hash != prev or _hash(prev, cid, ts, actor, action, reason, payload) != h:
            return False, rid
        prev = h
    return True, None
