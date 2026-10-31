"""Stub config module providing a dummy DB connection for tests."""

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
    # Return a dummy connection object; tests only check that the function exists.
    return _DummyConnection()
