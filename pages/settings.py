from nicegui import ui
from src.components.Layout import frame, page_body, page_header


def init():
    @ui.page("/settings")
    def settings_page():
        frame(active="settings")

        with page_body():
            page_header("Settings", "Manage your application preferences.")

            ui.label("Appearance").classes("text-xl font-semibold")

            async def save_dark_mode(e):
                is_dark = str(e.value).lower()

                await ui.run_javascript(f"""
                    document.documentElement.dataset.theme = '{'dark' if is_dark == 'true' else 'light'}';
                    document.body.classList.toggle('dark-theme', {is_dark});
                    localStorage.setItem('gaffer-dark-mode', '{is_dark}');
                """)

            dark_mode_switch = ui.switch("Dark Mode", value=False)

            dark_mode_switch.on_value_change(save_dark_mode)

            async def load_saved_theme():
                saved_theme = await ui.run_javascript(
                    "localStorage.getItem('gaffer-dark-mode') === 'true'"
                )
                dark_mode_switch.set_value(saved_theme)

            ui.timer(0.5, load_saved_theme, once=True)

            ui.button("Profile", on_click=lambda: ui.notify("You clicked me!"))
            ui.button("Account", on_click=lambda: ui.notify("You clicked me!"))
            ui.button("Notifications", on_click=lambda: ui.notify("You clicked me!"))
