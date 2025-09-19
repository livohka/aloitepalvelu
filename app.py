from flask import Flask, render_template, request, redirect, url_for, session

import db

app = Flask(__name__)
app.secret_key = "jotain nyt vaan"
FAKE_USER = {"username": "demo", "password": "demo123"}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/user")
def user():
    return render_template("user.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if username == FAKE_USER["username"] and password == FAKE_USER["password"]:
        session["username"] = username
        return redirect(url_for("index"))
    # kirjautuminen ei onnistu, -> etusivulle
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))

@app.route("/new")
def new():
    return render_template("new.html")

@app.route("/create", methods=["POST"])
def create():
    title = request.form["title"]
    description = request.form["description"]

    # oletuksena käyttäjä-id = 1 (ei vielä rekisteröintiä)
    db.execute("INSERT INTO initiatives (title, description, creator_id) VALUES (?, ?, ?)",
               [title, description, 1])

    return redirect("/")