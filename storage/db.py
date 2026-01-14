import sqlite3
from pathlib import Path

# from storage.init_db import init_db
# init_db()

DB_PATH = Path(__file__).parent / "prompt_engine.db"

def get_conn():
    return sqlite3.connect(DB_PATH)
