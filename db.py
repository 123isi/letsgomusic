import sqlite3

def init_db():
    with sqlite3.connect("playlist.db") as conn:
        cursor = conn.cursor()
        # 플레이리스트 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlist (
                rank INTEGER,
                title TEXT,
                artist TEXT,
                albumImageUrl TEXT
            )
        """)
        # 사용자 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT PRIMARY KEY,
        password TEXT NOT NULL
            )
        """)
