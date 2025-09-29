import sqlite3
from werkzeug.security import generate_password_hash
import os
import random
import datetime

# Path to project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database.db")
DEFAULT_IMAGE_PATH = os.path.join(BASE_DIR, "static", "kukka_optimized_50.png")

# Load default image
def load_default_image():
    with open(DEFAULT_IMAGE_PATH, "rb") as f:
        return f.read()

# Random description generator
def random_description(min_len=50, max_len=500):
    text = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Praesent vehicula, justo nec facilisis imperdiet, nulla massa malesuada sapien, "
        "nec varius lorem ipsum non risus. "
    ) * 20
    length = random.randint(min_len, max_len)
    return text[:length]

# Some random first/last names for demo users
FIRST_NAMES = [
    "Anna", "Pekka", "Jussi", "Kaisa", "Ville", "Laura", "Markus", "Tiina",
    "Mikko", "Heidi", "Juho", "Sanna", "Olli", "Mari", "Janne", "Satu"
]
LAST_NAMES = [
    "Korhonen", "Virtanen", "Mäkinen", "Niemi", "Heikkinen", "Laine", "Järvinen",
    "Hämäläinen", "Savolainen", "Ahonen", "Räsänen", "Salmi", "Lehtonen", "Toivonen"
]

def random_name():
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)

def init_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    # Create tables
    cur.executescript("""
    DROP TABLE IF EXISTS signatures;
    DROP TABLE IF EXISTS initiatives;
    DROP TABLE IF EXISTS users;

    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        first_name TEXT,
        last_name TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        is_admin INTEGER DEFAULT 0
    );

    CREATE TABLE initiatives (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TEXT DEFAULT (datetime('now')),
        start_date TEXT,
        end_date TEXT,
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
    """)

    # Default users with custom names
    users = [
        ("admin", generate_password_hash("admin123"), "Allu", "Administrator", 1),
        ("matti", generate_password_hash("matti123"), "Matti", "Sörsselssön", 0),
        ("liisa", generate_password_hash("liisa123"), "Liisa", "Liitovaara", 0),
    ]

    # Generate 247 more random users
    for i in range(4, 251):
        username = f"user{i}"
        password = generate_password_hash("password123")
        first, last = random_name()
        users.append((username, password, first, last, 0))

    cur.executemany(
        "INSERT INTO users (username, password_hash, first_name, last_name, is_admin) VALUES (?, ?, ?, ?, ?)",
        users
    )

    default_img = load_default_image()

    # Generate initiatives
    initiatives = []
    today = datetime.date.today()
    created_at = today - datetime.timedelta(days=7)  # one week before script execution

    # Force admin, matti and liisa to have 2–7 initiatives each
    fixed_creators = {1: "Admin", 2: "Matti", 3: "Liisa"}
    total_fixed = 0
    for creator_id in fixed_creators.keys():
        count = random.randint(2, 7)
        total_fixed += count
        for i in range(count):
            start_date = created_at.isoformat()
            end_date = (today + datetime.timedelta(days=random.randint(-3, 7))).isoformat()
            active = 1 if datetime.date.fromisoformat(end_date) >= today else 0
            initiatives.append((
                f"{fixed_creators[creator_id]} Initiative {i+1}",
                random_description(),
                creator_id,
                created_at.isoformat(),
                start_date,
                end_date,
                active,
                None,
                default_img,
                0
            ))

    # Remaining initiatives up to 150 total
    for i in range(total_fixed + 1, 151):
        creator_id = random.randint(1, 250)
        start_date = created_at.isoformat()
        end_date = (today + datetime.timedelta(days=random.randint(-3, 7))).isoformat()
        active = 1 if datetime.date.fromisoformat(end_date) >= today else 0

        initiatives.append((
            f"Test Initiative {i}",
            random_description(),
            creator_id,
            created_at.isoformat(),
            start_date,
            end_date,
            active,
            None,
            default_img,
            0
        ))

    cur.executemany(
        """
        INSERT INTO initiatives
        (title, description, creator_id, created_at, start_date, end_date, active, user_id, image, deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        initiatives
    )

    # Generate signatures (0–60 per initiative)
    signatures = []
    for initiative_id in range(1, len(initiatives) + 1):
        signer_count = random.randint(0, 60)
        signers = random.sample(range(1, 251), signer_count)
        for user_id in signers:
            signed_at = today.isoformat()
            signatures.append((initiative_id, user_id, signed_at))

    cur.executemany(
        "INSERT INTO signatures (initiative_id, user_id, signed_at) VALUES (?, ?, ?)",
        signatures
    )

    con.commit()

    # Print summary
    print(f"Database created at {DB_FILE}")
    print(f"Users: {len(users)}")
    print(f"Initiatives: {len(initiatives)}")
    print(f"Signatures: {len(signatures)}")

    print("\nFixed creators sample initiatives:")
    for c in fixed_creators.keys():
        rows = [i for i in initiatives if i[2] == c]
        print(f" - User {c} has {len(rows)} initiatives")

    con.close()

if __name__ == "__main__":
    init_db()
