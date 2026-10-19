from os import environ
from dotenv import load_dotenv

load_dotenv()

ROCKY_API_KEY = environ["ROCKY_API_KEY"]
STORAGE_SECRET = environ["STORAGE_SECRET"]