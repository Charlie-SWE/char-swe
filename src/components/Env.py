import secrets
from os import environ
from dotenv import load_dotenv, set_key

load_dotenv()

# Optional: the chat page disables itself when this is empty
ROCKY_API_KEY = environ.get("ROCKY_API_KEY", "")

# Signs NiceGUI's session cookies. Generated and persisted on first run.
if not environ.get("STORAGE_SECRET"):
    print("GENERATING STORAGE_SECRET")
    set_key(".env", "STORAGE_SECRET", secrets.token_urlsafe(32))
    load_dotenv(override=True)

STORAGE_SECRET = environ["STORAGE_SECRET"]
