from nicegui import ui
from src.components.Colors import PrimaryDarkHex, PrimaryLightHex, SecondaryLightHex, SecondaryDarkHex

def frame():
    with ui.header().style(f'background-color: {PrimaryDarkHex}'):
        ui.button(on_click=lambda: drawer.toggle(), icon='menu').props('flat').style(f'color: {SecondaryLightHex}')
        ui.label('Gaffer').classes('text-xl').style(f'color: {PrimaryLightHex}')

    with ui.left_drawer().classes('bg-gray-100') as drawer:
        ui.label('Navigation').classes('text-lg').style(f'color: {SecondaryDarkHex}')
        
        ui.button('Home', icon='home', on_click=lambda: ui.navigate.to('/')).classes('w-full').props('flat align=left').style(f'color: {SecondaryDarkHex}')
        ui.button('Calendar', icon='calendar_month', on_click=lambda: ui.navigate.to('/calendar')).classes('w-full').props('flat align=left').style(f'color: {SecondaryDarkHex}')
        # ui.button('Chat', icon='smart_toy', on_click=lambda: ui.navigate.to('/chat')).classes('w-full').props('flat align=left').style(f'color: {SecondaryDarkHex}')
        ui.button('Settings', icon='settings', on_click=lambda: ui.navigate.to('/settings')).classes('w-full').props('flat align=left').style(f'color: {SecondaryDarkHex}')
