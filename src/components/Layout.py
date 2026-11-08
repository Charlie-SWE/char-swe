from nicegui import ui
from src.components.Colors import (
    PrimaryDarkHex,
    PrimaryLightHex,
    SecondaryDarkHex,
    SecondaryGrayHex,
)

NAV_ITEMS = [
    ("home", "Home", "home", "/"),
    ("calendar", "Calendar", "calendar_month", "/calendar"),
    ("data", "View Data", "table_chart", "/view-data"),
    ("chat", "Chat", "smart_toy", "/chat"),
    ("weather", "Weather", "cloud", "/weather"),
    ("settings", "Settings", "settings", "/settings"),
]

HEAD = f"""
<script>
    document.documentElement.classList.add('theme-loading');

    function applySavedTheme() {{
        if (localStorage.getItem('gaffer-dark-mode') === 'true') {{
            document.body.classList.add('dark-theme');
        }}
        document.documentElement.classList.remove('theme-loading');
    }}

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', applySavedTheme);
    }} else {{
        applySavedTheme();
    }}
</script>
<style>
    html.theme-loading body {{
    background-color: #111827 !important;
    visibility: visible;
}}

html.theme-loading .nicegui-content {{
    background-color: #111827 !important;
}}
</style>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=Source+Sans+3:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  body {{ background:#F4F5F7; font-family:'Source Sans 3',sans-serif; color:{SecondaryDarkHex}; }}
  .font-display {{ font-family:'Archivo',sans-serif; letter-spacing:-0.01em; }}
  .font-mono-label {{ font-family:'JetBrains Mono',monospace; font-size:11px; letter-spacing:0.1em; }}
  .nav-btn {{ height:44px; border-radius:10px; text-transform:none; font-size:15px; font-weight:600; }}
  .nav-btn .q-icon {{ color:#7A849A; }}
  .nav-btn.active {{ background:#EEF2F9; color:{PrimaryDarkHex} !important; }}
  .nav-btn.active .q-icon {{ color:{PrimaryLightHex}; }}
  .card {{ background:#fff; border:1px solid #E3E6EC; border-radius:14px; }}
  .feature-card {{ cursor:pointer; transition:border-color .15s, box-shadow .15s; }}
  .feature-card:hover {{ border-color:#B9C4D8; box-shadow:0 6px 20px rgba(0,57,118,.08); }}
</style>
"""


def frame(active: str = "home", user: dict | None = None):
    ui.add_head_html(HEAD)

    ui.add_head_html('<link rel="stylesheet" href="/assets/css/styles.css">')
    
    ui.query(".nicegui-content").classes("p-0")

    with ui.header().classes("items-center gap-3 px-5 h-16").style(
        f"background-color: {PrimaryDarkHex}"
    ):
        ui.button(on_click=lambda: drawer.toggle(), icon="menu").props(
            "flat round color=white"
        )
        with ui.element("div").classes("w-8 h-8 rounded-lg flex items-center justify-center").style(
            f"background:{PrimaryLightHex}"
        ):
            ui.image("favicon.svg").classes("w-6")
        ui.label("Gaffer").classes("font-display text-xl font-extrabold text-white")
        ui.space()
        if user:
            with ui.column().classes("gap-0 items-end leading-tight"):
                ui.label(user.get("name", "")).classes("text-sm font-semibold text-white")
                if user.get("role"):
                    ui.label(user["role"]).classes("text-xs").style("color:#AFC0DD")
            initials = "".join(w[0] for w in user.get("name", "").split()[:2]).upper()
            ui.label(initials).classes(
                "w-9 h-9 rounded-full flex items-center justify-center font-display font-bold text-sm"
            ).style(f"background:{PrimaryLightHex}; color:{SecondaryDarkHex}")

    with ui.left_drawer(value=True).props("width=232 bordered").classes(
        "theme-drawer px-3 py-5 gap-1"
    ) as drawer:
        ui.label("NAVIGATION").classes("font-mono-label px-3 pb-2").style(
            f"color:{SecondaryGrayHex}"
        )
        for key, label, icon, path in NAV_ITEMS:
            ui.button(label, icon=icon, on_click=lambda p=path: ui.navigate.to(p)).classes(
                "nav-btn w-full" + (" active" if key == active else "")
            ).props("flat no-caps align=left")


def page_header(eyebrow: str, title: str, subtitle: str = ""):
    with ui.column().classes("gap-1"):
        ui.label(eyebrow).classes("font-mono-label").style("color:#2C8ECD")
        ui.label(title).classes("font-display text-4xl font-extrabold").style(
            f"color:{SecondaryDarkHex}"
        )
        if subtitle:
            ui.label(subtitle).classes("text-base").style("color:#55607A")


def page_body():
    return ui.column().classes("w-full max-w-[1080px] mx-auto px-10 pt-8 pb-14 gap-7")
