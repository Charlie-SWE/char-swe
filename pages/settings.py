from nicegui import ui
from src.components.Layout import frame

def init():
    @ui.page('/settings')
    def settings_page():
        frame()
        ui.label("Settings").classes("text-4xl font-bold")
        ui.button("Profile", on_click=lambda: ui.notify("You clicked me!"))
        ui.button("Account", on_click=lambda: ui.notify("You clicked me!"))
        ui.button("Notifications", on_click=lambda: ui.notify("You clicked me!"))