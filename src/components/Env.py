from os import environ
from dotenv import load_dotenv

load_dotenv()

# Optional: if missing, the chat page disables input and shows a tooltip
ROCKY_API_KEY = environ.get("ROCKY_API_KEY", "")
STORAGE_SECRET = environ["STORAGE_SECRET"]