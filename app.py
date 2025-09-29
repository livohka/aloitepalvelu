from flask import Flask, render_template, request, redirect, url_for, session, abort, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import Forbidden
import secrets
import db
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # keep secret in production


@app.errorhandler(403)
def forbidden(e):
    flash("Ei käyttöoikeutta pyydettyyn toimintoon.")
    # Palaa edelliselle sivulle, jos referrer löytyy, muuten etusivulle
    return redirect(request.referrer or url_for("index"))


# --- HOME PAGE ---
@app.route("/")
def index():
    # Fetch active initiatives with signature count
    active = db.query(
        """
        SELECT i.id, i.title, u.username, i.image,
               COUNT(s.id) AS signatures
        FROM initiatives i
        JOIN users u ON i.creator_id = u.id
        LEFT JOIN signatures s ON s.initiative_id = i.id
        WHERE i.active = 1 AND i.deleted = 0
        GROUP BY i.id
        ORDER BY i.created_at DESC
        """
    )

    # Fetch inactive initiatives with signature count
    inactive = db.query(
        """
        SELECT i.id, i.title, u.username, i.image,
               COUNT(s.id) AS signatures
        FROM initiatives i
        JOIN users u ON i.creator_id = u.id
        LEFT JOIN signatures s ON s.initiative_id = i.id
        WHERE i.active = 0 AND i.deleted = 0
        GROUP BY i.id
        ORDER BY i.created_at DESC
        """
    )

    return render_template(
        "index.html",
        active_initiatives=active,
        inactive_initiatives=inactive
    )



# --- USER PAGE ---
@app.route("/user", methods=["GET", "POST"])
def user():
    if "user_id" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()

        if len(first_name) < 2 or len(last_name) < 2:
            flash("Etunimen ja sukunimen pitää olla vähintään 2 merkkiä")
        else:
            db.execute(
                "UPDATE users SET first_name=?, last_name=? WHERE id=?",
                [first_name, last_name, session["user_id"]],
            )
            flash("Tiedot päivitetty")

        return redirect(url_for("user"))

    # Hae käyttäjän tiedot
    rows = db.query(
        "SELECT id, username, first_name, last_name FROM users WHERE id = ?",
        [session["user_id"]],
    )
    if not rows:
        abort(404)
    user = rows[0]

    # Käyttäjän aloitteet
    initiatives = db.query(
        """
        SELECT i.id, i.title, i.description, i.active, i.image,
               COUNT(s.id) AS signatures
        FROM initiatives i
        LEFT JOIN signatures s ON s.initiative_id = i.id
        WHERE i.creator_id = ? AND i.deleted = 0
        GROUP BY i.id
        ORDER BY i.id DESC
        """,
        [session["user_id"]],
    )

    return render_template("user.html", user=user, initiatives=initiatives)

# --- SEARCH INITIATIVES ---
@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    results = []

    if query:
        results = db.query(
            """
            SELECT i.id, i.title, u.username, i.image,
                   COUNT(s.id) AS signatures
            FROM initiatives i
            JOIN users u ON i.creator_id = u.id
            LEFT JOIN signatures s ON s.initiative_id = i.id
            WHERE i.deleted = 0
              AND (i.title LIKE ? OR i.description LIKE ? OR u.username LIKE ?)
            GROUP BY i.id
            ORDER BY i.created_at DESC
            """,
            [f"%{query}%", f"%{query}%", f"%{query}%"]
        )

    return render_template("search.html", query=query, results=results)


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


# --- INITIATIVE SIGNATURES LIST ---
@app.route("/initiative/<int:id>/signatures")
def initiative_signatures(id):
    if "user_id" not in session:
        abort(403)

    initiative = db.query(
        "SELECT id, title, creator_id FROM initiatives WHERE id=? AND deleted=0",
        [id]
    )
    if not initiative:
        abort(404)
    initiative = initiative[0]

    # Allow only creator or admin
    if initiative["creator_id"] != session["user_id"] and not session.get("is_admin"):
        abort(403)

    signatures = db.query(
        """
        SELECT u.username, s.signed_at
        FROM signatures s
        JOIN users u ON s.user_id = u.id
        WHERE s.initiative_id = ?
        ORDER BY s.signed_at DESC
        """,
        [id],
    )

    return render_template("initiative_signatures.html",
                           initiative=initiative,
                           signatures=signatures)




