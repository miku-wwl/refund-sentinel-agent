import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from .models import Problem


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    """Product facts and provider observations only. Runtime owns Runs/Actions and claiming."""

    def __init__(self, path):
        self.path = path

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.path, timeout=2)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def provision(self):
        with self.db() as db:
            db.executescript("""
                CREATE TABLE incidents (id TEXT PRIMARY KEY, capture_id TEXT UNIQUE NOT NULL,
                    data TEXT NOT NULL, created_at TEXT NOT NULL) STRICT;
                CREATE TABLE observations (id TEXT PRIMARY KEY, effect_key TEXT NOT NULL,
                    payload_digest TEXT NOT NULL, data TEXT NOT NULL,
                    created_at TEXT NOT NULL) STRICT;
            """)

    def reserve(self, capture_id, message, modes):
        incident_id = str(uuid4())
        data = {
            "id": incident_id,
            "capture_id": capture_id,
            "message": message,
            "modes": modes,
            "analysis_state": "ANALYZING",
        }
        try:
            with self.db() as db:
                db.execute(
                    "INSERT INTO incidents VALUES (?,?,?,?)",
                    (incident_id, capture_id, json.dumps(data), now()),
                )
        except sqlite3.IntegrityError:
            raise Problem("CAPTURE_ALREADY_HAS_INCIDENT", 409) from None
        return incident_id

    def get(self, incident_id):
        with self.db() as db:
            row = db.execute("SELECT data FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if row is None:
            raise Problem("INCIDENT_NOT_FOUND", 404)
        return json.loads(row[0])

    def update(self, incident_id, **fields):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT data FROM incidents WHERE id=?", (incident_id,)).fetchone()
            if row is None:
                raise Problem("INCIDENT_NOT_FOUND", 404)
            data = json.loads(row[0]) | fields
            db.execute("UPDATE incidents SET data=? WHERE id=?", (json.dumps(data), incident_id))

    def list(self):
        with self.db() as db:
            return [
                json.loads(row[0])
                for row in db.execute(
                    "SELECT data FROM incidents ORDER BY created_at DESC LIMIT 100"
                )
            ]

    def observe(self, effect_key, digest, **data):
        observation_id = str(uuid4())
        with self.db() as db:
            db.execute(
                "INSERT INTO observations VALUES (?,?,?,?,?)",
                (observation_id, effect_key, digest, json.dumps(data), now()),
            )
        return observation_id

    def observations(self, effect_key):
        with self.db() as db:
            return [
                dict(row) | {"data": json.loads(row["data"])}
                for row in db.execute(
                    "SELECT * FROM observations WHERE effect_key=? ORDER BY created_at",
                    (effect_key,),
                )
            ]
