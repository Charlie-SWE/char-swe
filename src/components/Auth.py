from nicegui import app, ui

from hashlib import pbkdf2_hmac
from os import urandom

from src.components.Database import db

import re


def hash_password(password, salt = urandom(32)):
    hash = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return (salt + hash).hex()

def login(username, password):
    login_err_message = "The provided username or password is incorrect."

    # Get user and hashed password
    cur = db().cursor()
    cur.execute("SELECT pass FROM User WHERE User.user_id = :username", {"username": username})
    result = cur.fetchone()
    if (result == None):
        raise Exception(login_err_message)
    pass_bytes = bytes.fromhex(result[0])

    # Checks if the password is correct.
    # Only proceeds if there is not a mismatch between the user's hash and hashed password
    if (hash_password(password, pass_bytes[:32]) != result[0]):
        raise Exception(login_err_message)

    # Successful login!
    app.storage.user["authenticated"] = True
    app.storage.user["id"] = username


def register(username, password):
    database = db()
    cur = database.cursor()
    cur.execute(
        """
        SELECT * FROM User
        WHERE user_id = :username;
        """,
        {
            "username": username
        }
    )
    result = cur.fetchone()

    
    # Disallow identical user id
    if (result != None):
        raise Exception(f"Username \"{username}\" is already in use. Please choose another.")

    # Empty Username
    if (username == ""):
        raise Exception(f"Please enter a username.")

    # Disallow insufficient password
    if (len(password) < 8):
        raise Exception(f"Password must be at least 8 characters long.")

    pass_hash = hash_password(password)
    
    cur.execute(
        """
        INSERT INTO User 
        (user_id, pass)
        VALUES (:username, :pass);
        """, 
        {
            "username": username,
            "pass": pass_hash
        }
    )
    database.commit()

    login(username, password)

    ui.navigate.to("/")

def logout():
    app.storage.clear()
    ui.navigate.to("/login")

def create_session():
    database = db()
    cur = database.cursor()
    cur.execute(
        f"""
        SELECT session_id
        FROM ChatSession
        WHERE user_id = :user_id
        ORDER BY session_id DESC
        """,
        {
            "user_id": app.storage.user["id"]
        }
    )
    result = cur.fetchone()
    session_id = 0
    if result != None:
        session_id = result[0] + 1

    cur.execute(
        f"""
        INSERT INTO ChatSession
        (session_id, user_id)
        VALUES (:session_id, :user_id)
        """,
        {
            "session_id": session_id,
            "user_id": app.storage.user["id"]
        }
    )
    database.commit()
    return session_id
    

def log_message(session, message, agent):
    database = db()
    cur = database.cursor()
    cur.execute(
        f"""
        SELECT message_id
        FROM ChatMessage
        WHERE user_id = :user_id
            AND session_id = :session_id
        ORDER BY message_id DESC
        """,
        {
            "user_id": app.storage.user["id"],
            "session_id": session
        }
    )
    
    result = cur.fetchone()
    message_id = 0
    if (result != None):
        message_id = result[0] + 1
    
    cur.execute(
        """
        INSERT INTO ChatMessage
        (message_id, session_id, user_id, message_text, agent_type)
        VALUES (:message_id, :session_id, :user_id, :message_text, :agent_type)
        """,
        {
            "message_id": message_id,
            "session_id": session,
            "user_id": app.storage.user["id"],
            "message_text": message,
            "agent_type": agent
        }
    )
    database.commit()