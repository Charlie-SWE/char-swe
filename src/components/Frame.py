from nicegui import ui
from src.components.Colors import PrimaryDarkHex, PrimaryLightHex, SecondaryLightHex, SecondaryDarkHex

NAV_ITEMS = [
    ('Home', 'home', '/'),
    ('Calendar', 'calendar_month', '/calendar'),
    ('View Data', 'table_chart', '/view-data'),
    ('Chat', 'smart_toy', '/chat'),
    ('Settings', 'settings', '/settings'),
]


def frame(active: str = '/'):
    ui.query('body').style('background-color: #f5f7fa')

    with ui.header(elevated=True).classes('items-center gap-2 px-4 py-2').style(
        f'background-color: {PrimaryDarkHex}'
    ):
        ui.button(on_click=lambda: drawer.toggle(), icon='menu') \
            .props('flat round dense') \
            .style(f'color: {SecondaryLightHex}')
        ui.label('Gaffer').classes('text-2xl font-bold tracking-wide absolute left-1/2 -translate-x-1/2') \
            .style(f'color: {PrimaryLightHex}')

    with ui.left_drawer(value=True, bordered=True) \
            .props('width=240') \
            .classes('bg-white q-pa-md') as drawer:
        ui.label('Navigation') \
            .classes('text-xs font-semibold uppercase tracking-wider text-gray-400 q-mb-sm q-px-sm')

        for label, icon, path in NAV_ITEMS:
            is_active = path == active
            btn = ui.button(label, icon=icon, on_click=lambda p=path: ui.navigate.to(p)) \
                .props('flat no-caps align=left') \
                .classes('w-full rounded-lg q-mb-xs text-base')

            if is_active:
                btn.style(
                    f'color: {PrimaryDarkHex}; '
                    f'background-color: {PrimaryLightHex}22; '
                    f'font-weight: 600'
                )
            else:
                btn.style(f'color: {SecondaryDarkHex}')