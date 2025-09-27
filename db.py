import sqlite3
from flask import g

DB_FILE = "database.db"

def get_connection():
    if "db" not in g:
        con = sqlite3.connect(DB_FILE)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        g.db = con
    return g.db

def execute(sql, params=None):
    """Suorita SQL-komento (INSERT, UPDATE, DELETE). Palauttaa viimeisen rivin id."""
    con = get_connection()
    cur = con.cursor()
    if params is None:
        params = []
    result = cur.execute(sql, params)
    con.commit()
    return result.lastrowid

def query(sql, params=None):
    """Suorita SQL SELECT ja palauta rivit listana (sqlite3.Row)."""
    con = get_connection()
    cur = con.cursor()
    if params is None:
        params = []
    cur.execute(sql, params)
    rows = cur.fetchall()
    return rows

def close_connection(e=None):
    """Sulje yhteys, jos olemassa (kutsutaan app.teardown_appcontext)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()
