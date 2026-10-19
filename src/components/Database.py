import sqlite3


def db():
    db_connection = sqlite3.connect("data/userdb/data.db")
    return db_connection