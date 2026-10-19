from nicegui import ui
from src.components.Frame import frame
from src.components.Colors import PrimaryDarkHex, PrimaryLightHex, SecondaryDarkHex

INTRO = (
    "We are creating an awesome app that takes data from previous soccer matches and uses it to "
    "predict future match outcomes to optimize for a win in the next game! The user and primary "
    "stakeholder is the Kent State women's soccer coach Rob Marinaro."
)

GOALS = (
    "The project aims to support team and strategy management. The software will help the coach "
    "plan the team lineup for the next game and see historical data between the games that were "
    "previously played. If a player is sick or has scheduling conflicts, the coach will be able to "
    "adjust the lineup based on these conditions."
)

FEATURES = (
    "Rob Marinaro will be able to input future game conditions and who the opposing team will be. "
    "There are also opportunities to input player schedules to filter what players and team "
    "compositions will be recommended. There will also be some capabilities to ask an AI assistant "
    "questions about player schedules, player statistics, and to make recommendations based on these "
    "statistics. He will also be able to set constraints and the application will generate possible "
    "lineups to use based on which is the most optimal."
)

TECH = (
    "This project will use the NCAA API to pull historical data from previous soccer matches. "
    "It will also use data from kentstatesports.com. The project will be created with NiceGUI using "
    "SQLite as the database. The backend will make requests to the Rocky API and use LangChain to "
    "allow the LLM to deterministically pull data and run an XGBoost model to make the best "
    "predictions and reconmmendations."
)


def section_card(icon: str, text: str):
    with ui.card().props('flat bordered').classes('w-full rounded-xl q-pa-lg bg-white'):
        with ui.row().classes('items-start no-wrap gap-4'):
            ui.icon(icon, size='md').classes('shrink-0').style(f'color: {SecondaryDarkHex}')
            ui.label(text).classes('text-base leading-relaxed text-gray-700')


@ui.page('/')
def home():
    frame(active='/')

    with ui.column().classes('w-full max-w-3xl mx-auto q-py-xl q-px-md gap-6'):
        with ui.column().classes('gap-2'):
            ui.label('Home').classes('text-4xl font-bold').style(f'color: {PrimaryDarkHex}')
            ui.element('div').classes('h-1 w-16 rounded').style(f'background-color: {PrimaryLightHex}')

        with ui.column().classes('gap-2'):
            ui.label('Hello!').classes('text-xl font-medium text-gray-800')
            ui.label(INTRO).classes('text-lg leading-relaxed text-gray-700')

        section_card('groups', GOALS)
        section_card('tune', FEATURES)
        section_card('memory', TECH)

        ui.label('Thank you!').classes('text-gray-500 italic q-mt-md')