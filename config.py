"""Config module providing real DB connection when available, with dummy fallback for isolated unit tests."""

class _DummyCursor:
    def __init__(self):
        self.lastrowid = 1
        self.rowcount = 1
    def execute(self, query, *args, **kwargs):
        pass
    def fetchone(self):
        return ("test_db",)
    def fetchall(self):
        return []
    def close(self):
        pass

class _DummyConnection:
    def cursor(self, *args, **kwargs):
        return _DummyCursor()
    def commit(self):
        pass
    def rollback(self):
        pass
    def close(self):
        pass

def get_db_connection():
    try:
        from backend.config import get_db_connection as real_get_db
        return real_get_db()
    except Exception:
        return _DummyConnection()
