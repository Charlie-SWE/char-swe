import os

import dotenv
import requests
from nicegui import run, ui
from datetime import date

from src.components.Colors import (
    PrimaryDarkHex,
    PrimaryLightHex,
    SecondaryDarkHex,
    SecondaryLightHex,
)
from src.components.Layout import frame, page_body, page_header
from src.services.game_details import get_games


def init():
    @ui.page("/previous_matches")
    def chat_page():

        with page_body():
            with ui.row().classes("w-full items-end justify-between no-wrap"):
                page_header(
                    "Chat",
                    "Ask about schedules, stats and recommendations.",
                )
