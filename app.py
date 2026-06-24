import os
import warnings

from flask import Flask, redirect, render_template, request, session, url_for

from auth import register_user
from database.db import init_db, seed_db

app = Flask(__name__)

# Rotating SPENDLY_SECRET_KEY invalidates all existing sessions — users are
# silently logged out. Any future "remember me" tokens must handle rotation.
_secret_key = os.environ.get("SPENDLY_SECRET_KEY")
if not _secret_key:
    warnings.warn(
        "SPENDLY_SECRET_KEY is not set — falling back to an insecure development "
        "key. Sessions will NOT survive across processes and must not be used "
        "in production.",
        RuntimeWarning,
        stacklevel=2,
    )
    _secret_key = "spendly-dev-secret-do-not-use-in-prod"
app.config["SECRET_KEY"] = _secret_key

# Run schema creation and demo seeding exactly once, before the first request
# is handled. `before_request` runs inside the app context, which `init_db()`
# and `seed_db()` need for `flask run`, WSGI runners, and direct execution.
_db_bootstrapped = False


@app.before_request
def _bootstrap_db():
    global _db_bootstrapped
    if _db_bootstrapped:
        return
    # Tests set SKIP_DB_BOOTSTRAP=1 in the app config so they can control
    # init_db()/seed_db() directly via fixtures.
    if app.config.get("SKIP_DB_BOOTSTRAP"):
        return
    init_db()
    seed_db()
    _db_bootstrapped = True


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html", user_name=session.get("user_name"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "")
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        user_id, error = register_user(name, email, password)
        if error is not None:
            # 400 lets tests distinguish "form re-shown" from a successful GET.
            return (
                render_template(
                    "register.html",
                    error=error,
                    submitted_name=name,
                    submitted_email=email,
                ),
                400,
            )
        # Clear any pre-existing session data before writing the new keys —
        # prevents session fixation across the registration boundary.
        session.clear()
        session["user_id"] = user_id
        session["user_name"] = name
        return redirect(url_for("landing")), 302
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