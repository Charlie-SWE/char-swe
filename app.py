from nicegui import ui, app
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.components.Env import STORAGE_SECRET

from pages import account, landing, calendar, settings, chat


# USER AUTHENTICATION
# If a user is not logged in, they will be redirected to /login

# Non-authenticated users should be able to access these pages
public_routes = {"/favicon.ico", "/login", "/register"}

@app.add_middleware
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if app.storage.user.get('authenticated') or path in public_routes or path.startswith('/_nicegui'):
            return await call_next(request)
        return RedirectResponse(f'/login?redirect_to={path}')

def main():
    landing.init() # layout now handeled by src/components/Layout.py
    calendar.init()
    settings.init()
    chat.init()
    account.init()
    ui.run(storage_secret=STORAGE_SECRET)

if __name__ in {"__main__", "__mp_main__"}:
    main()