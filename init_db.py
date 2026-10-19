# init_db.py
# Initializes the database file defined by the SQL schema. This should be run before starting the app!

import sqlite3
user_db = sqlite3.connect("data/userdb/data.db")

user_db.cursor().execute(open("data/userdb/schema.sql", "r").read())