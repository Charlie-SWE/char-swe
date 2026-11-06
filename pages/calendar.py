import calendar
from datetime import date

from nicegui import ui

from src.components.Colors import (
    PrimaryDarkHex,
    PrimaryLightHex,
    SecondaryDarkHex,
    SecondaryLightHex,
    SecondaryLightGrayHex,
)
from src.components.Layout import frame, page_body, page_header

FIRST_WEEKDAY = calendar.SUNDAY 
WEEKDAYS = [calendar.day_abbr[(FIRST_WEEKDAY + i) % 7].upper() for i in range(7)]

CSS = """
.cal-grid  { display:grid; grid-template-columns:repeat(7, minmax(0, 1fr)); }
.cal-head  { padding:10px 12px; font-family:'JetBrains Mono',monospace; font-size:11px; letter-spacing:.1em;
             color:#7A849A; border-bottom:1px solid #E3E6EC; }
.cal-cell  { min-height:104px; padding:8px; display:flex; flex-direction:column; gap:4px; min-width:0;
             border-right:1px solid #EEF0F3; border-bottom:1px solid #EEF0F3; }
.cal-cell:nth-child(7n) { border-right:0; }
.cal-cell.outside { background:#FAFBFC; }
.cal-cell.outside .cal-num { color:%(lightgray)s; }
.cal-num   { width:26px; height:26px; border-radius:50%%; display:flex; align-items:center; justify-content:center;
             font-size:13px; font-weight:600; color:#3D4860; }
.cal-num.today { background:%(gold)s; color:%(dark2)s; font-weight:700; }
.cal-event { font-size:12px; font-weight:600; line-height:1.3; padding:3px 6px; border-radius:6px;
             background:#EEF2F9; color:%(dark)s; border-left:3px solid %(dark)s;
             white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.cal-event.away { border-left-color:%(light)s; }
.legend-swatch { width:12px; height:12px; border-radius:3px; background:#EEF2F9; }
""" % {
    "dark": PrimaryDarkHex,
    "dark2": SecondaryDarkHex,
    "gold": PrimaryLightHex,
    "light": SecondaryLightHex,
    "lightgray": SecondaryLightGrayHex,
}


def event_label(game: dict) -> str:
    prefix = "@" if game.get("home") is False else "vs"
    time = f'{game["time"]} ' if game.get("time") else ""
    result = ""
    if game.get("score"):
        us, them = game["score"]
        result = f'{"W" if us > them else "L" if us < them else "D"} {us}–{them} '
    return f'{result}{time}{prefix} {game.get("opponent", "TBD")}'


def init(get_games=lambda year, month: []):
    @ui.page("/calendar")
    def calendar_page():
        frame("calendar")
        ui.add_css(CSS)

        today = date.today()
        view = {"year": today.year, "month": today.month}

        def shift(delta: int):
            m = view["month"] - 1 + delta
            view["year"] += m // 12
            view["month"] = m % 12 + 1
            month_view.refresh()

        def go_today():
            view.update(year=today.year, month=today.month)
            month_view.refresh()

        @ui.refreshable
        def month_view():
            y, m = view["year"], view["month"]
            games = get_games(y, m) or []
            by_day: dict[date, list[dict]] = {}
            for g in games:
                by_day.setdefault(g["date"], []).append(g)

            # Toolbar
            with ui.row().classes("w-full items-center justify-between no-wrap px-5 py-4").style(
                "border-bottom:1px solid #E3E6EC"
            ):
                with ui.row().classes("items-center gap-1 no-wrap"):
                    for icon, delta in (("chevron_left", -1), ("chevron_right", 1)):
                        ui.button(icon=icon, on_click=lambda d=delta: shift(d)).props(
                            "flat round dense"
                        ).style(f"color:{PrimaryDarkHex}")
                    ui.label(f"{calendar.month_name[m]} {y}").classes(
                        "font-display text-xl font-bold ml-2"
                    ).style(f"color:{SecondaryDarkHex}")
                ui.button("Today", on_click=go_today).props("outline no-caps dense").classes(
                    "px-3"
                ).style(f"color:{PrimaryDarkHex}; border-radius:8px; font-weight:600")

            # Grid
            with ui.element("div").classes("cal-grid w-full"):
                for wd in WEEKDAYS:
                    ui.label(wd).classes("cal-head")
                for d in calendar.Calendar(FIRST_WEEKDAY).itermonthdates(y, m):
                    outside = d.month != m
                    with ui.element("div").classes("cal-cell" + (" outside" if outside else "")):
                        ui.label(str(d.day)).classes("cal-num" + (" today" if d == today else ""))
                        for g in by_day.get(d, []):
                            text = event_label(g)
                            with ui.label(text).classes(
                                "cal-event" + (" away" if g.get("home") is False else "")
                            ):
                                ui.tooltip(text)

            # Footer
            with ui.row().classes("w-full items-center gap-5 px-5 py-3 text-sm").style("color:#55607A"):
                if games:
                    for label, color in (("Home", PrimaryDarkHex), ("Away", SecondaryLightHex)):
                        with ui.row().classes("items-center gap-2"):
                            ui.element("div").classes("legend-swatch").style(f"border-left:3px solid {color}")
                            ui.label(label)
                else:
                    ui.icon("event_busy").style("color:#96A0A5; font-size:20px")
                    ui.label(f"No games scheduled for {calendar.month_name[m]}.")

        with page_body():
            page_header("SCHEDULE", "Calendar", "Upcoming games, conditions and opponents.")
            with ui.column().classes("card w-full gap-0 overflow-hidden"):
                month_view()