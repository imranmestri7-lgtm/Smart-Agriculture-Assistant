"""Stub config module providing a dummy DB connection for tests."""

class _DummyCursor:
    def execute(self, query):
        pass
    def fetchone(self):
        return ("test_db",)
    def close(self):
        pass

class _DummyConnection:
    def cursor(self):
        return _DummyCursor()
    def close(self):
        pass

def get_db_connection():
    # Return a dummy connection object; tests only check that the function exists.
    return _DummyConnection()
