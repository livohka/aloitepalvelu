import sqlite3
from werkzeug.security import generate_password_hash
import os
import random

# Polku projektin juureen (kansion, jossa init.db.py sijaitsee)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Tietokanta luodaan projektin juureen
DB_FILE = os.path.join(BASE_DIR, "database.db")

# Kuva sijaitsee static-hakemistossa
DEFAULT_IMAGE_PATH = os.path.join(BASE_DIR, "static", "kukka_optimized_50.png")

# Load default image
def load_default_image():
    with open(DEFAULT_IMAGE_PATH, "rb") as f:
        return f.read()

# Generate random long descriptions
def random_description(min_len=100, max_len=1900):
    text = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Praesent vehicula, justo nec facilisis imperdiet, nulla massa malesuada sapien, "
        "nec varius lorem ipsum non risus. "
    ) * 50
    length = random.randint(min_len, max_len)
    return text[:length]

def init_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    # Create tables
    cur.executescript("""
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
    """)

    # Users
    users = [
        ("admin", generate_password_hash("admin123"), 1),
        ("matti", generate_password_hash("salasana"), 0),
        ("liisa", generate_password_hash("password"), 0),
    ]
    cur.executemany(
        "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)", users
    )

    default_img = load_default_image()

    # First 3 initiatives manually
    initiatives = [
        ("Free coffee on Mondays", "Coffee for everyone at work on Mondays!", 1, 1, None, default_img, 0),
        ("New break room", "Sofas and a game console for the break room.", 2, 1, None, default_img, 0),
        ("Longer lunch breaks", "Lunch break extended to 1 hour.", 3, 0, None, default_img, 0),
    ]

    # Add 20 test initiatives with random long descriptions
    for i in range(4, 24):
        initiatives.append((
            f"Test Initiative {i}",
            random_description(),
            random.choice([1, 2, 3]),  # creator_id
            1,
            None,
            default_img,
            0
        ))

    cur.executemany(
        "INSERT INTO initiatives (title, description, creator_id, active, user_id, image, deleted) VALUES (?, ?, ?, ?, ?, ?, ?)",
        initiatives
    )

    # Votes
    votes = [
        (2, 1),  # Matti → Admin's initiative
        (3, 1),  # Liisa → Admin's initiative
        (1, 2),  # Admin → Matti's initiative
    ]
    cur.executemany(
        "INSERT INTO votes (user_id, initiative_id) VALUES (?, ?)",
        votes
    )

    # Signatures
    signatures = [
        (1, 2),  # Matti signed Admin's initiative
        (1, 3),  # Liisa signed Admin's initiative
        (2, 1),  # Admin signed Matti's initiative
    ]
    cur.executemany(
        "INSERT INTO signatures (initiative_id, user_id) VALUES (?, ?)",
        signatures
    )

    con.commit()
    con.close()
    print(f"Database created at {DB_FILE} and filled with test data (default image + 20 extra initiatives).")

if __name__ == "__main__":
    init_db()
