from flask import Flask, render_template, request, redirect, url_for, session, abort, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import db
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # keep secret in production


# --- HOME PAGE ---
@app.route("/")
def index():
    initiatives = db.query("""
        SELECT i.id, i.title, i.description, i.active, u.username
        FROM initiatives i
        JOIN users u ON i.creator_id = u.id
        WHERE i.deleted = 0
        ORDER BY i.id DESC
    """)
    count_row = db.query("SELECT COUNT(*) AS c FROM initiatives WHERE deleted = 0")
    count = count_row[0]["c"] if count_row else 0
    return render_template("index.html", initiatives=initiatives, count=count)


# --- USER PAGE ---
@app.route("/user")
def user():
    if "user_id" not in session:
        return redirect(url_for("index"))

    rows = db.query("SELECT id, username FROM users WHERE id = ?", [session["user_id"]])
    if not rows:
        abort(404)
    user = rows[0]

    # only show non-deleted initiatives for the user
    initiatives = db.query(
        "SELECT id, title, description, active FROM initiatives WHERE creator_id = ? AND deleted = 0 ORDER BY id DESC",
        [session["user_id"]],
    )

    return render_template("user.html", user=user, initiatives=initiatives)


# --- EDIT INITIATIVE ---
@app.route("/initiative/<int:id>/edit", methods=["GET", "POST"])
def edit_initiative(id):
    if "user_id" not in session:
        abort(403)

    rows = db.query("SELECT id, title, description, creator_id, active, image, deleted FROM initiatives WHERE id = ?", [id])
    if not rows:
        abort(404)
    initiative = rows[0]

    if initiative["creator_id"] != session["user_id"]:
        abort(403)

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()

        if not title:
            return "Title cannot be empty", 400

        remove_image = request.form.get("remove_image")

        image = None
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename:
                data = file.read()
                if len(data) > 100 * 1024:
                    return "Image too large (max 100 KB)", 400
                image = data

        if remove_image:
            db.execute(
                "UPDATE initiatives SET title=?, description=?, image=NULL WHERE id=?",
                [title, description, id]
            )
        elif image is not None:
            db.execute(
                "UPDATE initiatives SET title=?, description=?, image=? WHERE id=?",
                [title, description, image, id]
            )
        else:
            db.execute(
                "UPDATE initiatives SET title=?, description=? WHERE id=?",
                [title, description, id]
            )

        return redirect(url_for("user"))

    return render_template("edit_initiative.html", initiative=initiative)


# --- ACTIVATE INITIATIVE ---
@app.route("/initiative/<int:id>/activate", methods=["POST"])
def activate_initiative(id):
    if "user_id" not in session:
        abort(403)

    rows = db.query("SELECT id, creator_id FROM initiatives WHERE id = ?", [id])
    if not rows:
        abort(404)
    initiative = rows[0]

    if initiative["creator_id"] != session["user_id"]:
        abort(403)

    db.execute("UPDATE initiatives SET active = 1 WHERE id = ?", [id])
    return redirect(url_for("user"))


# --- DEACTIVATE INITIATIVE ---
@app.route("/initiative/<int:id>/deactivate", methods=["POST"])
def deactivate_initiative(id):
    if "user_id" not in session:
        abort(403)

    rows = db.query("SELECT id, creator_id FROM initiatives WHERE id = ?", [id])
    if not rows:
        abort(404)
    initiative = rows[0]

    if initiative["creator_id"] != session["user_id"]:
        abort(403)

    db.execute("UPDATE initiatives SET active = 0 WHERE id = ?", [id])
    return redirect(url_for("user"))


# --- DELETE INITIATIVE (SOFT DELETE) ---
@app.route("/initiative/<int:id>/delete", methods=["POST"])
def delete_initiative(id):
    if "user_id" not in session:
        abort(403)

    rows = db.query("SELECT id, creator_id FROM initiatives WHERE id = ?", [id])
    if not rows:
        abort(404)
    initiative = rows[0]

    if initiative["creator_id"] != session["user_id"]:
        abort(403)

    db.execute("UPDATE initiatives SET deleted = 1 WHERE id = ?", [id])
    return redirect(url_for("user"))


