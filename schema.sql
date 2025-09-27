PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS votes;
    DROP TABLE IF EXISTS signatures;
    DROP TABLE IF EXISTS initiatives;
    DROP TABLE IF EXISTS users;

    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        is_admin INTEGER DEFAULT 0
    );

    CREATE TABLE initiatives (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TEXT DEFAULT (datetime('now')),
        active INTEGER DEFAULT 1,
        user_id INTEGER,
        image BLOB,
        deleted INTEGER DEFAULT 0
    );

    CREATE TABLE signatures (
        id INTEGER PRIMARY KEY,
        initiative_id INTEGER NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        signed_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE votes (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        initiative_id INTEGER NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
        created_at TEXT DEFAULT (datetime('now'))
    );