# --- REGISTER NEW USER ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        password1 = request.form["password1"]
        password2 = request.form["password2"]

        # Validation
        if not username or not password1:
            flash("Käyttäjänimi ja salasana ovat pakollisia")
            return redirect(url_for("register"))
        if len(first_name) < 2 or len(last_name) < 2:
            flash("Etunimen ja sukunimen on oltava vähintään 2 merkkiä")
            return redirect(url_for("register"))
        if password1 != password2:
            flash("Salasanat eivät täsmää")
            return redirect(url_for("register"))

        # Hash password
        hash_value = generate_password_hash(password1)
        try:
            db.execute(
                "INSERT INTO users (username, first_name, last_name, password_hash) VALUES (?, ?, ?, ?)",
                [username, first_name, last_name, hash_value],
            )
        except sqlite3.IntegrityError:
            flash("Käyttäjänimi on jo varattu")
            return redirect(url_for("register"))

        # Auto-login new user
        row = db.query("SELECT id FROM users WHERE username = ?", [username])[0]
        session["username"] = username
        session["user_id"] = row["id"]

        flash(f"Tervetuloa {first_name} {last_name}, rekisteröityminen onnistui!")
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
        session["is_admin"] = int(user["is_admin"])
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
    session.pop("is_admin", None)
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

    image = None
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename:
            data = file.read()
            if len(data) > 100 * 1024:
                return "Image too large (max 100 KB)", 400
            image = data

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
        default_path = os.path.join(app.root_path, "static", "kukka_optimized_50.png")
        with open(default_path, "rb") as f:
            image_bytes = f.read()
    else:
        image_bytes = rows[0]["image"]

    response = make_response(image_bytes)
    response.headers.set("Content-Type", "image/jpeg")
    return response


# --- INITIATIVE PAGE + SIGNATURES ---
@app.route("/initiative/<int:id>", methods=["GET", "POST"])
def initiative_page(id):
    initiative = db.query(
        "SELECT i.*, u.username FROM initiatives i JOIN users u ON i.creator_id=u.id WHERE i.id=?",
        [id]
    )
    if not initiative:
        abort(404)
    initiative = initiative[0]

    user_signature = None
    if "user_id" in session:
        rows = db.query("SELECT 1 FROM signatures WHERE user_id=? AND initiative_id=?", [session["user_id"], id])
        user_signature = bool(rows)

    if request.method == "POST":
        if "user_id" not in session:
            abort(403)
        if initiative["active"] == 0:
            abort(403)

        if "sign" in request.form:
            try:
                db.execute(
                    "INSERT INTO signatures(user_id, initiative_id) VALUES (?, ?)",
                    [session["user_id"], id]
                )
            except sqlite3.IntegrityError:
                pass
        elif "unsign" in request.form:
            db.execute(
                "DELETE FROM signatures WHERE user_id=? AND initiative_id=?",
                [session["user_id"], id]
            )
        return redirect(url_for("initiative_page", id=id))

    signatures = db.query("SELECT COUNT(*) AS c FROM signatures WHERE initiative_id=?", [id])[0]["c"]

    return render_template("initiative.html", initiative=initiative, signatures=signatures, user_signature=user_signature)


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
        SELECT i.id, i.title, i.description, i.active, i.deleted, i.image, u.username,
               COUNT(s.id) AS signatures
        FROM initiatives i
        JOIN users u ON i.creator_id = u.id
        LEFT JOIN signatures s ON s.initiative_id = i.id
        GROUP BY i.id
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
    db.execute("DELETE FROM signatures WHERE initiative_id = ?", [id])
    db.execute("DELETE FROM initiatives WHERE id = ?", [id])
    flash("Initiative permanently deleted")
    return redirect(url_for("admin_dashboard"))


# --- ADMIN: DELETE USER ---
@app.route("/admin/user/<int:id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(id):
    if id == session.get("user_id"):
        flash("You cannot delete yourself!")
        return redirect(url_for("admin_dashboard"))

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