# --- REGISTER NEW USER ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password1 = request.form["password1"]
        password2 = request.form["password2"]

        if not username or not password1:
            flash("Username and password are required")
            return redirect(url_for("register"))
        if password1 != password2:
            flash("Passwords do not match")
            return redirect(url_for("register"))

        hash_value = generate_password_hash(password1)
        try:
            db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                [username, hash_value],
            )
        except sqlite3.IntegrityError:
            flash("Username is already taken")
            return redirect(url_for("register"))

        row = db.query("SELECT id FROM users WHERE username = ?", [username])[0]
        session["username"] = username
        session["user_id"] = row["id"]

        flash(f"Registration successful, welcome {username}!")
        return redirect(url_for("index"))

    return render_template("register.html")


# --- LOGIN ---
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    rows = db.query("SELECT id, username, password_hash, is_admin FROM users WHERE username = ?", [username])
    if not rows:
        flash("Invalid username or password")
        return redirect(url_for("index"))

    user = rows[0]
    if check_password_hash(user["password_hash"], password):
        session["username"] = user["username"]
        session["user_id"] = user["id"]
        session["is_admin"] = int(user["is_admin"])   # ensure it is int
        flash(f"Login successful, welcome {user['username']}!")
        return redirect(url_for("index"))
    else:
        flash("Invalid username or password")
        return redirect(url_for("index"))


# --- LOGOUT ---
@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("user_id", None)
    session.pop("is_admin", None)   # remove admin info from session
    flash("You have been logged out")
    return redirect(url_for("index"))


# --- NEW INITIATIVE PAGE ---
@app.route("/new")
def new():
    if "user_id" not in session:
        return redirect(url_for("index"))
    return render_template("new.html")


# --- CREATE INITIATIVE ---
@app.route("/create", methods=["POST"])
def create():
    if "user_id" not in session:
        abort(403)

    title = request.form["title"].strip()
    description = request.form["description"].strip()
    active = 1 if request.form.get("active") else 0

    # Handle uploaded image
    image = None
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename:
            data = file.read()
            if len(data) > 100 * 1024:  # max 100 KB
                return "Image too large (max 100 KB)", 400
            image = data

    # If user did not upload an image → use default image
    if image is None:
        default_path = os.path.join(app.root_path, "static", "kukka_optimized_50.png")
        with open(default_path, "rb") as f:
            image = f.read()

    db.execute(
        "INSERT INTO initiatives (title, description, creator_id, active, image) VALUES (?, ?, ?, ?, ?)",
        [title, description, session["user_id"], active, image],
    )
    return redirect("/")


# --- SERVE INITIATIVE IMAGE ---
@app.route("/initiative_image/<int:id>")
def initiative_image(id):
    rows = db.query("SELECT image FROM initiatives WHERE id=?", [id])
    if not rows or rows[0]["image"] is None:
        abort(404)
    image_bytes = rows[0]["image"]
    response = make_response(image_bytes)
    response.headers.set("Content-Type", "image/jpeg")
    return response


# --- INITIATIVE PAGE + VOTING ---
@app.route("/initiative/<int:id>", methods=["GET", "POST"])
def initiative_page(id):
    initiative = db.query(
        "SELECT i.*, u.username FROM initiatives i JOIN users u ON i.creator_id=u.id WHERE i.id=?",
        [id]
    )
    if not initiative:
        abort(404)
    initiative = initiative[0]

    user_vote = None
    if "user_id" in session:
        rows = db.query("SELECT 1 FROM votes WHERE user_id=? AND initiative_id=?", [session["user_id"], id])
        user_vote = bool(rows)

    if request.method == "POST":
        if "user_id" not in session:
            abort(403)
        if initiative["active"] == 0:
            abort(403)

        if "vote" in request.form:
            try:
                db.execute(
                    "INSERT INTO votes(user_id, initiative_id) VALUES (?, ?)",
                    [session["user_id"], id]
                )
            except sqlite3.IntegrityError:
                pass
        elif "unvote" in request.form:
            db.execute(
                "DELETE FROM votes WHERE user_id=? AND initiative_id=?",
                [session["user_id"], id]
            )
        return redirect(url_for("initiative_page", id=id))

    votes = db.query("SELECT COUNT(*) AS c FROM votes WHERE initiative_id=?", [id])[0]["c"]

    return render_template("initiative.html", initiative=initiative, votes=votes, user_vote=user_vote)


# --- ADMIN DECORATOR ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            abort(403)
        user = db.query("SELECT is_admin FROM users WHERE id = ?", [session["user_id"]])
        if not user or user[0]["is_admin"] != 1:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# --- ADMIN DASHBOARD ---
@app.route("/admin")
@admin_required
def admin_dashboard():
    users = db.query("SELECT id, username, created_at, is_admin FROM users ORDER BY id")
    initiatives = db.query("""
        SELECT i.id, i.title, i.description, i.active, i.deleted, u.username
        FROM initiatives i
        JOIN users u ON i.creator_id = u.id
        ORDER BY i.id DESC
    """)
    return render_template("admin.html", users=users, initiatives=initiatives)


