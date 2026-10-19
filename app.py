from nicegui import ui
from pages import landing, calendar, settings, chat, view_data

def main():
    landing.init() # layout now handeled by src/components/Layout.py
    calendar.init()
    settings.init()
    chat.init()
    view_data.init()
    ui.run()

if __name__ in {"__main__", "__mp_main__"}:
    main()