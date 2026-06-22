from flask import Flask, render_template

from database.db import init_db, seed_db

app = Flask(__name__)

# Run schema creation and demo seeding exactly once, before the first request
# is handled. `before_request` runs inside the app context, which `init_db()`
# and `seed_db()` need for `flask run`, WSGI runners, and direct execution.
_db_bootstrapped = False


@app.before_request
def _bootstrap_db():
    global _db_bootstrapped
    if _db_bootstrapped:
        return
    init_db()
    seed_db()
    _db_bootstrapped = True


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    return "Logout — coming in Step 3"


@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


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
