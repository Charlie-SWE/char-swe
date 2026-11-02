from nicegui import ui
from src.components.Layout import frame

def init():
    @ui.page('/settings')
    def settings_page():
        frame()
        ui.label("Settings").classes("text-4xl font-bold")
        with ui.column().classes("w-full max-w-2xl gap-4"):
            with ui.card().classes("w-full"):
                ui.label("Profile").classes("text-xl font-bold")
                ui.button("Edit Username", on_click=lambda: ui.notify("You clicked me!")

            with ui.card().classes("w-full"):
                ui.label("Account").classes("text-xl font-bold")
                ui.button("Change Password", on_click=lambda: ui.notify("You clicked me!")
                ui.button("Delete Account", on_click=lambda: ui.notify("You clicked me!")

            with ui.card().classes("w-full"):
                ui.label("Appearance").classes("text-xl font-bold")
                ui.button("Dark Mode", on_click=lambda: ui.notify("You clicked me!")