# --- ADMIN: RESTORE INITIATIVE ---
@app.route("/admin/initiative/<int:id>/restore", methods=["POST"])
@admin_required
def admin_restore_initiative(id):
    db.execute("UPDATE initiatives SET deleted = 0 WHERE id = ?", [id])
    flash("Initiative restored")
    return redirect(url_for("admin_dashboard"))


# --- ADMIN: PURGE INITIATIVE ---
@app.route("/admin/initiative/<int:id>/purge", methods=["POST"])
@admin_required
def admin_purge_initiative(id):
    db.execute("DELETE FROM votes WHERE initiative_id = ?", [id])
    db.execute("DELETE FROM signatures WHERE initiative_id = ?", [id])
    db.execute("DELETE FROM initiatives WHERE id = ?", [id])
    flash("Initiative permanently deleted")
    return redirect(url_for("admin_dashboard"))


# --- ADMIN: DELETE USER ---
@app.route("/admin/user/<int:id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(id):
    if id == session.get("user_id"):   # prevent deleting your own account
        flash("You cannot delete yourself!")
        return redirect(url_for("admin_dashboard"))

    db.execute("DELETE FROM votes WHERE user_id = ?", [id])
    db.execute("DELETE FROM signatures WHERE user_id = ?", [id])
    db.execute("DELETE FROM initiatives WHERE creator_id = ?", [id])
    db.execute("DELETE FROM users WHERE id = ?", [id])

    flash("User permanently deleted")
    return redirect(url_for("admin_dashboard"))


# --- ADMIN: GRANT ADMIN RIGHTS ---
@app.route("/admin/user/<int:id>/make_admin", methods=["POST"])
@admin_required
def admin_make_admin(id):
    if id == session.get("user_id"):
        flash("You already have admin rights")
        return redirect(url_for("admin_dashboard"))

    db.execute("UPDATE users SET is_admin = 1 WHERE id = ?", [id])
    flash("User granted admin rights")
    return redirect(url_for("admin_dashboard"))


# --- ADMIN: REMOVE ADMIN RIGHTS ---
@app.route("/admin/user/<int:id>/remove_admin", methods=["POST"])
@admin_required
def admin_remove_admin(id):
    if id == session.get("user_id"):
        flash("You cannot remove your own admin rights!")
        return redirect(url_for("admin_dashboard"))

    db.execute("UPDATE users SET is_admin = 0 WHERE id = ?", [id])
    flash("User admin rights removed")
    return redirect(url_for("admin_dashboard"))


# --- ADMIN: EDIT INITIATIVE ---
@app.route("/admin/initiative/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_initiative(id):
    rows = db.query("SELECT * FROM initiatives WHERE id = ?", [id])
    if not rows:
        abort(404)
    initiative = rows[0]

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        if not title:
            flash("Title cannot be empty", "error")
            return redirect(url_for("admin_edit_initiative", id=id))

        db.execute(
            "UPDATE initiatives SET title=?, description=? WHERE id=?",
            [title, description, id],
        )
        flash("Initiative updated", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_edit_initiative.html", initiative=initiative)


# --- ADMIN: ACTIVATE INITIATIVE ---
@app.route("/admin/initiative/<int:id>/activate", methods=["POST"])
@admin_required
def admin_activate_initiative(id):
    db.execute("UPDATE initiatives SET active = 1 WHERE id = ?", [id])
    flash("Initiative activated", "success")
    return redirect(url_for("admin_dashboard"))


# --- ADMIN: DEACTIVATE INITIATIVE ---
@app.route("/admin/initiative/<int:id>/deactivate", methods=["POST"])
@admin_required
def admin_deactivate_initiative(id):
    db.execute("UPDATE initiatives SET active = 0 WHERE id = ?", [id])
    flash("Initiative deactivated", "success")
    return redirect(url_for("admin_dashboard"))


# --- ADMIN: SOFT DELETE INITIATIVE ---
@app.route("/admin/initiative/<int:id>/delete", methods=["POST"])
@admin_required
def admin_delete_initiative(id):
    db.execute("UPDATE initiatives SET deleted = 1 WHERE id = ?", [id])
    flash("Initiative marked as deleted", "success")
    return redirect(url_for("admin_dashboard"))


@app.teardown_appcontext
def teardown_db(exception):
    db.close_connection(exception)
