import sqlite3


def db():
    db_connection = sqlite3.connect("data/userdb/data.db", )
    db_connection.execute("PRAGMA foreign_keys = ON;")
    return db_connection