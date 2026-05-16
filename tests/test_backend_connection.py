import os
import sqlite3

import pytest
from werkzeug.security import generate_password_hash


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point DB_PATH at a temp file, init schema, seed demo user + expenses."""
    db_file = tmp_path / "test_spendly.db"
    monkeypatch.setattr("database.db.DB_PATH", str(db_file))

    from database.db import init_db, seed_db
    init_db()
    seed_db()

    yield str(db_file)


@pytest.fixture
def client(temp_db, monkeypatch):
    """Flask test client that shares the temp DB."""
    # app.py runs init_db()/seed_db() at import time against the real DB_PATH.
    # We re-import after the monkeypatch so it picks up the temp path.
    import importlib
    import database.db as db_module
    import app as app_module

    # Reload app so its module-level init_db/seed_db hit the temp DB.
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.secret_key = "test-secret"

    with app_module.app.test_client() as c:
        yield c


def _seed_user_id(temp_db):
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    conn.close()
    return row["id"]


def _make_empty_user(temp_db):
    conn = sqlite3.connect(temp_db)
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Empty User", "empty@spendly.com", generate_password_hash("pw")),
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid


# ---------------------------------------------------------------- #
# get_user_by_id                                                    #
# ---------------------------------------------------------------- #

def test_get_user_by_id_valid(temp_db):
    from database.queries import get_user_by_id
    uid = _seed_user_id(temp_db)
    user = get_user_by_id(uid)
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    # member_since format: "Month YYYY"
    parts = user["member_since"].split()
    assert len(parts) == 2
    assert parts[1].isdigit() and len(parts[1]) == 4


def test_get_user_by_id_missing(temp_db):
    from database.queries import get_user_by_id
    assert get_user_by_id(99999) is None


# ---------------------------------------------------------------- #
# get_summary_stats                                                 #
# ---------------------------------------------------------------- #

def test_get_summary_stats_with_expenses(temp_db):
    from database.queries import get_summary_stats
    uid = _seed_user_id(temp_db)
    stats = get_summary_stats(uid)
    assert stats["transaction_count"] == 8
    assert round(stats["total_spent"], 2) == 181.00
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(temp_db):
    from database.queries import get_summary_stats
    uid = _make_empty_user(temp_db)
    assert get_summary_stats(uid) == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


# ---------------------------------------------------------------- #
# get_recent_transactions                                           #
# ---------------------------------------------------------------- #

def test_get_recent_transactions_ordered(temp_db):
    from database.queries import get_recent_transactions
    uid = _seed_user_id(temp_db)
    txns = get_recent_transactions(uid)
    assert len(txns) == 8
    dates = [t["date"] for t in txns]
    assert dates == sorted(dates, reverse=True)
    for t in txns:
        assert set(t.keys()) == {"date", "description", "category", "amount"}


def test_get_recent_transactions_empty(temp_db):
    from database.queries import get_recent_transactions
    uid = _make_empty_user(temp_db)
    assert get_recent_transactions(uid) == []


# ---------------------------------------------------------------- #
# get_category_breakdown                                            #
# ---------------------------------------------------------------- #

def test_get_category_breakdown_with_expenses(temp_db):
    from database.queries import get_category_breakdown
    uid = _seed_user_id(temp_db)
    cats = get_category_breakdown(uid)
    assert len(cats) == 7
    amounts = [c["amount"] for c in cats]
    assert amounts == sorted(amounts, reverse=True)
    pcts = [c["pct"] for c in cats]
    assert all(isinstance(p, int) for p in pcts)
    assert sum(pcts) == 100


def test_get_category_breakdown_empty(temp_db):
    from database.queries import get_category_breakdown
    uid = _make_empty_user(temp_db)
    assert get_category_breakdown(uid) == []


# ---------------------------------------------------------------- #
# Route: /profile                                                   #
# ---------------------------------------------------------------- #

def test_profile_unauthenticated_redirects(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_authenticated_seed_user(client, temp_db):
    uid = _seed_user_id(temp_db)
    with client.session_transaction() as s:
        s["user_id"] = uid

    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)

    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body
    assert "₹181.00" in body
    assert ">8<" in body or ">\n            8" in body or "8</p>" in body
    assert "Bills" in body
    for cat in ("Food", "Transport", "Bills", "Health",
                "Entertainment", "Shopping", "Other"):
        assert cat in body

    # newest-first ordering — 2026-04-18 should appear before 2026-04-01
    assert body.index("2026-04-18") < body.index("2026-04-01")


def test_profile_authenticated_empty_user(client, temp_db):
    uid = _make_empty_user(temp_db)
    with client.session_transaction() as s:
        s["user_id"] = uid

    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)

    assert "Empty User" in body
    assert "₹0.00" in body
    assert "—" in body  # top_category placeholder
