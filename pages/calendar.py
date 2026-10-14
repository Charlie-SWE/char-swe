import calendar
from datetime import datetime
from nicegui import ui
from src.components.Layout import frame
from src.components.Colors import (
    PrimaryDarkHex,
    PrimaryLightHex,
    SecondaryDarkHex,
    SecondaryLightHex,
    SecondaryYellowHex,
)


def init():
    @ui.page('/calendar')
    def calendar_page():
        frame()
        today = datetime.today()

        year = today.year
        month = today.month

        highlighted_days = {8, 15, 22} # for now this is just example days that show highlighted days

        month_name = calendar.month_name[month]
        month_calendar = calendar.monthcalendar(year, month)

        ui.label("Calendar").classes("text-4xl font-bold")
        ui.label(f"{month_name} {year}").classes("text-2xl")

        css = f"""
                .calendar {{
                    width: 100%;
                    border-collapse: collapse;
                    text-align: center;
                }}

                .calendar th {{
                    background-color: {PrimaryDarkHex};
                    color: white;
                    padding: 12px;
                }}

                .calendar td {{
                    border: 1px solid {SecondaryLightHex};
                    padding: 20px 10px;
                    height: 65px;
                    position: relative;
                }}

                .today {{
                    background-color: {PrimaryLightHex};
                    font-weight: bold;
                }}

                .event-dot {{
                    height: 8px;
                    width: 8px;
                    background-color: {SecondaryYellowHex};
                    border-radius: 50%;
                    display: block;
                    margin: 5px auto 0 auto;
                }}
        """

        ui.add_css(css)

        html = '<table class="calendar">'
        html += "<tr>"
        for day_name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            html += f"<th>{day_name}</th>"
        html += "</tr>"

        for week in month_calendar:
            html += "<tr>"

            for day in week:
                if day == 0:
                    html += "<td></td>"
                    continue

                cell_class = ""

                if day == today.day:
                    cell_class = "today"

                html += f'<td class="{cell_class}">{day}'

                if day in highlighted_days:
                    html += '<span class="event-dot"></span>'

                html += "</td>"

            html += "</tr>"

        html += "</table>"

        ui.html(html)

        ui.label("Yellow dots tell us about upcoming events.").classes("text-sm")