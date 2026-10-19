from nicegui import ui, app
from src.components.Layout import frame

from src.components.Database import db
from src.components.Auth import login, register





def init():
    @ui.page('/login')
    def login_page(redirect_to: str = ""):
        frame()
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
        ui.label("Create an account").classes("text-4xl font-bold")

        username = ui.input("Username").props("autofocus").on("keydown.enter", lambda: password.run_method("focus"))
        password = ui.input("Password", password=True, password_toggle_button=True).on("keydown.enter", register)
        ui.button("Register", on_click=lambda: register(username, password))
        