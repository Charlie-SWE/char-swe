from nicegui import ui, app
from src.components.Layout import frame, page_body, page_header

from src.components.Database import db
from src.components.Auth import login, register

from fastapi.responses import RedirectResponse

def init():
    @ui.page('/login')
    def login_page(redirect_to: str = ""):
        if ("authenticated" in app.storage.user):
            return RedirectResponse("/")
        
        frame()

        with page_body():
            page_header("Welcome!", "Sign in with your login information, or create an account if you don't yet have one.")

            with ui.card().classes("w-96 mx-auto"):
                ui.label("Login").classes("text-4xl font-bold")

                def submit_login():
                    if login(username.value, password.value):
                        ui.navigate.to(redirect_to)

                username = ui.input("Username").props("autofocus").on("keydown.enter", lambda: password.run_method("focus"))
                password = ui.input("Password", password=True, password_toggle_button=True).on("keydown.enter", submit_login)
                ui.button("Login", on_click=submit_login)

                ui.markdown("## No account?")
                ui.button("Register", on_click= lambda: ui.navigate.to("/register"))

    @ui.page('/register')
    def register_page():
        if ("authenticated" in app.storage.user):
            return RedirectResponse("/")

        def submit_register():
            try:
                register(username.value, password.value)
            except Exception as e:
                ui.notify(f'An error occurred: {e}', type='negative')

        frame()

        with page_body():
            page_header("Welcome!", "Enter a username and a password that is at least 8 characters long.")
            with ui.card().classes("w-96 mx-auto"):
                username = ui.input("Username").props("autofocus").on("keydown.enter", lambda: password.run_method("focus"))
                password = ui.input("Password", password=True, password_toggle_button=True).on("keydown.enter", register)
                ui.button("Register", on_click=submit_register)
        