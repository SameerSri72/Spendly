from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    created_at = row["created_at"]
    try:
        dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        dt = datetime.strptime(created_at[:10], "%Y-%m-%d")

    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": dt.strftime("%B %Y"),
    }


def get_summary_stats(user_id):
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COUNT(*) AS c, COALESCE(SUM(amount), 0) AS s "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        top = conn.execute(
            "SELECT category, SUM(amount) AS s FROM expenses "
            "WHERE user_id = ? GROUP BY category "
            "ORDER BY s DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if totals["c"] == 0:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    return {
        "total_spent": totals["s"],
        "transaction_count": totals["c"],
        "top_category": top["category"],
    }


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "date": r["date"],
            "description": r["description"],
            "category": r["category"],
            "amount": r["amount"],
        }
        for r in rows
    ]


def get_category_breakdown(user_id):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS s FROM expenses "
            "WHERE user_id = ? GROUP BY category ORDER BY s DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    total = sum(r["s"] for r in rows)
    if total == 0:
        return []

    pcts = [round(r["s"] / total * 100) for r in rows]
    pcts[0] += 100 - sum(pcts)

    return [
        {"name": r["category"], "amount": r["s"], "pct": pcts[i]}
        for i, r in enumerate(rows)
    ]
