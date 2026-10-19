from nicegui import ui, run
from src.components.Layout import frame


def init():
    @ui.page("/weather")
    def weather_page():
        frame()
        ui.label("Weather Test").classes(
            "text-4xl font-bold"
        )
