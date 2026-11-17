import threading
from nicegui import app, ui
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.components.Colors import load_css
from src.components.Env import STORAGE_SECRET

from pages import (
    account,
    landing,
    calendar,
    settings,
    chat,
    view_data,
    weather,
    xgboost,
    previous_matches,
)

from src.tools.init_db import init_db

# USER AUTHENTICATION
# If a user is not logged in, they will be redirected to /login

# Non-authenticated users should be able to access these pages
public_routes = {"/favicon.ico", "/login", "/register"}

# Non-authenticated users should be able to access paths with these prefixes
# (/assets holds the static CSS used by the shared layout, including on /login)
public_prefixes = ("/_nicegui", "/assets")

@app.add_middleware
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if app.storage.user.get('authenticated') or path in public_routes or path.startswith(public_prefixes):
            return await call_next(request)
        return RedirectResponse(f'/login?redirect_to={path}')

# Initialize Database
init_db()

def main():
    # Imports all of the CSS
    load_css()

    # Loads all of the pages
    landing.init()
    calendar.init()
    settings.init()
    chat.init()
    view_data.init()
    weather.init()
    previous_matches.init()
    xgboost.init()
    account.init()
    app.add_static_files("/assets", "assets")

    # Loads the favicon
    ui.run(favicon="favicon.svg", storage_secret=STORAGE_SECRET)


if __name__ in {"__main__", "__mp_main__"}:
    main()
