import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "spendly.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def create_user(name, email, password):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()


def seed_db():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count > 0:
        conn.close()
        return

    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cursor.lastrowid

    expenses = [
        (user_id, 12.50, "Food",          "2026-04-01", "Lunch"),
        (user_id,  8.00, "Transport",     "2026-04-03", "Bus pass"),
        (user_id, 55.00, "Bills",         "2026-04-05", "Electricity"),
        (user_id, 25.00, "Health",        "2026-04-08", "Pharmacy"),
        (user_id, 15.00, "Entertainment", "2026-04-10", "Cinema"),
        (user_id, 40.00, "Shopping",      "2026-04-13", "Clothes"),
        (user_id,  7.50, "Other",         "2026-04-15", "Miscellaneous"),
        (user_id, 18.00, "Food",          "2026-04-18", "Groceries"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()
