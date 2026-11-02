from nicegui import ui
from src.components.Layout import frame
from data.kent_state_roster import roster

def init():
    @ui.page('/view-data')
    def view_data_page():
        frame()
        ui.label('View Player Data').classes('text-4xl font-bold')

        #player names from roster
        players = []
        for player in roster:
            players.append(player[1])

        def show_player(e):
            for player in roster:
                if player[1] == e.value:
                    number = player[0]

                    if len(player) == 4:
                        position = player[2]
                        year = player[3]
                    else:
                        position = 'Not provided'
                        year = player[2]
                    player_info.set_text(
                         f'Number: {number} | Position: {position} | Year: {year}'
                    )

        ui.select(
            options=players,
            label='Select a Player',
            on_change=show_player
        ) 

        player_info = ui.label('Select a player to view their information')

        