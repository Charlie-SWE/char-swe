from nicegui import ui
from src.components.Layout import frame

def init():
    @ui.page('/view-data')
    def view_data_page():
        frame()
        ui.label('View Player Data').classes('text-4xl font-bold')

        #player names from database
        players = []

        ui.select(
            options=players,
            label='Select a Player'
        )

        ui.label('Select a player to view their information')