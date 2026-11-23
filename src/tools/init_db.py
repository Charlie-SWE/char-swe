# init_db.py
# Initializes the database file defined by the SQL schema. This should be run before starting the app!

import sqlite3


def init_db():
    database_path = "data/userdb/"
    db_name = "data.db"
    db_schema = "schema.sql"

    user_db = sqlite3.connect(database_path + db_name)
    user_db.cursor().executescript(open(database_path + db_schema, "r").read())