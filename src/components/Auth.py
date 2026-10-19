from nicegui import app, ui

from hashlib import pbkdf2_hmac
from os import urandom

from src.components.Database import db

def hash_password(password, salt = urandom(32)):
    hash = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return (salt + hash).hex()

def login(username, password):
    cur = db().cursor()
    cur.execute("SELECT pass FROM User WHERE User.user_id = :username", {"username": username})
    result = cur.fetchone()
    pass_bytes = bytes.fromhex(result[0])
    if (hash_password(password, pass_bytes[:32]) == result[0]):
        app.storage.user["authenticated"] = True
        app.storage.user["id"] = username
        return True
    return False

def register(username, password):
    database = db()
    cur = database.cursor()
    cur.execute(
        """
        INSERT INTO User 
        (user_id, pass)
        VALUES (:username, :pass);
        """, 
        {
            "username": username,
            "pass": hash_password(password)
        }
    )
    database.commit()
    ui.navigate.to("/login")

def logout():
    app.storage.clear()
    ui.navigate.to("/login")