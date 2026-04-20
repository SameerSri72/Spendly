import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email

app = Flask(__name__)
app.secret_key = "spendly-dev-secret"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not all([name, email, password, confirm]):
            flash("All fields are required.", "error")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("register.html")

        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "error")
            return render_template("register.html")

        flash("Account created — please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("profile"))
        flash("Invalid email or password.", "error")
        return render_template("login.html")
    return render_template("login.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name": "Alex Rivera",
        "email": "alex@example.com",
        "member_since": "January 2024",
        "initials": "AR",
    }
    stats = {
        "total_spent": "$2,847.50",
        "transactions": 34,
        "top_category": "Food & Dining",
    }
    transactions = [
        {"date": "Apr 18, 2026", "description": "Grocery run", "category": "Food & Dining", "amount": "$62.40"},
        {"date": "Apr 15, 2026", "description": "Spotify", "category": "Entertainment", "amount": "$9.99"},
        {"date": "Apr 12, 2026", "description": "Bus pass", "category": "Transport", "amount": "$45.00"},
        {"date": "Apr 10, 2026", "description": "Coffee shop", "category": "Food & Dining", "amount": "$5.80"},
        {"date": "Apr 08, 2026", "description": "Electric bill", "category": "Utilities", "amount": "$110.00"},
    ]
    categories = [
        {"name": "Food & Dining", "amount": "$980.20", "percent": 34},
        {"name": "Transport", "amount": "$520.00", "percent": 18},
        {"name": "Entertainment", "amount": "$310.50", "percent": 11},
        {"name": "Utilities", "amount": "$890.00", "percent": 31},
        {"name": "Shopping", "amount": "$146.80", "percent": 6},
    ]
    return render_template("profile.html", user=user, stats=stats, transactions=transactions, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
