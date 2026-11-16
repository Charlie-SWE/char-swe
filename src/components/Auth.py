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

def create_session():
    database = db()
    cur = database.cursor()
    cur.execute(
        f"""
        SELECT session_id
        FROM ChatSession
        WHERE user_id = "{app.storage.user["id"]}"
        ORDER BY session_id DESC
        """
    )
    result = cur.fetchone()
    session_id = 0
    if result != None:
        session_id = result[0] + 1

    cur.execute(
        f"""
        INSERT INTO ChatSession
        (session_id, user_id)
        VALUES ({session_id}, "{app.storage.user["id"]}")
        """
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
        WHERE user_id = "{app.storage.user["id"]}"
            AND session_id = {session}
        ORDER BY message_id DESC
        """
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