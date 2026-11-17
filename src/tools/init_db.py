# init_db.py
# Initializes the database file defined by the SQL schema. This should be run before starting the app!

import sqlite3

from os import environ
from dotenv import load_dotenv, get_key, set_key, unset_key
import secrets

load_dotenv()

def init_db():
    database_path = "data/userdb/"
    db_name = "data.db"
    db_schema = "schema.sql"

    if (get_key(".env", "STORAGE_SECRET") == None):
        print("GENERATING KEY")
        set_key(".env", "STORAGE_SECRET", secrets.token_urlsafe(32))
    user_db = sqlite3.connect(database_path + db_name)
    user_db.cursor().executescript(open(database_path + db_schema, "r").read())