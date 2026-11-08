from nicegui import ui
from src.components.Layout import frame, page_header, page_body
from src.components.Colors import PrimaryDarkHex, PrimaryLightHex, SecondaryDarkHex, SecondaryYellowHex, SecondaryLightHex

FEATURES = [
    ("groups", "Plan the lineup",
     "Input future game conditions and the opposing team, set constraints, and generate possible lineups ranked by how optimal they are.",
     "Open calendar", "/calendar"),
    ("event_busy", "Adjust for availability",
     "Player sick or has a scheduling conflict? Add player schedules to filter which players and compositions get recommended.",
     "View data", "/view-data"),
    ("forum", "Ask the AI assistant",
     "Ask questions about player schedules and statistics, and get recommendations based on them.",
     "Start a chat", "/chat"),
]

PIPELINE = [
    ("01", "Sources", ["NCAA API", "kentstatesports.com"]),
    ("02", "Storage", ["SQLite"]),
    ("03", "Intelligence", ["Rocky API", "LangChain", "XGBoost"]),
    ("04", "Interface", ["NiceGUI"]),
]

ABOUT = [
    "We are creating an app that takes data from previous soccer matches and uses it to predict future match outcomes to optimize for a win in the next game. The user and primary stakeholder is the Kent State women’s soccer coach Rob Marinaro.",
    "The project aims to support team and strategy management. The software will help the coach plan the team lineup for the next game and see historical data between the games that were previously played. If a player is sick or has scheduling conflicts, the coach will be able to adjust the lineup based on these conditions.",
    "Rob Marinaro will be able to input future game conditions and who the opposing team will be. There are also opportunities to input player schedules to filter what players and team compositions will be recommended. There will also be some capabilities to ask an AI assistant questions about player schedules, player statistics, and to make recommendations based on these statistics. He will also be able to set constraints and the application will generate possible lineups to use based on which is the most optimal.",
    "This project will use the NCAA API to pull historical data from previous soccer matches. It will also use data from kentstatesports.com. The project will be created with NiceGUI using SQLite as the database. The backend will make requests to the Rocky API and use LangChain to allow the LLM to deterministically pull data and run an XGBoost model to make the best predictions and recommendations.",
]


def init(get_user=lambda: None):
    @ui.page("/")
    def landing_page():
        user = get_user()
        frame("home", user)
        with page_body():
            page_header("OVERVIEW", "Home")

            with ui.row().classes("w-full rounded-2xl p-10 gap-10 items-center no-wrap").style(
                f"background:{PrimaryDarkHex}"
            ):
                with ui.column().classes("flex-[1.5] gap-3"):
                    ui.label("MATCH PREDICTION & LINEUP PLANNING").classes(
                        "text-xs font-semibold px-3 py-1 rounded-full"
                    ).style(f"background:rgba(239,171,0,.16); color:{SecondaryYellowHex}")
                    ui.label("Turn past matches into a better plan for the next one.").classes(
                        "font-display text-3xl font-bold text-white leading-tight"
                    )
                    ui.label(
                        "Gaffer uses data from previous soccer matches to predict outcomes and optimize "
                        "for a win in the next game."
                    ).classes("text-base leading-relaxed").style("color:#C9D5EA")
                    with ui.row().classes("gap-2 mt-2"):
                        ui.button("Plan next game", icon="event",
                                  on_click=lambda: ui.navigate.to("/calendar")).props(
                            "unelevated no-caps"
                        ).style(f"background:{PrimaryLightHex} !important; color:{SecondaryDarkHex}; font-weight:700; border-radius:10px")
                        ui.button("Ask the assistant", icon="smart_toy",
                                  on_click=lambda: ui.navigate.to("/chat")).props(
                            "outline no-caps color=white"
                        ).style("border-radius:10px; font-weight:600")
                with ui.column().classes("flex-1 gap-2"):
                    for icon, verb, rest in [("history", "Learn", "from historical match data"),
                                             ("tune", "Set", "conditions, opponent & availability"),
                                             ("emoji_events", "Get", "the most optimal lineup")]:
                        with ui.row().classes("w-full items-center gap-3 rounded-xl px-4 py-3 no-wrap").style(
                            "background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12)"
                        ):
                            ui.icon(icon).style(f"color:{SecondaryYellowHex}; font-size:22px")
                            ui.html(f'<b style="color:#fff">{verb}</b> {rest}').classes("text-sm").style("color:#DCE4F2")

            # What you can do
            ui.label("What you can do").classes("font-display text-lg font-bold").style(f"color:{SecondaryDarkHex}")
            with ui.element("div").classes("w-full grid gap-4").style(
                "grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); margin-top:-14px"
            ):
                for icon, title, body, cta, path in FEATURES:
                    with ui.column().classes("card feature-card p-6 gap-2").on(
                        "click", lambda p=path: ui.navigate.to(p)
                    ):
                        with ui.element("div").classes("w-10 h-10 rounded-lg flex items-center justify-center").style("background:#EEF2F9"):
                            ui.icon(icon).style(f"color:{PrimaryDarkHex}; font-size:22px")
                        ui.label(title).classes("font-display text-base font-bold").style(f"color:{SecondaryDarkHex}")
                        ui.label(body).classes("text-sm leading-relaxed").style("color:#55607A")
                        with ui.row().classes("items-center gap-1 mt-auto pt-1"):
                            ui.label(cta).classes("text-sm font-semibold").style(f"color:{PrimaryDarkHex}")
                            ui.icon("arrow_forward").style(f"color:{PrimaryDarkHex}; font-size:18px")

            # How it works
            with ui.column().classes("card w-full p-6 gap-4"):
                ui.label("How it works").classes("font-display text-lg font-bold").style(f"color:{SecondaryDarkHex}")
                with ui.element("div").classes("w-full grid gap-3").style(
                    "grid-template-columns:repeat(auto-fit,minmax(190px,1fr))"
                ):
                    for n, title, tags in PIPELINE:
                        with ui.column().classes("pipeline-box rounded-xl p-4 gap-2"):
                            with ui.row().classes("items-center gap-2"):
                                ui.label(n).classes("font-mono-label").style(f"color:{SecondaryLightHex}")
                                ui.label(title).classes("text-sm font-semibold").style(f"color:{SecondaryDarkHex}")
                            with ui.row().classes("gap-1"):
                                for t in tags:
                                    ui.label(t).classes("pipeline-tag text-xs px-2 py-1 rounded-md").style(
                                        "font-family:'JetBrains Mono',monospace"
                                    )

            # About the project
            with ui.row().classes("card w-full p-7 gap-10 no-wrap"):
                with ui.column().classes("w-[260px] shrink-0 gap-4"):
                    ui.label("About the project").classes("font-display text-lg font-bold").style(f"color:{SecondaryDarkHex}")
                    with ui.column().classes("gap-0"):
                        ui.label("STAKEHOLDER").classes("font-mono-label").style("color:#7A849A")
                        ui.label("Rob Marinaro").classes("font-semibold").style(f"color:{SecondaryDarkHex}")
                        ui.label("Head Coach, Kent State Women’s Soccer").classes("text-sm").style("color:#55607A")
                    with ui.column().classes("gap-0"):
                        ui.label("FOCUS").classes("font-mono-label").style("color:#7A849A")
                        ui.label("Team & strategy management").classes("text-sm").style("color:#55607A")
                with ui.column().classes("gap-3 max-w-[680px]"):
                    for p in ABOUT:
                        ui.label(p).classes("text-[15.5px] leading-relaxed").style("color:#2A3550")
